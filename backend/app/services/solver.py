from datetime import date, datetime, time, timedelta
import json
import logging
import time as perf_time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4

from ortools.sat.python import cp_model
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Wagi odcinkowo-liniowej (piecewise-linear) funkcji kary za odchylenie od efektywnego celu tygodniowego (za każdą minutę)
W_DEV_1 = 6                 # do 4h (0 - 240 min)
W_DEV_2 = 3 * W_DEV_1       # > 4h do 10h (240 - 600 min)
W_DEV_3 = 8 * W_DEV_1       # > 10h (> 600 min)
URGENCY_SCALE = 1200        # waga premii za rzadkość dyspozycyjności (scarcity_ratio * URGENCY_SCALE)


class SolverShiftItem(BaseModel):
    id: int
    name: str
    start_time: str  # "HH:MM" lub "HH:MM:SS"
    end_time: str    # "HH:MM" lub "HH:MM:SS"
    applicable_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


class SolverRoleItem(BaseModel):
    id: int
    name: str


class SolverEmployeeItem(BaseModel):
    id: str
    full_name: str
    role_ids: List[int] = Field(default_factory=list)
    target_hours_per_month: Optional[float] = None
    target_shifts_per_month: Optional[int] = None
    worked_or_scheduled_hours: float = 0.0
    remaining_monthly_target: float = 0.0
    effective_weekly_target_hours: float = 0.0
    effective_weekly_target_minutes: int = 0
    scarcity_ratio: float = 0.0


class SolverRequirementItem(BaseModel):
    date: str  # ISO "YYYY-MM-DD"
    shift_def_id: int
    role_id: int
    min_count: int


class SolverAvailabilityItem(BaseModel):
    user_id: str
    date: str  # ISO "YYYY-MM-DD"
    shift_def_id: int
    status: str  # "AVAILABLE", "PREFERRED", "UNAVAILABLE", "UNKNOWN"


class SolverLeaveDayItem(BaseModel):
    user_id: str
    date: str  # ISO "YYYY-MM-DD"


class SolverJobPayload(BaseModel):
    """
    Samowystarczalny kontrakt Pure-Compute (JSON-In -> OR-Tools CP-SAT -> JSON-Out)
    dla bezstanowego mikroserwisu `solver-worker` (zero połączeń z bazą PostgreSQL).
    """
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[int] = None
    start_date: str  # ISO "YYYY-MM-DD"
    end_date: str    # ISO "YYYY-MM-DD"
    save: bool = False
    shifts: List[SolverShiftItem] = Field(default_factory=list)
    roles: List[SolverRoleItem] = Field(default_factory=list)
    employees: List[SolverEmployeeItem] = Field(default_factory=list)
    requirements: List[SolverRequirementItem] = Field(default_factory=list)
    availabilities: List[SolverAvailabilityItem] = Field(default_factory=list)
    leave_days: List[SolverLeaveDayItem] = Field(default_factory=list)
    weekly_targets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


def _parse_time_str(val: Union[str, time]) -> time:
    if isinstance(val, time):
        return val
    parts = [int(p) for p in str(val).strip().split(":")]
    if len(parts) == 2:
        return time(parts[0], parts[1])
    if len(parts) >= 3:
        return time(parts[0], parts[1], parts[2])
    return time(int(parts[0]), 0)


