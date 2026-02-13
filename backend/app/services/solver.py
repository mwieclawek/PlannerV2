from datetime import date, timedelta, datetime
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

        # Fetch specific requirements
        specific_reqs = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.date >= start_date, 
            StaffingRequirement.date <= end_date
        )).all()

        # Fetch global requirements (where day_of_week is NOT NULL)
        global_reqs = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.day_of_week != None
        )).all()

        req_map = {}
        
        # Populate with global first
        for d in days:
            dow = d.weekday()
            for r in global_reqs:
                if r.day_of_week == dow:
                    req_map[(d, r.shift_def_id, r.role_id)] = r.min_count
        
        # Override with specific
        for r in specific_reqs:
            if r.date: # Should be true given query, but safe check
                req_map[(r.date, r.shift_def_id, r.role_id)] = r.min_count

        # 2. Build Model
        model = cp_model.CpModel()
        
        # Variables: shifts[(employee_id, day_str, shift_id, role_id)]
        # We use strings for keys in the dict to be safe with ortools
        work = {} 
        
        for e in employees:
            for d in days:
                for s in shifts:
                    # Check if shift is applicable for this weekday
                    weekday = d.weekday()  # 0=Mon, 6=Sun (matches applicable_days format)
                    applicable_days = [int(x) for x in s.applicable_days.split(",")] if s.applicable_days else list(range(7))
                    if weekday not in applicable_days:
                        continue  # Skip this shift for this day
                    
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
        
        # Constraints
        
        # Helper: Calculate shift durations and overlaps
        shift_durations = {}
        shift_overlaps = [] # List of tuples (s1_id, s2_id)
        
        for s1 in shifts:
            start1 = datetime.combine(date.today(), s1.start_time)
            end1 = datetime.combine(date.today(), s1.end_time)
            if end1 <= start1: end1 += timedelta(days=1)
            duration = (end1 - start1).total_seconds() / 3600
            shift_durations[s1.id] = duration
            
            for s2 in shifts:
                if s1.id >= s2.id: continue # unique pairs, avoid self-compare (handled separately)
                
                start2 = datetime.combine(date.today(), s2.start_time)
                end2 = datetime.combine(date.today(), s2.end_time)
                if end2 <= start2: end2 += timedelta(days=1)
                
                # Check overlap: Max(start1, start2) < Min(end1, end2)
                latest_start = max(start1, start2)
                earliest_end = min(end1, end2)
                
                if latest_start < earliest_end:
                    overlap_duration = (earliest_end - latest_start).total_seconds() / 60 # minutes
                    # Allow overlap if <= 30 minutes (e.g. handover)
                    if overlap_duration > 30:
                        shift_overlaps.append((s1.id, s2.id))

        # C1. No overlapping shifts per employee per day & Max 1 role per shift
        for e in employees:
            for d in days:
                # 1. Max 1 role per unique shift (s.id)
                for s in shifts:
                    vars_for_shift = []
                    for r in roles:
                        if (e.id, d, s.id, r.id) in work:
                            vars_for_shift.append(work[(e.id, d, s.id, r.id)])
                    if vars_for_shift:
                        model.Add(sum(vars_for_shift) <= 1)
                
                # 2. No overlapping different shifts
                for s1_id, s2_id in shift_overlaps:
                    vars_s1 = []
                    vars_s2 = []
                    for r in roles:
                        if (e.id, d, s1_id, r.id) in work: vars_s1.append(work[(e.id, d, s1_id, r.id)])
                        if (e.id, d, s2_id, r.id) in work: vars_s2.append(work[(e.id, d, s2_id, r.id)])
                    
                    if vars_s1 and vars_s2:
                        model.Add(sum(vars_s1) + sum(vars_s2) <= 1)

        # C2. Availability Constraints
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((e_id, d, s_id), AvailabilityStatus.UNAVAILABLE) 
            
            if status == AvailabilityStatus.UNAVAILABLE:
                model.Add(w_var == 0)

        # C3. Staffing Requirements
        for d in days:
            for s in shifts:
                for r in roles:
                    min_req = req_map.get((d, s.id, r.id), 0)
                    relevant_workers = []
                    for e in employees:
                        if (e.id, d, s.id, r.id) in work:
                            relevant_workers.append(work[(e.id, d, s.id, r.id)])
                    if relevant_workers:
                        # Allow slightly less if infeasible? No, hard constraint for now.
                        # But to prevent "infeasible" due to lack of staff, usually we might use soft constraint.
                        # For now, keep as hard constraint <= min_req ??? 
                        # Wait, original code was sum <= min_req? That sounds wrong. 
                        # Usually min_req means "at least".
                        # Original: "model.Add(sum(relevant_workers) <= min_req)" 
                        # The user feedback implied they rely on this. 
                        # Actually, looking at previous code, it was trying to fill UP TO requirement.
                        # "constraint: sum ... <= min_req". This acts as a CAP.
                        # Typically "Requirement" = "We NEED this many".
                        # If I change it to >= it might break if not enough staff.
                        # Let's keep it as CAP for now (matches "Target"), 
                        # BUT usually a "Requirement" is a lower bound. 
                        # Let's switch to >= but maybe with a slack variable if we wanted to be fancy.
                        # Given the prompt doesn't explicitly ask to fix "requirements logic", 
                        # I will assume the previous "Max Cap" logic was intended or I should stick to it unless asked.
                        # Wait, "min_count" implies minimum. 
                        # Let's look at the UI/Usage context. "Requirements" usually means "I need 2 waiters".
                        # If I only have 1, I want 1. If I have 3, I want 2.
                        # So `sum == min_req` is ideal. `sum <= min_req` allows 0. `sum >= min_req` forces it.
                        # The previous code had `sum <= min_req`. This forces under-staffing or exact staffing.
                        # Let's keep it `sum <= min_req` to avoid breaking "feasible" status, 
                        # effectively treating it as "Slots Available".
                        model.Add(sum(relevant_workers) <= min_req)

        # C4. Monthly Targets (Hours / Shifts)
        # We are solving for a range [start_date, end_date]. 
        # If this range is shorter than a month, we only enforce proportional or absolute?
        # User asked: "Assuming if not defined, no limit".
        # We will enforce limit for the *generated period* based on the monthly target.
        # Ideally we'd know usage so far in month, but we don't.
        # We will assume the target applies to this generation if it covers the whole month (simplification).
        # Or better: Just apply the limit as a Hard Cap for the period.
        
        for e in employees:
            employee_vars = []
            employee_hours_coeffs = []
            
            for d in days:
                for s in shifts:
                    for r in roles:
                        if (e.id, d, s.id, r.id) in work:
                            var = work[(e.id, d, s.id, r.id)]
                            employee_vars.append(var)
                            employee_hours_coeffs.append(int(shift_durations[s.id] * 10)) # Scaled by 10 for int 

            # Shift Count Limit
            if e.target_shifts_per_month is not None:
                model.Add(sum(employee_vars) <= e.target_shifts_per_month)
                
            # Hours Limit
            if e.target_hours_per_month is not None:
                # scaled hours <= target * 10
                model.Add(cp_model.LinearExpr.WeightedSum(employee_vars, employee_hours_coeffs) <= e.target_hours_per_month * 10)


        # Objective: Maximize preferences & Penalize Overworking
        objective_terms = []
        
        # 1. Preferences & Slot Filling Reward
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((e_id, d, s_id), AvailabilityStatus.UNAVAILABLE)
            
            # High reward for simply filling a requirement
            objective_terms.append(w_var * 100) 
            
            if status == AvailabilityStatus.PREFERRED:
                objective_terms.append(w_var * 10)
            elif status == AvailabilityStatus.NEUTRAL:
                objective_terms.append(w_var * 5)
            elif status == AvailabilityStatus.AVAILABLE:
                objective_terms.append(w_var * 1) # Base score for working
        
        # 2. Penalty for split shifts (working > 1 shift per day)
        # We subtract Penalty * Excess from objective
        # Let Penalty = 50. It's less than 100, so filling a slot is prioritized over avoiding split shifts.
        for e in employees:
            for d in days:
                daily_vars = []
                for s in shifts:
                    for r in roles:
                         if (e.id, d, s.id, r.id) in work:
                            daily_vars.append(work[(e.id, d, s.id, r.id)])
                
                if daily_vars:
                    shifts_worked = sum(daily_vars)
                    is_working = model.NewBoolVar(f"working_{e.id}_{d}")
                    model.Add(shifts_worked >= 1).OnlyEnforceIf(is_working)
                    model.Add(shifts_worked == 0).OnlyEnforceIf(is_working.Not())
                    
                    penalty_weight = 50
                    objective_terms.append(shifts_worked * (-penalty_weight))
                    objective_terms.append(is_working * penalty_weight)

        model.Maximize(sum(objective_terms))

        # 3. Solve
        solver = cp_model.CpSolver()
        # Set a time limit in case of complexity
        solver.parameters.max_time_in_seconds = 10.0
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

            # 4. Calculate staffing warnings
            # Count assigned workers per (date, shift, role)
            assigned_count = {}
            for sc in generated_schedules:
                key = (sc.date, sc.shift_def_id, sc.role_id)
                assigned_count[key] = assigned_count.get(key, 0) + 1
            
            # Compare with requirements and generate warnings
            warnings = []
            shift_map = {s.id: s.name for s in shifts}
            role_map = {r.id: r.name for r in roles}
            
            for (d, s_id, r_id), required in req_map.items():
                if required > 0:
                    assigned = assigned_count.get((d, s_id, r_id), 0)
                    if assigned < required:
                        warnings.append({
                            "date": d.isoformat(),
                            "shift_def_id": s_id,
                            "role_id": r_id,
                            "role_name": role_map.get(r_id, "Unknown"),
                            "shift_name": shift_map.get(s_id, "Unknown"),
                            "required": required,
                            "assigned": assigned,
                            "missing": required - assigned
                        })

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
            
            return {
                "status": "success", 
                "count": len(generated_schedules), 
                "schedules": generated_schedules,
                "warnings": warnings
            }
        else:
            return {"status": "infeasible", "count": 0, "warnings": []}

