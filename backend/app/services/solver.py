from datetime import date, timedelta, datetime
from typing import List, Dict, Tuple
from ortools.sat.python import cp_model
from sqlmodel import Session, select
from ..models import User, ShiftDefinition, JobRole, Availability, StaffingRequirement, Schedule, AvailabilityStatus
import logging

logger = logging.getLogger(__name__)

class SolverService:
    def __init__(self, session: Session, tenant_id: int | None = None):
        self.session = session
        self.tenant_id = tenant_id

    def solve(self, start_date: date, end_date: date, save: bool = True):
        # 1. Fetch Data
        tid = self.tenant_id
        emp_q = select(User).where(User.is_active == True)
        shift_q = select(ShiftDefinition)
        role_q = select(JobRole)
        if tid is not None:
            emp_q = emp_q.where(User.tenant_id == tid)
            shift_q = shift_q.where(ShiftDefinition.tenant_id == tid)
            role_q = role_q.where(JobRole.tenant_id == tid)
        employees = self.session.exec(emp_q).all()
        shifts = self.session.exec(shift_q).all()
        roles = self.session.exec(role_q).all()
        tenant_shift_ids = {s.id for s in shifts}
        
        # Helper to get range of dates
        delta = end_date - start_date
        days = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
        
        logger.info(
            f"[SOLVER WORKER] Rozpoczęcie generowania grafiku: {start_date} do {end_date} "
            f"(dni: {len(days)}, pracownicy: {len(employees)}, zdefiniowane zmiany: {len(shifts)}, role: {len(roles)}) [tenant:{tid}]."
        )

        # Fetch operational data
        availabilities = self.session.exec(select(Availability).where(
            Availability.date >= start_date, Availability.date <= end_date
        )).all()
        if tid is not None:
            emp_ids = {e.id for e in employees}
            availabilities = [a for a in availabilities if a.user_id in emp_ids]
        
        # Map availability: (str(user_id), date, shift_id) -> status string
        avail_map = {}
        for a in availabilities:
            val = str(a.status.value) if hasattr(a.status, 'value') else str(a.status)
            avail_map[(str(a.user_id), a.date.isoformat(), a.shift_def_id)] = val

        # Fetch specific requirements
        specific_reqs = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.date >= start_date, 
            StaffingRequirement.date <= end_date
        )).all()
        if tid is not None:
            specific_reqs = [r for r in specific_reqs if r.shift_def_id in tenant_shift_ids]

        # Fetch global requirements (where day_of_week is NOT NULL)
        global_reqs = self.session.exec(select(StaffingRequirement).where(
            StaffingRequirement.day_of_week != None
        )).all()
        if tid is not None:
            global_reqs = [r for r in global_reqs if r.shift_def_id in tenant_shift_ids]
        
        # Fetch month-to-date schedules for hours calculation
        month_start_date = start_date.replace(day=1)
        mtd_schedules = self.session.exec(select(Schedule).where(
            Schedule.date >= month_start_date,
            Schedule.date < start_date
        )).all()
        if tid is not None:
            mtd_schedules = [s for s in mtd_schedules if s.user_id in emp_ids]
        
        # Calculate already scheduled hours per employee
        mtd_hours = {}
        for s in mtd_schedules:
            shift = self.session.get(ShiftDefinition, s.shift_def_id)
            if shift:
                start_dt = datetime.combine(date.today(), shift.start_time)
                end_dt = datetime.combine(date.today(), shift.end_time)
                if end_dt <= start_dt: end_dt += timedelta(days=1)
                duration = (end_dt - start_dt).total_seconds() / 3600
                mtd_hours[s.user_id] = mtd_hours.get(s.user_id, 0.0) + duration

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
                    weekday = d.weekday()  # 0=Mon, 6=Sun
                    if hasattr(s, 'days') and s.days:
                        applicable_days = [link.day_of_week for link in s.days]
                    else:
                        applicable_days = list(range(7))
                        
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
                    
                    # Check if one shift is completely enveloped by the other
                    is_enveloped = (start1 >= start2 and end1 <= end2) or (start2 >= start1 and end2 <= end1)
                    
                    # Allow overlap if <= 30 minutes (e.g. handover) AND not enveloped
                    if overlap_duration > 30 or is_enveloped:
                        shift_overlaps.append((s1.id, s2.id))

        # Helper: Calculate pairs of consecutive shifts with < 11h rest ("Clopening")
        clopening_pairs = []  # (s1_id, s2_id) where rest between end of s1 and start of s2 < 11h
        dummy_d0 = date(2026, 1, 1)
        dummy_d1 = date(2026, 1, 2)
        for s1 in shifts:
            start1 = datetime.combine(dummy_d0, s1.start_time)
            end1 = datetime.combine(dummy_d0, s1.end_time)
            if end1 <= start1:
                end1 += timedelta(days=1)
            for s2 in shifts:
                start2 = datetime.combine(dummy_d1, s2.start_time)
                rest_hours = (start2 - end1).total_seconds() / 3600.0
                if rest_hours < 11.0:
                    clopening_pairs.append((s1.id, s2.id))

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
            status = avail_map.get((str(e_id), d.isoformat(), s_id), "UNKNOWN") 
            
            # Forbid scheduling if they didn't explicitly say they are available
            if status not in ["AVAILABLE", "PREFERRED"]:
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
                        model.Add(sum(relevant_workers) <= min_req)

        # Objective: Maximize preferences & Penalize Overworking
        objective_terms = []

        # C4. Monthly Targets (Hours / Shifts)
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

            # Shift Count Limit (Soft Penalty instead of Hard Constraint)
            if e.target_shifts_per_month is not None:
                excess_shifts_var = model.NewIntVar(0, len(employee_vars), f"excess_shifts_{e.id}")
                model.Add(sum(employee_vars) - e.target_shifts_per_month <= excess_shifts_var)
                # Penalty 2000 per excess shift
                objective_terms.append(excess_shifts_var * -2000)
                
            # Hours Limit (Soft Penalty)
            if e.target_hours_per_month is not None:
                already_scheduled = mtd_hours.get(e.id, 0.0)
                remaining = max(0, e.target_hours_per_month - already_scheduled)
                target_scaled = int(remaining * 10)
                
                # Soft penalty for exceeding
                excess_var = model.NewIntVar(0, sum(employee_hours_coeffs) + 1000, f"excess_hours_{e.id}")
                model.Add(cp_model.LinearExpr.WeightedSum(employee_vars, employee_hours_coeffs) - target_scaled <= excess_var)
                
                # Penalty 6000 per scaled hour (meaning 60,000 per full hour to outweigh slot reward)
                objective_terms.append(excess_var * -6000)

        # 1. Preferences & Slot Filling Reward
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((str(e_id), d.isoformat(), s_id), "UNKNOWN")
            
            # CRITICAL: High reward for simply filling a requirement so it outweighs overtime penalties
            objective_terms.append(w_var * 50000) 
            
            if status == "PREFERRED":
                # Reward for PREFERRED
                objective_terms.append(w_var * 2000)
            elif status == "AVAILABLE":
                # Reward for being available
                objective_terms.append(w_var * 500)
        
        # 2. Penalty for split shifts (working > 1 shift per day)
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

        # 3. Labor Law Compliance – 11-hour Daily Rest ("Clopening") Soft Penalty
        for e in employees:
            for i in range(len(days) - 1):
                d_curr = days[i]
                d_next = days[i + 1]
                if (d_next - d_curr).days != 1:
                    continue

                for s1_id, s2_id in clopening_pairs:
                    vars_s1 = [
                        work[(e.id, d_curr, s1_id, r.id)]
                        for r in roles
                        if (e.id, d_curr, s1_id, r.id) in work
                    ]
                    vars_s2 = [
                        work[(e.id, d_next, s2_id, r.id)]
                        for r in roles
                        if (e.id, d_next, s2_id, r.id) in work
                    ]
                    if vars_s1 and vars_s2:
                        violation_var = model.NewBoolVar(f"clopening_{e.id}_{d_curr}_{s1_id}_{s2_id}")
                        model.Add(violation_var >= sum(vars_s1) + sum(vars_s2) - 1)
                        # High penalty of -25000: strongly avoids clopening unless absolutely no other worker exists
                        objective_terms.append(violation_var * -25000)

        model.Maximize(sum(objective_terms))

        # 3. Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0
        logger.info(f"[SOLVER WORKER] Rozpoczynanie obliczeń CP-SAT: utworzono {len(work)} zmiennych, {len(objective_terms)} składników celu (limit: 10s) [tenant:{tid}].")
        
        import time
        solver_start_ts = time.perf_counter()
        status = solver.Solve(model)
        solve_duration = time.perf_counter() - solver_start_ts
        status_name = solver.StatusName(status)

        generated_schedules = []

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
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

            logger.info(f"[SOLVER WORKER] Obliczenia zakończone sukcesem w {solve_duration:.2f}s (status={status_name}). Wygenerowano {len(generated_schedules)} przypisań [tenant:{tid}].")

            # 4. Calculate staffing warnings and log deficits
            assigned_count = {}
            for sc in generated_schedules:
                key = (sc.date, sc.shift_def_id, sc.role_id)
                assigned_count[key] = assigned_count.get(key, 0) + 1
            
            warnings = []
            shift_map = {s.id: s.name for s in shifts}
            role_map = {r.id: r.name for r in roles}
            user_map_obj = {u.id: u for u in employees}
            
            for (d, s_id, r_id), required in req_map.items():
                if required > 0:
                    assigned = assigned_count.get((d, s_id, r_id), 0)
                    if assigned < required:
                        missing = required - assigned
                        s_name = shift_map.get(s_id, f"ID:{s_id}")
                        r_name = role_map.get(r_id, f"ID:{r_id}")
                        warnings.append({
                            "date": d.isoformat(),
                            "shift_def_id": s_id,
                            "role_id": r_id,
                            "role_name": r_name,
                            "shift_name": s_name,
                            "required": required,
                            "assigned": assigned,
                            "missing": missing
                        })
                        logger.warning(
                            f"[SOLVER WORKER DEFICIT] Braki kadrowe: data {d.isoformat()}, zmiana '{s_name}', rola '{r_name}' "
                            f"- wymagano {required}, obsadzono {assigned} (deficyt: {missing}) [tenant:{tid}]."
                        )

            # Check 11h rest violations (clopening) in final schedule
            sched_by_user_day = {}
            for sc in generated_schedules:
                sched_by_user_day.setdefault((sc.user_id, sc.date), []).append(sc.shift_def_id)
            
            for (u_id, d_c), s1_list in sched_by_user_day.items():
                d_n = d_c + timedelta(days=1)
                s2_list = sched_by_user_day.get((u_id, d_n), [])
                for s1_i in s1_list:
                    for s2_i in s2_list:
                        if (s1_i, s2_i) in clopening_pairs:
                            u_obj = user_map_obj.get(u_id)
                            u_name = u_obj.full_name if u_obj else str(u_id)
                            logger.warning(
                                f"[SOLVER WORKER REST VIOLATION] Naruszenie odpoczynku 11h (clopening) dla pracownika '{u_name}' "
                                f"między {d_c.isoformat()} ({shift_map.get(s1_i, '?')}) a {d_n.isoformat()} ({shift_map.get(s2_i, '?')}) [tenant:{tid}]."
                            )

            if save:
                statements = select(Schedule).where(Schedule.date >= start_date, Schedule.date <= end_date)
                results = self.session.exec(statements).all()
                for res in results:
                    self.session.delete(res)
                
                for item in generated_schedules:
                    self.session.add(item)
                self.session.commit()
                logger.info(f"[SOLVER WORKER] Zapisano do bazy {len(generated_schedules)} wpisów grafiku dla zakresu {start_date} - {end_date} [tenant:{tid}].")
            
            shift_map_obj = {s.id: s for s in shifts}
            role_map_obj = {r.id: r for r in roles}

            enriched_schedules = []
            for sc in generated_schedules:
                sh = shift_map_obj.get(sc.shift_def_id)
                r = role_map_obj.get(sc.role_id)
                u = user_map_obj.get(sc.user_id)
                
                enriched_schedules.append({
                    "id": sc.id, 
                    "date": sc.date,
                    "shift_def_id": sc.shift_def_id,
                    "user_id": sc.user_id,
                    "role_id": sc.role_id,
                    "is_published": sc.is_published,
                    "user_name": u.full_name if u else "Unknown",
                    "role_name": r.name if r else "Unknown",
                    "shift_name": sh.name if sh else "Unknown",
                    "start_time": sh.start_time if sh else None,
                    "end_time": sh.end_time if sh else None,
                })

            return {
                "status": "success", 
                "count": len(generated_schedules), 
                "schedules": enriched_schedules,
                "warnings": warnings
            }
        else:
            logger.error(f"[SOLVER WORKER ANOMALY] Solver nie znalazł dopuszczalnego grafiku (status={status_name}) w {solve_duration:.2f}s dla okresu {start_date} - {end_date} [tenant:{tid}].")
            return {"status": "infeasible", "count": 0, "warnings": []}