def solve_from_payload(payload_input: Union[SolverJobPayload, Dict[str, Any], str]) -> Dict[str, Any]:
    """
    100% bezstanowa funkcja Pure-Compute:
    przyjmuje `SolverJobPayload` (obiekt Pydantic, dict lub JSON string),
    uruchamia solver OR-Tools CP-SAT i zwraca kompletny słownik JSON z wygenerowanymi przypisaniami
    oraz raportem `solver_explanation` — bez jakiejkolwiek sesji bazodanowej.
    """
    if isinstance(payload_input, str):
        payload = SolverJobPayload.model_validate_json(payload_input)
    elif isinstance(payload_input, dict):
        payload = SolverJobPayload.model_validate(payload_input)
    else:
        payload = payload_input

    tid = payload.tenant_id
    start_date = date.fromisoformat(payload.start_date)
    end_date = date.fromisoformat(payload.end_date)
    delta = end_date - start_date
    days: List[date] = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    shifts = payload.shifts
    roles = payload.roles
    employees = payload.employees

    logger.info(
        f"[SOLVER WORKER] Rozpoczęcie generowania grafiku (Pure-Compute): {start_date} do {end_date} "
        f"(dni: {len(days)}, pracownicy: {len(employees)}, zdefiniowane zmiany: {len(shifts)}, role: {len(roles)}) [tenant:{tid}]."
    )

    # Map availability: (user_id_str, date_iso, shift_id) -> status string
    avail_map: Dict[Tuple[str, str, int], str] = {}
    for a in payload.availabilities:
        avail_map[(str(a.user_id), a.date, int(a.shift_def_id))] = str(a.status)

    # Approved leave days set: (user_id_str, date_iso)
    leave_days_set: Set[Tuple[str, str]] = {
        (str(ld.user_id), str(ld.date)) for ld in payload.leave_days
    }

    # Staffing requirements map: (date_iso, shift_id, role_id) -> min_count
    req_map: Dict[Tuple[str, int, int], int] = {}
    for req in payload.requirements:
        req_map[(req.date, int(req.shift_def_id), int(req.role_id))] = int(req.min_count)

    # Parse shift times, durations & overlaps
    shift_times: Dict[int, Tuple[time, time]] = {
        s.id: (_parse_time_str(s.start_time), _parse_time_str(s.end_time))
        for s in shifts
    }
    shift_durations: Dict[int, float] = {}
    shift_overlaps: List[Tuple[int, int]] = []

    for s1 in shifts:
        t1_start, t1_end = shift_times[s1.id]
        start1 = datetime.combine(date.today(), t1_start)
        end1 = datetime.combine(date.today(), t1_end)
        if end1 <= start1:
            end1 += timedelta(days=1)
        shift_durations[s1.id] = (end1 - start1).total_seconds() / 3600.0

        for s2 in shifts:
            if s1.id >= s2.id:
                continue
            t2_start, t2_end = shift_times[s2.id]
            start2 = datetime.combine(date.today(), t2_start)
            end2 = datetime.combine(date.today(), t2_end)
            if end2 <= start2:
                end2 += timedelta(days=1)

            latest_start = max(start1, start2)
            earliest_end = min(end1, end2)
            if latest_start < earliest_end:
                overlap_duration = (earliest_end - latest_start).total_seconds() / 60.0
                is_enveloped = (start1 >= start2 and end1 <= end2) or (start2 >= start1 and end2 <= end1)
                if overlap_duration > 30 or is_enveloped:
                    shift_overlaps.append((s1.id, s2.id))

    # Pairs of consecutive shifts with < 11h rest ("Clopening")
    clopening_pairs: List[Tuple[int, int]] = []
    dummy_d0 = date(2026, 1, 1)
    dummy_d1 = date(2026, 1, 2)
    for s1 in shifts:
        t1_start, t1_end = shift_times[s1.id]
        start1 = datetime.combine(dummy_d0, t1_start)
        end1 = datetime.combine(dummy_d0, t1_end)
        if end1 <= start1:
            end1 += timedelta(days=1)
        for s2 in shifts:
            t2_start, _ = shift_times[s2.id]
            start2 = datetime.combine(dummy_d1, t2_start)
            rest_hours = (start2 - end1).total_seconds() / 3600.0
            if rest_hours < 11.0:
                clopening_pairs.append((s1.id, s2.id))

    # Build CP-SAT Model
    model = cp_model.CpModel()
    work: Dict[Tuple[str, str, int, int], Any] = {}

    for e in employees:
        e_roles = set(e.role_ids)
        for d in days:
            d_iso = d.isoformat()
            weekday = d.weekday()
            for s in shifts:
                applicable_days = s.applicable_days if s.applicable_days else list(range(7))
                if weekday not in applicable_days:
                    continue
                for r in roles:
                    if r.id in e_roles:
                        var_name = f"work_{e.id}_{d_iso}_{s.id}_{r.id}"
                        work[(e.id, d_iso, s.id, r.id)] = model.NewBoolVar(var_name)

    # C1. No overlapping shifts per employee per day & Max 1 role per shift
    for e in employees:
        for d in days:
            d_iso = d.isoformat()
            for s in shifts:
                vars_for_shift = [
                    work[(e.id, d_iso, s.id, r.id)]
                    for r in roles
                    if (e.id, d_iso, s.id, r.id) in work
                ]
                if vars_for_shift:
                    model.Add(sum(vars_for_shift) <= 1)

            for s1_id, s2_id in shift_overlaps:
                vars_s1 = [
                    work[(e.id, d_iso, s1_id, r.id)]
                    for r in roles
                    if (e.id, d_iso, s1_id, r.id) in work
                ]
                vars_s2 = [
                    work[(e.id, d_iso, s2_id, r.id)]
                    for r in roles
                    if (e.id, d_iso, s2_id, r.id) in work
                ]
                if vars_s1 and vars_s2:
                    model.Add(sum(vars_s1) + sum(vars_s2) <= 1)

    # C2. Availability & Approved Leave Constraints
    for (e_id, d_iso, s_id, r_id), w_var in work.items():
        if (e_id, d_iso) in leave_days_set:
            model.Add(w_var == 0)
            continue
        status = avail_map.get((e_id, d_iso, s_id), "UNKNOWN")
        if status not in ("AVAILABLE", "PREFERRED"):
            model.Add(w_var == 0)

    # C3. Staffing Requirements
    for d in days:
        d_iso = d.isoformat()
        for s in shifts:
            for r in roles:
                min_req = req_map.get((d_iso, s.id, r.id), 0)
                relevant_workers = [
                    work[(e.id, d_iso, s.id, r.id)]
                    for e in employees
                    if (e.id, d_iso, s.id, r.id) in work
                ]
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
            d_iso = d.isoformat()
            for s in shifts:
                for r in roles:
                    if (e.id, d_iso, s.id, r.id) in work:
                        var = work[(e.id, d_iso, s.id, r.id)]
                        employee_vars.append(var)
                        employee_minutes_coeffs.append(shift_minutes[s.id])

        if e.target_shifts_per_month is not None:
            excess_shifts_var = model.NewIntVar(0, len(employee_vars), f"excess_shifts_{e.id}")
            model.Add(sum(employee_vars) - int(e.target_shifts_per_month) <= excess_shifts_var)
            objective_terms.append(excess_shifts_var * -2000)

        if e.target_hours_per_month is not None and employee_vars:
            wt = payload.weekly_targets.get(str(e.id), {})
            already_scheduled = float(wt.get("worked_or_scheduled_hours", e.worked_or_scheduled_hours))
            remaining_monthly_hours = float(
                wt.get(
                    "remaining_monthly_target",
                    e.remaining_monthly_target
                    if e.remaining_monthly_target > 0 or already_scheduled > 0
                    else max(0.0, float(e.target_hours_per_month) - already_scheduled),
                )
            )
            remaining_monthly_min = int(round(remaining_monthly_hours * 60))
            eff_target_min = int(
                wt.get(
                    "effective_weekly_target_minutes",
                    e.effective_weekly_target_minutes
                    if e.effective_weekly_target_minutes > 0 or "effective_weekly_target_minutes" in wt
                    else remaining_monthly_min,
                )
            )
            max_week_min = sum(employee_minutes_coeffs) + 600
            worked_minutes_expr = cp_model.LinearExpr.WeightedSum(employee_vars, employee_minutes_coeffs)

            # Silna kara za przekroczenie pozostałego limitu miesięcznego (-1000 za minutę)
            excess_monthly_var = model.NewIntVar(0, max_week_min, f"excess_hours_{e.id}")
            model.Add(worked_minutes_expr - remaining_monthly_min <= excess_monthly_var)
            objective_terms.append(excess_monthly_var * -1000)

            # Trójprogowa odcinkowo-liniowa (piecewise-linear) funkcja kary względem effective_weekly_target_minutes:
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

    emp_by_id: Dict[str, SolverEmployeeItem] = {e.id: e for e in employees}

    # 1. Preferences, Slot Filling Reward & Scarcity / Urgency Priority Weight
    for (e_id, d_iso, s_id, r_id), w_var in work.items():
        status = avail_map.get((e_id, d_iso, s_id), "UNKNOWN")
        objective_terms.append(w_var * 50000)

        if status == "PREFERRED":
            objective_terms.append(w_var * 2000)
        elif status == "AVAILABLE":
            objective_terms.append(w_var * 500)

        wt = payload.weekly_targets.get(str(e_id), {})
        emp_obj = emp_by_id.get(e_id)
        scarcity_ratio = float(
            wt.get("scarcity_ratio", emp_obj.scarcity_ratio if emp_obj else 0.0)
        )
        urgency_bonus = int(round(scarcity_ratio * URGENCY_SCALE))
        if urgency_bonus > 0:
            objective_terms.append(w_var * urgency_bonus)

    # 2. Penalty for split shifts (working > 1 shift per day)
    for e in employees:
        for d in days:
            d_iso = d.isoformat()
            daily_vars = [
                work[(e.id, d_iso, s.id, r.id)]
                for s in shifts
                for r in roles
                if (e.id, d_iso, s.id, r.id) in work
            ]
            if daily_vars:
                shifts_worked = sum(daily_vars)
                is_working = model.NewBoolVar(f"working_{e.id}_{d_iso}")
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
            d_curr_iso = d_curr.isoformat()
            d_next_iso = d_next.isoformat()

            for s1_id, s2_id in clopening_pairs:
                vars_s1 = [
                    work[(e.id, d_curr_iso, s1_id, r.id)]
                    for r in roles
                    if (e.id, d_curr_iso, s1_id, r.id) in work
                ]
                vars_s2 = [
                    work[(e.id, d_next_iso, s2_id, r.id)]
                    for r in roles
                    if (e.id, d_next_iso, s2_id, r.id) in work
                ]
                if vars_s1 and vars_s2:
                    violation_var = model.NewBoolVar(f"clopening_{e.id}_{d_curr_iso}_{s1_id}_{s2_id}")
                    model.Add(violation_var >= sum(vars_s1) + sum(vars_s2) - 1)
                    objective_terms.append(violation_var * -25000)

    model.Maximize(sum(objective_terms))

    # Solve CP-SAT
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    logger.info(
        f"[SOLVER WORKER] Rozpoczynanie obliczeń CP-SAT: utworzono {len(work)} zmiennych, "
        f"{len(objective_terms)} składników celu (limit: 10s) [tenant:{tid}]."
    )

    solver_start_ts = perf_time.perf_counter()
    status = solver.Solve(model)
    solve_duration = perf_time.perf_counter() - solver_start_ts
    status_name = solver.StatusName(status)

    shift_map = {s.id: s for s in shifts}
    role_map = {r.id: r for r in roles}
    total_required_slots = sum(r_cnt for r_cnt in req_map.values() if r_cnt > 0)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        generated_items: List[Dict[str, Any]] = []
        for (e_id, d_iso, s_id, r_id), w_var in work.items():
            if solver.Value(w_var) == 1:
                sh = shift_map.get(s_id)
                rl = role_map.get(r_id)
                emp = emp_by_id.get(e_id)
                generated_items.append({
                    "id": str(uuid4()),
                    "date": d_iso,
                    "shift_def_id": s_id,
                    "user_id": e_id,
                    "role_id": r_id,
                    "is_published": False,
                    "user_name": emp.full_name if emp else "Unknown",
                    "role_name": rl.name if rl else "Unknown",
                    "shift_name": sh.name if sh else "Unknown",
                    "start_time": sh.start_time if sh else None,
                    "end_time": sh.end_time if sh else None,
                })

        logger.info(
            f"[SOLVER WORKER] Obliczenia zakończone sukcesem w {solve_duration:.2f}s (status={status_name}). "
            f"Wygenerowano {len(generated_items)} przypisań [tenant:{tid}]."
        )

        assigned_count: Dict[Tuple[str, int, int], int] = {}
        for item in generated_items:
            k = (item["date"], item["shift_def_id"], item["role_id"])
            assigned_count[k] = assigned_count.get(k, 0) + 1

        warnings: List[Dict[str, Any]] = []
        deficit_details: Dict[str, str] = {}
        deficit_explanations: List[Dict[str, Any]] = []
        domain_logs: List[str] = [
            f"Obliczenia CP-SAT zakończone sukcesem w {solve_duration:.3f}s (status={status_name}). "
            f"Wygenerowano {len(generated_items)} przypisań."
        ]

        for (d_iso, s_id, r_id), required in req_map.items():
            if required > 0:
                assigned = assigned_count.get((d_iso, s_id, r_id), 0)
                if assigned < required:
                    missing = required - assigned
                    sh_obj = shift_map.get(s_id)
                    rl_obj = role_map.get(r_id)
                    s_name = sh_obj.name if sh_obj else f"ID:{s_id}"
                    r_name = rl_obj.name if rl_obj else f"ID:{r_id}"
                    warnings.append({
                        "date": d_iso,
                        "shift_def_id": s_id,
                        "role_id": r_id,
                        "role_name": r_name,
                        "shift_name": s_name,
                        "required": required,
                        "assigned": assigned,
                        "missing": missing,
                    })
                    deficit_msg = (
                        f"Braki kadrowe: data {d_iso}, zmiana '{s_name}', rola '{r_name}' "
                        f"- wymagano {required}, obsadzono {assigned} (deficyt: {missing})."
                    )
                    domain_logs.append(deficit_msg)
                    logger.warning(f"[SOLVER WORKER DEFICIT] {deficit_msg} [tenant:{tid}].")

                    candidates = [u for u in employees if r_id in u.role_ids]
                    root_causes: List[str] = []
                    if not candidates:
                        cause_str = f"Żaden aktywny pracownik nie posiada roli '{r_name}'!"
                        root_causes.append(cause_str)
                        logger.warning(
                            f"[SOLVER WORKER DEFICIT CAUSE] Przyczyna braku obsady ({d_iso}, {s_name}, {r_name}): "
                            f"W lokalu [tenant:{tid}] {cause_str}"
                        )
                    else:
                        candidate_diagnostics = []
                        for cand in candidates:
                            day_assignments = [
                                it for it in generated_items
                                if it["user_id"] == cand.id and it["date"] == d_iso
                            ]
                            if day_assignments:
                                assigned_s_names = [it.get("shift_name", "?") for it in day_assignments]
                                diag = f"{cand.full_name}: zajęty na innej zmianie ({', '.join(assigned_s_names)})"
                            elif (cand.id, d_iso) in leave_days_set:
                                diag = f"{cand.full_name}: zatwierdzony urlop"
                            else:
                                st = avail_map.get((cand.id, d_iso, s_id), "UNKNOWN")
                                if st not in ("AVAILABLE", "PREFERRED"):
                                    diag = f"{cand.full_name}: brak dostępności ({st})"
                                else:
                                    diag = f"{cand.full_name}: dostępny ({st}), ale solver zoptymalizował inne kryterium (np. limit godzin)"
                            candidate_diagnostics.append(diag)
                            root_causes.append(diag)
                        cause_str = "; ".join(candidate_diagnostics)
                        logger.warning(
                            f"[SOLVER WORKER DEFICIT CAUSE] Analiza kandydatów ({d_iso}, {s_name}, {r_name}): "
                            f"{cause_str} [tenant:{tid}]."
                        )
                    deficit_details[f"{d_iso} | {s_name} ({r_name})"] = (
                        f"wymagano {required}, obsadzono {assigned} (brak: {missing}) — {cause_str}"
                    )
                    deficit_explanations.append({
                        "date": d_iso,
                        "shift_def_id": s_id,
                        "shift_name": s_name,
                        "role_id": r_id,
                        "role_name": r_name,
                        "required": required,
                        "assigned": assigned,
                        "missing": missing,
                        "root_causes": root_causes,
                    })

        # Podsumowanie przydziału godzin i zmian per pracownik
        sched_by_user: Dict[str, List[Dict[str, Any]]] = {}
        for it in generated_items:
            sched_by_user.setdefault(it["user_id"], []).append(it)

        employee_summary: Dict[str, Dict[str, Any]] = {}
        employee_summaries: List[Dict[str, Any]] = []
        for e in employees:
            e_scheds = sched_by_user.get(e.id, [])
            gen_hours = sum(shift_durations.get(it["shift_def_id"], 0.0) for it in e_scheds)
            wt = payload.weekly_targets.get(str(e.id), {})
            prev_h = float(wt.get("worked_or_scheduled_hours", e.worked_or_scheduled_hours))
            tot_h = prev_h + gen_hours
            eff_w_h = float(wt.get("effective_weekly_target_hours", e.effective_weekly_target_hours))
            scarcity_val = float(wt.get("scarcity_ratio", e.scarcity_ratio))
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

        # Check 11h rest violations (clopening) in final schedule
        sched_by_user_day: Dict[Tuple[str, str], List[int]] = {}
        for it in generated_items:
            sched_by_user_day.setdefault((it["user_id"], it["date"]), []).append(it["shift_def_id"])

        rest_violations: List[Dict[str, Any]] = []
        for (u_id, d_c_iso), s1_list in sched_by_user_day.items():
            d_n_iso = (date.fromisoformat(d_c_iso) + timedelta(days=1)).isoformat()
            s2_list = sched_by_user_day.get((u_id, d_n_iso), [])
            for s1_i in s1_list:
                for s2_i in s2_list:
                    if (s1_i, s2_i) in clopening_pairs:
                        u_obj = emp_by_id.get(u_id)
                        u_name = u_obj.full_name if u_obj else str(u_id)
                        s1_name = shift_map[s1_i].name if s1_i in shift_map else "?"
                        s2_name = shift_map[s2_i].name if s2_i in shift_map else "?"
                        rv_msg = (
                            f"Naruszenie odpoczynku 11h (clopening) dla pracownika '{u_name}' "
                            f"między {d_c_iso} ({s1_name}) a {d_n_iso} ({s2_name})."
                        )
                        domain_logs.append(rv_msg)
                        rest_violations.append({
                            "user_id": str(u_id),
                            "user_name": u_name,
                            "date_from": d_c_iso,
                            "date_to": d_n_iso,
                            "shift_from": s1_name,
                            "shift_to": s2_name,
                        })
                        logger.warning(f"[SOLVER WORKER REST VIOLATION] {rv_msg} [tenant:{tid}].")

        coverage_pct = (
            round((len(generated_items) / total_required_slots) * 100.0, 1)
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
            "total_assigned_slots": len(generated_items),
            "coverage_pct": coverage_pct,
            "deficit_explanations": deficit_explanations,
            "deficit_details": deficit_details,
            "employee_summary_log": employee_summary,
            "employee_summaries": employee_summaries,
            "rest_violations": rest_violations,
            "domain_logs": domain_logs,
        }

        return {
            "job_id": payload.job_id,
            "status": "success",
            "count": len(generated_items),
            "schedules": generated_items,
            "warnings": warnings,
            "weekly_targets": payload.weekly_targets,
            "solver_explanation": solver_explanation,
        }
    else:
        err_msg = (
            f"Solver nie znalazł dopuszczalnego grafiku (status={status_name}) "
            f"w {solve_duration:.2f}s dla okresu {start_date} - {end_date}."
        )
        logger.error(f"[SOLVER WORKER ANOMALY] {err_msg} [tenant:{tid}].")
        return {
            "job_id": payload.job_id,
            "status": "infeasible",
            "count": 0,
            "schedules": [],
            "warnings": [],
            "weekly_targets": payload.weekly_targets,
            "solver_explanation": {
                "solver_status": status_name,
                "solve_duration_sec": round(solve_duration, 4),
                "variables_count": len(work),
                "objective_terms_count": len(objective_terms),
                "objective_value": 0.0,
                "total_required_slots": total_required_slots,
                "total_assigned_slots": 0,
                "coverage_pct": 0.0,
                "deficit_explanations": [],
                "deficit_details": {},
                "employee_summary_log": {},
                "employee_summaries": [],
                "rest_violations": [],
                "domain_logs": [err_msg],
            },
        }


