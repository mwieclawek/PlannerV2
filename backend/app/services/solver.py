from datetime import date, timedelta, datetime
from typing import Any, List, Dict, Optional, Tuple
from ortools.sat.python import cp_model
from sqlmodel import Session, select
from ..models import (
    User, ShiftDefinition, JobRole, Availability, StaffingRequirement,
    Schedule, AvailabilityStatus, LeaveRequest, LeaveStatus,
)
from .log_service import log_event
from .scheduler_service import SchedulerService
import logging

logger = logging.getLogger(__name__)

# Wagi odcinkowo-liniowej (piecewise-linear) funkcji kary za odchylenie od efektywnego celu tygodniowego (za każdą minutę)
W_DEV_1 = 6                 # do 4h (0 - 240 min)
W_DEV_2 = 3 * W_DEV_1       # > 4h do 10h (240 - 600 min)
W_DEV_3 = 8 * W_DEV_1       # > 10h (> 600 min)
URGENCY_SCALE = 1200        # waga premii za rzadkość dyspozycyjności (scarcity_ratio * URGENCY_SCALE)


class SolverService:
    def __init__(self, session: Session, tenant_id: int | None = None):
        self.session = session
        self.tenant_id = tenant_id

    def solve(
        self,
        start_date: date,
        end_date: date,
        save: bool = True,
        weekly_targets: Optional[Dict[Any, Dict[str, Any]]] = None,
        actor: Any = None,
    ):
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
        emp_ids = {e.id for e in employees}
        
        # Helper to get range of dates
        delta = end_date - start_date
        days = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
        
        logger.info(
            f"[SOLVER WORKER] Rozpoczęcie generowania grafiku: {start_date} do {end_date} "
            f"(dni: {len(days)}, pracownicy: {len(employees)}, zdefiniowane zmiany: {len(shifts)}, role: {len(roles)}) [tenant:{tid}]."
        )

        # Oblicz efektywne cele tygodniowe z lookaheadem miesięcznym
        if weekly_targets is None:
            sched_svc = SchedulerService(self.session, tenant_id=tid)
            weekly_targets = sched_svc.compute_weekly_targets(
                start_date, end_date, employees=list(employees), shifts=list(shifts)
            )

        # Fetch operational data
        availabilities = self.session.exec(select(Availability).where(
            Availability.date >= start_date, Availability.date <= end_date
        )).all()
        if tid is not None:
            availabilities = [a for a in availabilities if a.user_id in emp_ids]
        
        # Map availability: (str(user_id), date, shift_id) -> status string
        avail_map = {}
        for a in availabilities:
            val = str(a.status.value) if hasattr(a.status, 'value') else str(a.status)
            avail_map[(str(a.user_id), a.date.isoformat(), a.shift_def_id)] = val

        # Approved leaves in the current week
        approved_leaves = self.session.exec(
            select(LeaveRequest).where(
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
            )
        ).all()
        if tid is not None:
            approved_leaves = [lr for lr in approved_leaves if lr.user_id in emp_ids]
        leave_days_set = set()
        for lr in approved_leaves:
            cur = max(start_date, lr.start_date)
            end_lr = min(end_date, lr.end_date)
            while cur <= end_lr:
                leave_days_set.add((lr.user_id, cur))
                cur += timedelta(days=1)

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
        
        # Already worked/scheduled hours in the month outside [start_date, end_date]
        mtd_hours = {
            e.id: float(weekly_targets.get(e.id, {}).get("worked_or_scheduled_hours", 0.0))
            for e in employees
        }

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

        # C2. Availability & Approved Leave Constraints
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            if (e_id, d) in leave_days_set:
                model.Add(w_var == 0)
                continue
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

        # Objective: Maximize preferences & Penalize Overworking / Weekly Target Deviation
        objective_terms = []
        shift_minutes = {s_id: int(round(dur * 60)) for s_id, dur in shift_durations.items()}

        # C4. Monthly & Effective Weekly Targets (Hours / Shifts)
        for e in employees:
            employee_vars = []
            employee_minutes_coeffs = []
            
            for d in days:
                for s in shifts:
                    for r in roles:
                        if (e.id, d, s.id, r.id) in work:
                            var = work[(e.id, d, s.id, r.id)]
                            employee_vars.append(var)
                            employee_minutes_coeffs.append(shift_minutes[s.id])

            # Shift Count Limit (Soft Penalty instead of Hard Constraint)
            if e.target_shifts_per_month is not None:
                excess_shifts_var = model.NewIntVar(0, len(employee_vars), f"excess_shifts_{e.id}")
                model.Add(sum(employee_vars) - e.target_shifts_per_month <= excess_shifts_var)
                objective_terms.append(excess_shifts_var * -2000)
                
            # Hours Target:
            # (a) Strong cap at remaining_monthly_target so monthly target is not exceeded
            # (b) 3-tier piecewise-linear penalty around effective_weekly_target_minutes
            if e.target_hours_per_month is not None and employee_vars:
                wt = weekly_targets.get(e.id, {})
                already_scheduled = mtd_hours.get(e.id, 0.0)
                remaining_monthly_hours = float(
                    wt.get("remaining_monthly_target", max(0.0, float(e.target_hours_per_month) - already_scheduled))
                )
                remaining_monthly_min = int(round(remaining_monthly_hours * 60))
                eff_target_min = int(
                    wt.get("effective_weekly_target_minutes", remaining_monthly_min)
                )
                max_week_min = sum(employee_minutes_coeffs) + 600
                worked_minutes_expr = cp_model.LinearExpr.WeightedSum(employee_vars, employee_minutes_coeffs)

                # Silna kara za przekroczenie pozostałego limitu miesięcznego (-1000 za minutę = -60 000 za godzinę)
                excess_monthly_var = model.NewIntVar(0, max_week_min, f"excess_hours_{e.id}")
                model.Add(worked_minutes_expr - remaining_monthly_min <= excess_monthly_var)
                objective_terms.append(excess_monthly_var * -1000)

                # Trójprogowa odcinkowo-liniowa (piecewise-linear) funkcja kary względem effective_weekly_target_minutes:
                # Tier 1: 0..240 min (do 4h) -> W_DEV_1
                # Tier 2: 240..600 min (>4h do 10h, maks. 360 min) -> W_DEV_2 = 3 * W_DEV_1
                # Tier 3: >600 min (>10h) -> W_DEV_3 = 8 * W_DEV_1
                under_tier1 = model.NewIntVar(0, 240, f"under_t1_{e.id}")
                under_tier2 = model.NewIntVar(0, 360, f"under_t2_{e.id}")
                under_tier3 = model.NewIntVar(0, max(1, eff_target_min), f"under_t3_{e.id}")
                over_tier1 = model.NewIntVar(0, 240, f"over_t1_{e.id}")
                over_tier2 = model.NewIntVar(0, 360, f"over_t2_{e.id}")
                over_tier3 = model.NewIntVar(0, max(1, max_week_min), f"over_t3_{e.id}")

                model.Add(
                    worked_minutes_expr
                    + under_tier1 + under_tier2 + under_tier3
                    - over_tier1 - over_tier2 - over_tier3
                    == eff_target_min
                )

                objective_terms.append((under_tier1 + over_tier1) * -W_DEV_1)
                objective_terms.append((under_tier2 + over_tier2) * -W_DEV_2)
                objective_terms.append((under_tier3 + over_tier3) * -W_DEV_3)

        # 1. Preferences, Slot Filling Reward & Scarcity / Urgency Priority Weight
        for key, w_var in work.items():
            e_id, d, s_id, r_id = key
            status = avail_map.get((str(e_id), d.isoformat(), s_id), "UNKNOWN")
            
            # CRITICAL: High reward for simply filling a requirement so it outweighs weekly target penalties
            objective_terms.append(w_var * 50000) 
            
            if status == "PREFERRED":
                objective_terms.append(w_var * 2000)
            elif status == "AVAILABLE":
                objective_terms.append(w_var * 500)

            # Waga rzadkości dyspozycyjności (Scarcity / Urgency Weight)
            wt = weekly_targets.get(e_id, {})
            scarcity_ratio = float(wt.get("scarcity_ratio", 0.0))
            urgency_bonus = int(round(scarcity_ratio * URGENCY_SCALE))
            if urgency_bonus > 0:
                objective_terms.append(w_var * urgency_bonus)
        
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
            deficit_details = {}
            deficit_explanations = []
            domain_logs = [
                f"Obliczenia CP-SAT zakończone sukcesem w {solve_duration:.3f}s (status={status_name}). Wygenerowano {len(generated_schedules)} przypisań."
            ]
            shift_map = {s.id: s.name for s in shifts}
            role_map = {r.id: r.name for r in roles}
            user_map_obj = {u.id: u for u in employees}
            total_required_slots = sum(r_cnt for r_cnt in req_map.values() if r_cnt > 0)
            
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
                        deficit_msg = (
                            f"Braki kadrowe: data {d.isoformat()}, zmiana '{s_name}', rola '{r_name}' "
                            f"- wymagano {required}, obsadzono {assigned} (deficyt: {missing})."
                        )
                        domain_logs.append(deficit_msg)
                        logger.warning(f"[SOLVER WORKER DEFICIT] {deficit_msg} [tenant:{tid}].")
                        # Diagnostyka przyczyn deficytu (Root Cause Analysis)
                        candidates = [u for u in employees if any(ur.id == r_id for ur in u.job_roles)]
                        root_causes = []
                        if not candidates:
                            cause_str = f"Żaden aktywny pracownik nie posiada roli '{r_name}'!"
                            root_causes.append(cause_str)
                            logger.warning(
                                f"[SOLVER WORKER DEFICIT CAUSE] Przyczyna braku obsady ({d.isoformat()}, {s_name}, {r_name}): "
                                f"W lokalu [tenant:{tid}] {cause_str}"
                            )
                        else:
                            candidate_diagnostics = []
                            for cand in candidates:
                                day_assignments = [sc for sc in generated_schedules if sc.user_id == cand.id and sc.date == d]
                                if day_assignments:
                                    assigned_s_names = [shift_map.get(sc.shift_def_id, '?') for sc in day_assignments]
                                    diag = f"{cand.full_name}: zajęty na innej zmianie ({', '.join(assigned_s_names)})"
                                elif (cand.id, d) in leave_days_set:
                                    diag = f"{cand.full_name}: zatwierdzony urlop"
                                else:
                                    st = avail_map.get((str(cand.id), d.isoformat(), s_id), "UNKNOWN")
                                    if st not in ["AVAILABLE", "PREFERRED"]:
                                        diag = f"{cand.full_name}: brak dostępności ({st})"
                                    else:
                                        diag = f"{cand.full_name}: dostępny ({st}), ale solver zoptymalizował inne kryterium (np. limit godzin)"
                                candidate_diagnostics.append(diag)
                                root_causes.append(diag)
                            cause_str = "; ".join(candidate_diagnostics)
                            logger.warning(
                                f"[SOLVER WORKER DEFICIT CAUSE] Analiza kandydatów ({d.isoformat()}, {s_name}, {r_name}): "
                                f"{cause_str} [tenant:{tid}]."
                            )
                        deficit_details[f"{d.isoformat()} | {s_name} ({r_name})"] = (
                            f"wymagano {required}, obsadzono {assigned} (brak: {missing}) — {cause_str}"
                        )
                        deficit_explanations.append({
                            "date": d.isoformat(),
                            "shift_def_id": s_id,
                            "shift_name": s_name,
                            "role_id": r_id,
                            "role_name": r_name,
                            "required": required,
                            "assigned": assigned,
                            "missing": missing,
                            "root_causes": root_causes,
                        })

            if warnings:
                log_event(
                    "DEFICIT",
                    f"Wykryto braki kadrowe przy generowaniu grafiku ({len(warnings)} pozycji)",
                    deficit_details,
                    level="WARNING",
                    actor=actor or "System / Solver",
                    tenant_id=tid,
                )

            # Podsumowanie przydziału godzin i zmian per pracownik
            sched_by_user = {}
            for sc in generated_schedules:
                sched_by_user.setdefault(sc.user_id, []).append(sc)

            employee_summary = {}
            employee_summaries = []
            for e in employees:
                e_scheds = sched_by_user.get(e.id, [])
                gen_hours = sum(shift_durations.get(sc.shift_def_id, 0.0) for sc in e_scheds)
                prev_h = mtd_hours.get(e.id, 0.0)
                tot_h = prev_h + gen_hours
                wt = weekly_targets.get(e.id, {})
                eff_w_h = float(wt.get("effective_weekly_target_hours", 0.0))
                scarcity_val = float(wt.get("scarcity_ratio", 0.0))
                target_h_str = f"{e.target_hours_per_month:.1f}h" if e.target_hours_per_month is not None else "brak"
                target_s_str = f"{e.target_shifts_per_month}" if e.target_shifts_per_month is not None else "brak"
                logger.info(
                    f"[SOLVER WORKER STATS] Pracownik '{e.full_name}' (id={e.id}): przydzielono {len(e_scheds)} zmian ({gen_hours:.1f}h). "
                    f"Cel efektywny tygodnia: {eff_w_h:.1f}h (scarcity={scarcity_val:.2f}). "
                    f"Miesiąc łącznie: {tot_h:.1f}h (MTD: {prev_h:.1f}h + nowe: {gen_hours:.1f}h, limit: {target_h_str}, limit zmian: {target_s_str}) [tenant:{tid}]."
                )
                employee_summary[e.full_name] = {
                    "cel_miesieczny": e.target_hours_per_month,
                    "juz_wyrobione": round(prev_h, 1),
                    "cel_efektywny_tygodnia": round(eff_w_h, 1),
                    "przypisane_godziny_w_tygodniu": round(gen_hours, 1),
                    "scarcity_ratio": round(scarcity_val, 2),
                }
                employee_summaries.append({
                    "user_id": str(e.id),
                    "user_name": e.full_name,
                    "assigned_shifts": len(e_scheds),
                    "assigned_hours": round(gen_hours, 2),
                    "mtd_hours": round(prev_h, 2),
                    "total_month_hours": round(tot_h, 2),
                    "target_hours": e.target_hours_per_month,
                    "target_shifts": e.target_shifts_per_month,
                    "effective_weekly_target_hours": round(eff_w_h, 2),
                    "scarcity_ratio": round(scarcity_val, 2),
                })

            log_event(
                "SOLVER",
                f"Wygenerowano grafik pracy ({start_date} – {end_date})",
                {
                    "zakres": f"{start_date} - {end_date}",
                    "status": status_name,
                    "czas_wykonania_s": round(solve_duration, 2),
                    "przypisane_zmiany": len(generated_schedules),
                    "liczba_deficytow": len(warnings),
                    "pracownicy": employee_summary,
                },
                level="INFO" if not warnings else "WARNING",
                actor=actor or "System / Solver",
                tenant_id=tid,
            )

            # Check 11h rest violations (clopening) in final schedule
            sched_by_user_day = {}
            for sc in generated_schedules:
                sched_by_user_day.setdefault((sc.user_id, sc.date), []).append(sc.shift_def_id)
            
            rest_violations = []
            for (u_id, d_c), s1_list in sched_by_user_day.items():
                d_n = d_c + timedelta(days=1)
                s2_list = sched_by_user_day.get((u_id, d_n), [])
                for s1_i in s1_list:
                    for s2_i in s2_list:
                        if (s1_i, s2_i) in clopening_pairs:
                            u_obj = user_map_obj.get(u_id)
                            u_name = u_obj.full_name if u_obj else str(u_id)
                            rv_msg = (
                                f"Naruszenie odpoczynku 11h (clopening) dla pracownika '{u_name}' "
                                f"między {d_c.isoformat()} ({shift_map.get(s1_i, '?')}) a {d_n.isoformat()} ({shift_map.get(s2_i, '?')})."
                            )
                            domain_logs.append(rv_msg)
                            rest_violations.append({
                                "user_id": str(u_id),
                                "user_name": u_name,
                                "date_from": d_c.isoformat(),
                                "date_to": d_n.isoformat(),
                                "shift_from": shift_map.get(s1_i, "?"),
                                "shift_to": shift_map.get(s2_i, "?"),
                            })
                            logger.warning(
                                f"[SOLVER WORKER REST VIOLATION] {rv_msg} [tenant:{tid}]."
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

            coverage_pct = (
                round((len(generated_schedules) / total_required_slots) * 100.0, 1)
                if total_required_slots > 0
                else 100.0
            )
            solver_explanation = {
                "solver_status": status_name,
                "solve_duration_sec": round(solve_duration, 4),
                "variables_count": len(work),
                "objective_terms_count": len(objective_terms),
                "objective_value": round(float(solver.ObjectiveValue()), 2),
                "total_required_slots": total_required_slots,
                "total_assigned_slots": len(generated_schedules),
                "coverage_pct": coverage_pct,
                "deficit_explanations": deficit_explanations,
                "employee_summaries": employee_summaries,
                "rest_violations": rest_violations,
                "domain_logs": domain_logs,
            }

            return {
                "status": "success", 
                "count": len(generated_schedules), 
                "schedules": enriched_schedules,
                "warnings": warnings,
                "weekly_targets": {str(k): v for k, v in weekly_targets.items()},
                "solver_explanation": solver_explanation,
            }
        else:
            err_msg = f"Solver nie znalazł dopuszczalnego grafiku (status={status_name}) w {solve_duration:.2f}s dla okresu {start_date} - {end_date}."
            logger.error(f"[SOLVER WORKER ANOMALY] {err_msg} [tenant:{tid}].")
            log_event(
                "SOLVER",
                f"Solver nie znalazł dopuszczalnego grafiku ({start_date} – {end_date})",
                {
                    "zakres": f"{start_date} - {end_date}",
                    "status": status_name,
                    "czas_wykonania_s": round(solve_duration, 2),
                    "przypisane_zmiany": 0,
                    "liczba_deficytow": 0,
                },
                level="ERROR",
                actor=actor or "System / Solver",
                tenant_id=tid,
            )
            return {
                "status": "infeasible",
                "count": 0,
                "warnings": [],
                "weekly_targets": {str(k): v for k, v in weekly_targets.items()},
                "solver_explanation": {
                    "solver_status": status_name,
                    "solve_duration_sec": round(solve_duration, 4),
                    "variables_count": len(work),
                    "objective_terms_count": len(objective_terms),
                    "objective_value": 0.0,
                    "total_required_slots": sum(r_cnt for r_cnt in req_map.values() if r_cnt > 0),
                    "total_assigned_slots": 0,
                    "coverage_pct": 0.0,
                    "deficit_explanations": [],
                    "employee_summaries": [],
                    "rest_violations": [],
                    "domain_logs": [err_msg],
                },
            }
