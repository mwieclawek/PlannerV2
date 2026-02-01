from datetime import date, timedelta
from typing import List, Dict, Tuple
from ortools.sat.python import cp_model
from sqlmodel import Session, select
from ..models import User, ShiftDefinition, JobRole, Availability, StaffingRequirement, Schedule, AvailabilityStatus

class SolverService:
    def __init__(self, session: Session):
        self.session = session

    def solve(self, start_date: date, end_date: date, save: bool = True):
        # 1. Fetch Data
        employees = self.session.exec(select(User)).all()
        shifts = self.session.exec(select(ShiftDefinition)).all()
        roles = self.session.exec(select(JobRole)).all()
        
        # Helper to get range of dates
        delta = end_date - start_date
        days = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
        
        # Fetch operational data
        availabilities = self.session.exec(select(Availability).where(
            Availability.date >= start_date, Availability.date <= end_date
        )).all()
        
        # Map availability: (user_id, date, shift_id) -> status
        avail_map = {}
        for a in availabilities:
            avail_map[(a.user_id, a.date, a.shift_def_id)] = a.status

        requirements = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.date >= start_date, StaffingRequirement.date <= end_date
        )).all()
        
        # Map requirements: (date, shift_id, role_id) -> min_count
        req_map = {}
        for r in requirements:
            req_map[(r.date, r.shift_def_id, r.role_id)] = r.min_count

        # 2. Build Model
        model = cp_model.CpModel()
        
        # Variables: shifts[(employee_id, day_str, shift_id, role_id)]
        # We use strings for keys in the dict to be safe with ortools
        work = {} 
        
        for e in employees:
            for d in days:
                for s in shifts:
                    for r in roles:
                        # Check if employee has this role
                        # In the real world, check e.job_roles links. Assuming simple check:
                        user_has_role = any(ur.id == r.id for ur in e.job_roles)
                        
                        if user_has_role:
                            # Create variable
                            var_name = f"work_{e.id}_{d}_{s.id}_{r.id}"
                            work[(e.id, d, s.id, r.id)] = model.NewBoolVar(var_name)
                        else:
                            # If employee doesn't have role, they can't work
                            pass
        
        # Constraints
        
        # C1. Max 1 shift per day per employee
        for e in employees:
            for d in days:
                daily_vars = []
                for s in shifts:
                    for r in roles:
                        if (e.id, d, s.id, r.id) in work:
                            daily_vars.append(work[(e.id, d, s.id, r.id)])
                if daily_vars:
                    model.Add(sum(daily_vars) <= 1)
        
        # C2. Availability Constraints
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((e_id, d, s_id), AvailabilityStatus.AVAILABLE) 
            # Default is AVAILABLE if not set (or could be UNKNOWN)
            
            if status == AvailabilityStatus.UNAVAILABLE:
                model.Add(w_var == 0)

        # C3. Staffing Requirements (Modified to prevent overstaffing)
        # Iterate over ALL shifts/roles to ensure 0 requirements result in 0 assignments
        for d in days:
            for s in shifts:
                for r in roles:
                    min_req = req_map.get((d, s.id, r.id), 0)
                    
                    relevant_workers = []
                    for e in employees:
                        if (e.id, d, s.id, r.id) in work:
                            relevant_workers.append(work[(e.id, d, s.id, r.id)])
                    
                    if relevant_workers:
                        # Constraint: Sum of workers <= min_req (Acts as capacity)
                        # Since we maximize 'happiness', the solver will try to fill up to min_req
                        model.Add(sum(relevant_workers) <= min_req)

        # Objective: Maximize preferences
        # PREFERRED = +1, NEUTRAL = 0 (or cost minimization: PREF=0, NEUTRAL=10, AVAIL=20)
        # Let's maximize score
        objective_terms = []
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((e_id, d, s_id), AvailabilityStatus.AVAILABLE)
            
            if status == AvailabilityStatus.PREFERRED:
                objective_terms.append(w_var * 10)
            elif status == AvailabilityStatus.NEUTRAL:
                objective_terms.append(w_var * 5)
            elif status == AvailabilityStatus.AVAILABLE:
                objective_terms.append(w_var * 1)
        
        model.Maximize(sum(objective_terms))

        # 3. Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        generated_schedules = []

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            generated_schedules = []
            for key, w_var in work.items():
                if solver.Value(w_var) == 1:
                    e_id, d, s_id, r_id = key
                    sc = Schedule(
                        date=d,
                        shift_def_id=s_id,
                        user_id=e_id,
                        role_id=r_id,
                        is_published=False
                    )
                    generated_schedules.append(sc)

            if save:
                # Clear old schedules for this period first to clean up
                statements = select(Schedule).where(Schedule.date >= start_date, Schedule.date <= end_date)
                results = self.session.exec(statements).all()
                for res in results:
                    self.session.delete(res)
                
                # Save to DB
                for item in generated_schedules:
                    self.session.add(item)
                self.session.commit()
            
            return {"status": "success", "count": len(generated_schedules), "schedules": generated_schedules}
        else:
            return {"status": "infeasible", "count": 0}