class SolverService:
    """
    Fasada silnika OR-Tools CP-SAT:
    - W trybie Pure-Compute (`solve_payload` lub `session=None`) działa całkowicie bez bazy danych.
    - W trybie kompatybilności z backendem (`solve(start_date, end_date, ...)`) deleguje pobranie danych
      i zapis wyników do `SchedulerService`, a obliczenia wykonuje przez `solve_from_payload(payload)`.
    """

    def __init__(self, session: Any = None, tenant_id: Optional[int] = None):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def solve_payload(payload: Union[SolverJobPayload, Dict[str, Any], str]) -> Dict[str, Any]:
        """Pure-compute entrypoint (`JSON-In -> OR-Tools CP-SAT -> JSON-Out`)."""
        return solve_from_payload(payload)

    def solve(
        self,
        start_date: date,
        end_date: date,
        save: bool = True,
        weekly_targets: Optional[Dict[Any, Dict[str, Any]]] = None,
        actor: Any = None,
    ) -> Dict[str, Any]:
        if self.session is None:
            raise RuntimeError(
                "SolverService.solve(start_date, end_date) requires a database session; "
                "use solve_from_payload(payload) or SolverService.solve_payload(payload) for stateless execution."
            )
        from .scheduler_service import SchedulerService

        sched_svc = SchedulerService(self.session, tenant_id=self.tenant_id)
        payload = sched_svc.build_solver_job_payload(
            start_date=start_date,
            end_date=end_date,
            save=save,
            weekly_targets=weekly_targets,
        )
        raw_result = solve_from_payload(payload)
        return sched_svc.finalize_solver_result(
            raw_result,
            start_date=start_date,
            end_date=end_date,
            save=save,
            actor=actor,
        )
