from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..contracts.wfm import (
    WfmEmployeeDTO,
    WfmPredictionInputDTO,
    WfmPredictionOutputDTO,
    WfmRoleDTO,
    WfmScheduleItemDTO,
)

logger = logging.getLogger(__name__)

POLISH_DAY_NAMES = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]


class WFMPredictionService:
    """
    100% bezstanowy silnik domenowy WFM Workforce Prediction & Live Labor Cost Simulation (Pure Domain Engine).
    Operuje wyłącznie na kontraktach `WfmPredictionInputDTO` -> `WfmPredictionOutputDTO`,
    bez jakiegokolwiek dostępu do sesji bazy danych (`Session`) ani modeli ORM.
    """

    @staticmethod
    def _calc_shift_duration_hours(start_t: time, end_t: time, ref_date: Optional[date] = None) -> float:
        d = ref_date or date(2026, 1, 1)
        start_dt = datetime.combine(d, start_t)
        end_dt = datetime.combine(d, end_t)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).total_seconds() / 3600.0

    @staticmethod
    def _calc_end_drift_minutes(planned_start: time, planned_end: time, actual_in: time, actual_out: time) -> float:
        ref = date(2026, 1, 1)
        p_start_dt = datetime.combine(ref, planned_start)
        p_end_dt = datetime.combine(ref, planned_end)
        if p_end_dt <= p_start_dt:
            p_end_dt += timedelta(days=1)

        a_in_dt = datetime.combine(ref, actual_in)
        if (a_in_dt - p_start_dt).total_seconds() < -12 * 3600:
            a_in_dt += timedelta(days=1)
        elif (a_in_dt - p_start_dt).total_seconds() > 12 * 3600:
            a_in_dt -= timedelta(days=1)

        a_out_dt = datetime.combine(ref, actual_out)
        while a_out_dt <= a_in_dt:
            a_out_dt += timedelta(days=1)

        return (a_out_dt - p_end_dt).total_seconds() / 60.0

    @staticmethod
    def _add_minutes_to_time_str(t: time, delta_minutes: float) -> str:
        ref = datetime.combine(date(2026, 1, 1), t) + timedelta(minutes=round(delta_minutes))
        return ref.strftime("%H:%M")

    @staticmethod
    def resolve_hourly_rate(
        user: Optional[WfmEmployeeDTO],
        role_id: Optional[int] = None,
        role_map: Optional[Dict[int, WfmRoleDTO]] = None,
    ) -> float:
        if user is not None and user.hourly_rate is not None and user.hourly_rate > 0:
            return float(user.hourly_rate)
        if role_id is not None and role_map is not None:
            role = role_map.get(role_id)
            if role and role.hourly_rate is not None and role.hourly_rate > 0:
                return float(role.hourly_rate)
        if user is not None:
            if user.hourly_rate is not None:
                return float(user.hourly_rate)
            for rate in user.role_hourly_rates:
                if rate is not None and rate > 0:
                    return float(rate)
            if role_map is not None:
                for rid in user.role_ids:
                    r = role_map.get(rid)
                    if r and r.hourly_rate is not None and r.hourly_rate > 0:
                        return float(r.hourly_rate)
        return 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. Bottleneck Forecast (Availability, Leaves & Monthly Target Pool)
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def forecast_bottlenecks(cls, input_dto: WfmPredictionInputDTO) -> Dict[str, Any]:
        start_date = input_dto.start_date
        week_end = input_dto.end_date or (start_date + timedelta(days=6))
        last_day_num = monthrange(start_date.year, start_date.month)[1]
        month_start = date(start_date.year, start_date.month, 1)
        month_end = date(start_date.year, start_date.month, last_day_num)
        horizon_end = max(week_end, month_end) if input_dto.include_rest_of_month else week_end

        employees = [
            e for e in input_dto.employees
            if e.is_active and e.role_system == "EMPLOYEE"
        ]
        shifts = input_dto.shifts
        roles = input_dto.roles

        emp_ids = {e.id for e in employees}
        shift_ids = {s.id for s in shifts}
        shift_map = {s.id: s for s in shifts}
        role_map = {r.id: r for r in roles}

        shift_durations = {
            s.id: cls._calc_shift_duration_hours(s.start_time, s.end_time)
            for s in shifts
        }

        sched_start = min(month_start, start_date)
        sched_end = max(month_end, horizon_end)
        scheduled_hours_by_user: Dict[UUID, float] = defaultdict(float)
        for sch in input_dto.schedules:
            if sch.user_id not in emp_ids:
                continue
            if sched_start <= sch.date <= sched_end and month_start <= sch.date <= month_end:
                dur = shift_durations.get(sch.shift_def_id, 0.0)
                scheduled_hours_by_user[sch.user_id] += dur

        days_in_horizon = [
            start_date + timedelta(days=i)
            for i in range((horizon_end - start_date).days + 1)
        ]

        req_map: Dict[Tuple[date, int, int], int] = {}
        global_reqs = [r for r in input_dto.requirements if r.day_of_week is not None and r.shift_def_id in shift_ids]
        specific_reqs = [
            r for r in input_dto.requirements
            if r.date is not None and start_date <= r.date <= horizon_end and r.shift_def_id in shift_ids
        ]
        for d in days_in_horizon:
            dow = d.weekday()
            for gr in global_reqs:
                if gr.day_of_week == dow:
                    req_map[(d, gr.shift_def_id, gr.role_id)] = gr.min_count
        for sr in specific_reqs:
            if sr.date is not None:
                req_map[(sr.date, sr.shift_def_id, sr.role_id)] = sr.min_count

        avail_map: Dict[Tuple[UUID, date, int], str] = {}
        slot_has_explicit_available: Dict[Tuple[date, int], bool] = defaultdict(bool)
        slot_has_explicit_unavailable: Dict[Tuple[date, int], bool] = defaultdict(bool)
        for av in input_dto.availabilities:
            if av.user_id not in emp_ids:
                continue
            if not (start_date <= av.date <= horizon_end):
                continue
            st = str(av.status)
            avail_map[(av.user_id, av.date, av.shift_def_id)] = st
            if st in ("AVAILABLE", "PREFERRED"):
                slot_has_explicit_available[(av.date, av.shift_def_id)] = True
            elif st == "UNAVAILABLE":
                slot_has_explicit_unavailable[(av.date, av.shift_def_id)] = True

        leave_by_user_date: Dict[Tuple[UUID, date], bool] = {}
        for lr in input_dto.leave_requests:
            if lr.user_id not in emp_ids or lr.status != "APPROVED":
                continue
            if lr.end_date < start_date or lr.start_date > horizon_end:
                continue
            cur = max(start_date, lr.start_date)
            end_l = min(horizon_end, lr.end_date)
            while cur <= end_l:
                leave_by_user_date[(lr.user_id, cur)] = True
                cur += timedelta(days=1)

        bottlenecks: List[Dict[str, Any]] = []

        for (d, s_id, r_id), required in sorted(req_map.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            if required <= 0:
                continue
            shift = shift_map.get(s_id)
            role = role_map.get(r_id)
            if not shift or not role:
                continue

            if shift.applicable_days and d.weekday() not in shift.applicable_days:
                continue

            role_candidates = [e for e in employees if r_id in e.role_ids]

            on_leave_users: List[str] = []
            unavailable_users: List[str] = []
            available_users: List[WfmEmployeeDTO] = []
            available_within_target_users: List[WfmEmployeeDTO] = []

            has_avail_for_slot = slot_has_explicit_available[(d, s_id)]
            has_unavail_for_slot = slot_has_explicit_unavailable[(d, s_id)]
            any_leave_on_day = any(leave_by_user_date.get((c.id, d), False) for c in role_candidates)

            shift_dur = shift_durations.get(s_id, 8.0)

            for cand in role_candidates:
                if leave_by_user_date.get((cand.id, d), False):
                    on_leave_users.append(cand.full_name)
                    continue

                st = avail_map.get((cand.id, d, s_id))
                if st == "UNAVAILABLE":
                    unavailable_users.append(cand.full_name)
                    continue
                elif st in ("AVAILABLE", "PREFERRED"):
                    is_avail = True
                else:
                    if has_avail_for_slot and not has_unavail_for_slot and not any_leave_on_day:
                        unavailable_users.append(cand.full_name)
                        is_avail = False
                    else:
                        is_avail = True

                if is_avail:
                    available_users.append(cand)
                    if cand.target_hours_per_month is not None:
                        rem = cand.target_hours_per_month - scheduled_hours_by_user.get(cand.id, 0.0)
                        if rem >= shift_dur:
                            available_within_target_users.append(cand)
                    else:
                        available_within_target_users.append(cand)

            avail_cnt = len(available_users)
            avail_target_cnt = len(available_within_target_users)

            if avail_cnt < required or avail_target_cnt < required:
                day_name = POLISH_DAY_NAMES[d.weekday()]
                date_short = d.strftime("%d.%m")
                scope = "WEEK" if d <= week_end else "MONTH"

                if avail_cnt < required:
                    severity = "CRITICAL"
                    deficit = required - avail_cnt
                    msg = (
                        f"{day_name} {date_short} (Rola: {role.name}) – "
                        f"wysoka koncentracja urlopów/braków dyspozycyjności, "
                        f"dostępnych tylko {avail_cnt} z {required} wymaganych pracowników"
                    )
                else:
                    severity = "WARNING"
                    deficit = required - avail_target_cnt
                    msg = (
                        f"{day_name} {date_short} (Rola: {role.name}) – "
                        f"ryzyko przeciążenia puli godzin, dostępnych w limicie "
                        f"tylko {avail_target_cnt} z {required} wymaganych pracowników"
                    )

                bottlenecks.append({
                    "date": d.isoformat(),
                    "day_name": day_name,
                    "shift_def_id": s_id,
                    "shift_name": shift.name,
                    "role_id": r_id,
                    "role_name": role.name,
                    "required_count": required,
                    "available_count": avail_cnt,
                    "available_within_target_count": avail_target_cnt,
                    "total_role_employees": len(role_candidates),
                    "on_leave_count": len(on_leave_users),
                    "on_leave_names": on_leave_users,
                    "unavailable_count": len(unavailable_users),
                    "unavailable_names": unavailable_users,
                    "deficit": deficit,
                    "severity": severity,
                    "scope": scope,
                    "message": msg,
                })

        employee_target_risks: List[Dict[str, Any]] = []
        days_remaining_in_month = [
            d for d in days_in_horizon if month_start <= d <= month_end
        ]

        for emp in employees:
            sched_hrs = round(scheduled_hours_by_user.get(emp.id, 0.0), 2)
            target_hrs = emp.target_hours_per_month
            rem_hrs = round(max(0.0, float(target_hrs) - sched_hrs), 2) if target_hrs is not None else 0.0

            potential_remaining_hours = 0.0
            leave_days_cnt = 0
            for d in days_remaining_in_month:
                if leave_by_user_date.get((emp.id, d), False):
                    leave_days_cnt += 1
                    continue
                day_avail_durs = []
                for s in shifts:
                    st = avail_map.get((emp.id, d, s.id))
                    if st != "UNAVAILABLE":
                        day_avail_durs.append(shift_durations.get(s.id, 0.0))
                if day_avail_durs:
                    potential_remaining_hours += max(day_avail_durs)

            risk_level = "LOW"
            risk_msg = None
            if target_hrs is not None and target_hrs > 0:
                if sched_hrs > target_hrs:
                    risk_level = "OVERLOAD"
                    risk_msg = (
                        f"{emp.full_name} – przekroczono cel miesięczny: "
                        f"zaplanowano {sched_hrs:.1f}h z {target_hrs}h (+{sched_hrs - target_hrs:.1f}h nadgodzin)"
                    )
                elif rem_hrs > potential_remaining_hours:
                    risk_level = "HIGH"
                    risk_msg = (
                        f"{emp.full_name} – wysokie ryzyko niewyrobienia celu miesięcznego: "
                        f"brakuje {rem_hrs:.1f}h do celu ({target_hrs}h), a dostępność pokrywa maks. {potential_remaining_hours:.1f}h"
                    )
                elif sched_hrs < target_hrs * 0.5 and len(days_remaining_in_month) <= 10:
                    risk_level = "MEDIUM"
                    risk_msg = (
                        f"{emp.full_name} – niski stopień realizacji celu miesięcznego: "
                        f"zaplanowano {sched_hrs:.1f}h z {target_hrs}h (pozostało {rem_hrs:.1f}h)"
                    )

            employee_target_risks.append({
                "user_id": str(emp.id),
                "user_name": emp.full_name,
                "target_hours_per_month": target_hrs,
                "scheduled_hours": sched_hrs,
                "remaining_hours_to_target": rem_hrs,
                "potential_available_hours": round(potential_remaining_hours, 1),
                "leave_days_in_horizon": leave_days_cnt,
                "risk_level": risk_level,
                "message": risk_msg,
            })

        return {
            "start_date": start_date.isoformat(),
            "week_end": week_end.isoformat(),
            "horizon_end": horizon_end.isoformat(),
            "bottlenecks": bottlenecks,
            "week_bottlenecks_count": sum(1 for b in bottlenecks if b["scope"] == "WEEK"),
            "month_bottlenecks_count": sum(1 for b in bottlenecks if b["scope"] == "MONTH"),
            "employee_target_risks": employee_target_risks,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. Schedule vs. Attendance Drift Prediction
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def predict_attendance_drift(cls, input_dto: WfmPredictionInputDTO) -> Dict[str, Any]:
        ref_date = input_dto.reference_date or date.today()
        lookback_weeks = max(4, min(8, input_dto.lookback_weeks_drift))
        history_start = ref_date - timedelta(days=lookback_weeks * 7)

        employees = input_dto.employees
        shifts = input_dto.shifts
        roles = input_dto.roles

        emp_map = {e.id: e for e in employees}
        emp_ids = set(emp_map.keys())
        shift_map = {s.id: s for s in shifts}
        role_map = {r.id: r for r in roles}

        hist_schedules = [
            s for s in input_dto.schedules
            if s.user_id in emp_ids and history_start <= s.date <= ref_date
        ]
        hist_attendances = [
            a for a in input_dto.attendances
            if a.user_id in emp_ids
            and history_start <= a.date <= ref_date
            and a.status == "CONFIRMED"
        ]

        schedule_by_id: Dict[UUID, WfmScheduleItemDTO] = {
            s.id: s for s in hist_schedules if s.id is not None
        }
        schedules_by_user_date: Dict[Tuple[UUID, date], List[WfmScheduleItemDTO]] = defaultdict(list)
        for s in hist_schedules:
            schedules_by_user_date[(s.user_id, s.date)].append(s)

        shift_end_drifts: Dict[int, List[float]] = defaultdict(list)
        shift_duration_drifts: Dict[int, List[float]] = defaultdict(list)
        total_planned_hours = 0.0
        total_actual_hours = 0.0
        matched_records_count = 0

        for att in hist_attendances:
            if att.is_absent:
                continue

            matched_sched: Optional[WfmScheduleItemDTO] = None
            if att.schedule_id and att.schedule_id in schedule_by_id:
                matched_sched = schedule_by_id[att.schedule_id]
            else:
                candidates = schedules_by_user_date.get((att.user_id, att.date), [])
                if candidates:
                    matched_sched = candidates[0]

            if not matched_sched:
                continue

            shift_def = shift_map.get(matched_sched.shift_def_id)
            if not shift_def:
                continue

            planned_hrs = cls._calc_shift_duration_hours(shift_def.start_time, shift_def.end_time, att.date)
            actual_hrs = cls._calc_shift_duration_hours(att.check_in, att.check_out, att.date)
            duration_drift_min = (actual_hrs - planned_hrs) * 60.0
            end_drift_min = cls._calc_end_drift_minutes(
                shift_def.start_time, shift_def.end_time, att.check_in, att.check_out
            )

            shift_end_drifts[shift_def.id].append(end_drift_min)
            shift_duration_drifts[shift_def.id].append(duration_drift_min)
            total_planned_hours += planned_hrs
            total_actual_hours += actual_hrs
            matched_records_count += 1

        shift_drifts: List[Dict[str, Any]] = []
        for s in shifts:
            end_drifts = shift_end_drifts.get(s.id, [])
            dur_drifts = shift_duration_drifts.get(s.id, [])
            sample_cnt = len(end_drifts)

            avg_end_drift = sum(end_drifts) / sample_cnt if sample_cnt > 0 else 0.0
            avg_dur_drift = sum(dur_drifts) / sample_cnt if sample_cnt > 0 else 0.0
            planned_end_str = s.end_time.strftime("%H:%M")
            planned_start_str = s.start_time.strftime("%H:%M")
            avg_actual_end_str = cls._add_minutes_to_time_str(s.end_time, avg_end_drift)

            is_drifting = sample_cnt > 0 and (avg_end_drift >= 15.0 or avg_dur_drift >= 15.0)
            msg = None
            if is_drifting:
                drift_display = int(round(max(avg_end_drift, avg_dur_drift)))
                msg = (
                    f"Zmiana '{s.name}' ({planned_start_str}–{planned_end_str}) "
                    f"realnie kończona średnio o {avg_actual_end_str} (+{drift_display} min)"
                )

            shift_drifts.append({
                "shift_def_id": s.id,
                "shift_name": s.name,
                "planned_start_time": planned_start_str,
                "planned_end_time": planned_end_str,
                "avg_actual_end_time": avg_actual_end_str,
                "avg_end_drift_minutes": round(avg_end_drift, 1),
                "avg_duration_drift_minutes": round(avg_dur_drift, 1),
                "sample_count": sample_cnt,
                "is_drifting": is_drifting,
                "message": msg,
            })

        shift_drifts.sort(key=lambda x: x["avg_end_drift_minutes"], reverse=True)

        drift_hours_ratio = (
            total_actual_hours / total_planned_hours
            if total_planned_hours > 0
            else 1.0
        )
        avg_drift_minutes_overall = (
            ((total_actual_hours - total_planned_hours) * 60.0) / matched_records_count
            if matched_records_count > 0
            else 0.0
        )

        month_start = date(ref_date.year, ref_date.month, 1)
        month_end = date(ref_date.year, ref_date.month, monthrange(ref_date.year, ref_date.month)[1])
        month_schedules = [
            s for s in input_dto.schedules
            if s.user_id in emp_ids and month_start <= s.date <= month_end
        ]

        drift_map_by_shift = {
            sd["shift_def_id"]: sd["avg_duration_drift_minutes"] / 60.0
            for sd in shift_drifts
        }

        month_planned_hours = 0.0
        month_projected_hours = 0.0
        month_planned_cost = 0.0
        month_projected_cost = 0.0

        for sch in month_schedules:
            sh = shift_map.get(sch.shift_def_id)
            if not sh:
                continue
            u = emp_map.get(sch.user_id)
            rate = cls.resolve_hourly_rate(u, sch.role_id, role_map)
            p_hrs = cls._calc_shift_duration_hours(sh.start_time, sh.end_time, sch.date)

            shift_drift_hrs = drift_map_by_shift.get(sch.shift_def_id, 0.0)
            if shift_drift_hrs == 0.0 and matched_records_count > 0 and drift_hours_ratio > 1.0:
                shift_drift_hrs = p_hrs * (drift_hours_ratio - 1.0)
            proj_hrs = max(p_hrs, p_hrs + max(0.0, shift_drift_hrs))

            month_planned_hours += p_hrs
            month_projected_hours += proj_hrs
            month_planned_cost += p_hrs * rate
            month_projected_cost += proj_hrs * rate

        return {
            "lookback_weeks": lookback_weeks,
            "history_start": history_start.isoformat(),
            "reference_date": ref_date.isoformat(),
            "matched_records_count": matched_records_count,
            "total_historical_planned_hours": round(total_planned_hours, 2),
            "total_historical_actual_hours": round(total_actual_hours, 2),
            "avg_drift_minutes_per_shift": round(avg_drift_minutes_overall, 1),
            "drift_hours_ratio": round(drift_hours_ratio, 4),
            "shift_drifts": shift_drifts,
            "drifting_shifts": [sd for sd in shift_drifts if sd["is_drifting"]],
            "monthly_projection": {
                "month": f"{ref_date.year}-{ref_date.month:02d}",
                "planned_hours": round(month_planned_hours, 2),
                "projected_actual_hours": round(month_projected_hours, 2),
                "projected_overtime_drift_hours": round(max(0.0, month_projected_hours - month_planned_hours), 2),
                "planned_cost": round(month_planned_cost, 2),
                "projected_actual_cost": round(month_projected_cost, 2),
                "projected_cost_drift_delta": round(max(0.0, month_projected_cost - month_planned_cost), 2),
            },
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. Shift Stability Analysis (ShiftGiveaway / Rotation)
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def analyze_shift_stability(cls, input_dto: WfmPredictionInputDTO) -> Dict[str, Any]:
        ref_date = input_dto.reference_date or date.today()
        history_start = ref_date - timedelta(days=input_dto.lookback_weeks_stability * 7)
        horizon_end = ref_date + timedelta(days=30)

        emp_ids = {e.id for e in input_dto.employees}
        shift_map = {s.id: s for s in input_dto.shifts}

        giveaways = [g for g in input_dto.giveaways if g.offered_by in emp_ids]
        schedules = [
            s for s in input_dto.schedules
            if s.user_id in emp_ids and history_start <= s.date <= horizon_end
        ]

        schedule_by_id: Dict[UUID, WfmScheduleItemDTO] = {
            s.id: s for s in input_dto.schedules if s.id is not None and s.user_id in emp_ids
        }

        scheduled_count_by_slot: Dict[Tuple[int, int], int] = defaultdict(int)
        for s in schedules:
            scheduled_count_by_slot[(s.shift_def_id, s.date.weekday())] += 1

        giveaways_by_slot: Dict[Tuple[int, int], int] = defaultdict(int)
        giveaways_by_weekday: Dict[int, int] = defaultdict(int)
        giveaways_by_shift: Dict[int, int] = defaultdict(int)

        for g in giveaways:
            sch = schedule_by_id.get(g.schedule_id)
            if not sch:
                continue
            dow = sch.date.weekday()
            giveaways_by_slot[(sch.shift_def_id, dow)] += 1
            giveaways_by_weekday[dow] += 1
            giveaways_by_shift[sch.shift_def_id] += 1

        hotspots: List[Dict[str, Any]] = []
        for (s_id, dow), g_count in giveaways_by_slot.items():
            sh = shift_map.get(s_id)
            s_name = sh.name if sh else f"Zmiana #{s_id}"
            day_name = POLISH_DAY_NAMES[dow]
            sched_cnt = max(g_count, scheduled_count_by_slot.get((s_id, dow), g_count))
            rate_pct = round((g_count / sched_cnt) * 100.0, 1) if sched_cnt > 0 else 0.0
            hotspots.append({
                "shift_def_id": s_id,
                "shift_name": s_name,
                "day_of_week": dow,
                "day_name": day_name,
                "giveaway_count": g_count,
                "scheduled_count": sched_cnt,
                "rotation_rate_pct": rate_pct,
                "message": (
                    f"{day_name} – zmiana '{s_name}': wysoka rotacja "
                    f"(wystawiono na giełdę {g_count}x, wskaźnik rezygnacji {rate_pct:.0f}%)"
                ),
            })

        hotspots.sort(key=lambda x: (x["giveaway_count"], x["rotation_rate_pct"]), reverse=True)

        weekday_summary = [
            {
                "day_of_week": dow,
                "day_name": POLISH_DAY_NAMES[dow],
                "giveaway_count": giveaways_by_weekday.get(dow, 0),
            }
            for dow in range(7)
        ]

        return {
            "total_giveaways": sum(giveaways_by_slot.values()),
            "hotspots": hotspots,
            "weekday_summary": weekday_summary,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  4. Live Labor Cost Simulator
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def simulate_labor_cost(cls, input_dto: WfmPredictionInputDTO) -> Dict[str, Any]:
        start_date = input_dto.start_date
        end_date = input_dto.end_date or (start_date + timedelta(days=6))

        employees = input_dto.employees
        shifts = input_dto.shifts
        roles = input_dto.roles

        emp_map = {str(e.id): e for e in employees}
        emp_uuids = {e.id for e in employees}
        shift_map = {s.id: s for s in shifts}
        role_map = {r.id: r for r in roles}

        drift_report = cls.predict_attendance_drift(input_dto)
        shift_drift_hours_map: Dict[int, float] = {}
        for sd in drift_report.get("shift_drifts", []):
            drift_min = max(
                float(sd.get("avg_duration_drift_minutes", 0.0)),
                float(sd.get("avg_end_drift_minutes", 0.0)),
            )
            shift_drift_hours_map[int(sd["shift_def_id"])] = max(0.0, drift_min / 60.0)

        overall_drift_ratio = max(1.0, float(drift_report.get("drift_hours_ratio", 1.0)))

        normalized_entries: List[Dict[str, Any]] = []
        if input_dto.draft_entries is not None:
            for item in input_dto.draft_entries:
                if isinstance(item, dict):
                    d_val = item.get("date")
                    if isinstance(d_val, str):
                        d_val = date.fromisoformat(d_val.split("T")[0])
                    normalized_entries.append({
                        "date": d_val,
                        "shift_def_id": int(item["shift_def_id"]),
                        "user_id": str(item["user_id"]),
                        "role_id": int(item["role_id"]),
                    })
                else:
                    normalized_entries.append({
                        "date": getattr(item, "date"),
                        "shift_def_id": int(getattr(item, "shift_def_id")),
                        "user_id": str(getattr(item, "user_id")),
                        "role_id": int(getattr(item, "role_id")),
                    })
        else:
            for s in input_dto.schedules:
                if s.user_id in emp_uuids and start_date <= s.date <= end_date:
                    normalized_entries.append({
                        "date": s.date,
                        "shift_def_id": s.shift_def_id,
                        "user_id": str(s.user_id),
                        "role_id": s.role_id,
                    })

        total_planned_hours = 0.0
        total_projected_hours = 0.0
        estimated_planned_cost = 0.0
        projected_cost_with_drift = 0.0

        role_stats: Dict[int, Dict[str, Any]] = {}
        for r in roles:
            role_stats[r.id] = {
                "role_id": r.id,
                "role_name": r.name,
                "color_hex": r.color_hex,
                "planned_hours": 0.0,
                "projected_hours_with_drift": 0.0,
                "planned_cost": 0.0,
                "projected_cost_with_drift": 0.0,
                "shifts_count": 0,
            }

        days_count = max(0, (end_date - start_date).days + 1)
        daily_stats: Dict[date, Dict[str, Any]] = {}
        for i in range(days_count):
            d = start_date + timedelta(days=i)
            daily_stats[d] = {
                "date": d.isoformat(),
                "day_of_week": d.weekday(),
                "day_name": POLISH_DAY_NAMES[d.weekday()],
                "planned_hours": 0.0,
                "projected_hours_with_drift": 0.0,
                "planned_cost": 0.0,
                "projected_cost_with_drift": 0.0,
                "shifts_count": 0,
                "is_most_expensive": False,
            }

        for entry in normalized_entries:
            d = entry["date"]
            s_id = entry["shift_def_id"]
            u_id = entry["user_id"]
            r_id = entry["role_id"]

            sh = shift_map.get(s_id)
            if not sh:
                continue
            u = emp_map.get(u_id)
            rate = cls.resolve_hourly_rate(u, r_id, role_map)
            p_hrs = cls._calc_shift_duration_hours(sh.start_time, sh.end_time, d)

            s_drift_hrs = shift_drift_hours_map.get(s_id, 0.0)
            if s_drift_hrs == 0.0 and overall_drift_ratio > 1.0:
                s_drift_hrs = p_hrs * (overall_drift_ratio - 1.0)
            proj_hrs = p_hrs + s_drift_hrs

            p_cost = p_hrs * rate
            proj_cost = proj_hrs * rate

            total_planned_hours += p_hrs
            total_projected_hours += proj_hrs
            estimated_planned_cost += p_cost
            projected_cost_with_drift += proj_cost

            if r_id not in role_stats:
                r_obj = role_map.get(r_id)
                role_stats[r_id] = {
                    "role_id": r_id,
                    "role_name": r_obj.name if r_obj else f"Rola #{r_id}",
                    "color_hex": r_obj.color_hex if r_obj else "#607D8B",
                    "planned_hours": 0.0,
                    "projected_hours_with_drift": 0.0,
                    "planned_cost": 0.0,
                    "projected_cost_with_drift": 0.0,
                    "shifts_count": 0,
                }
            role_stats[r_id]["planned_hours"] += p_hrs
            role_stats[r_id]["projected_hours_with_drift"] += proj_hrs
            role_stats[r_id]["planned_cost"] += p_cost
            role_stats[r_id]["projected_cost_with_drift"] += proj_cost
            role_stats[r_id]["shifts_count"] += 1

            if d in daily_stats:
                daily_stats[d]["planned_hours"] += p_hrs
                daily_stats[d]["projected_hours_with_drift"] += proj_hrs
                daily_stats[d]["planned_cost"] += p_cost
                daily_stats[d]["projected_cost_with_drift"] += proj_cost
                daily_stats[d]["shifts_count"] += 1

        hours_by_role = [
            {
                "role_id": rs["role_id"],
                "role_name": rs["role_name"],
                "color_hex": rs["color_hex"],
                "planned_hours": round(rs["planned_hours"], 2),
                "projected_hours_with_drift": round(rs["projected_hours_with_drift"], 2),
                "planned_cost": round(rs["planned_cost"], 2),
                "projected_cost_with_drift": round(rs["projected_cost_with_drift"], 2),
                "shifts_count": rs["shifts_count"],
            }
            for rs in role_stats.values()
        ]
        hours_by_role.sort(key=lambda x: x["planned_hours"], reverse=True)

        daily_costs = []
        max_daily_cost = max((ds["planned_cost"] for ds in daily_stats.values()), default=0.0)
        for d in sorted(daily_stats.keys()):
            ds = daily_stats[d]
            is_max = max_daily_cost > 0 and abs(ds["planned_cost"] - max_daily_cost) < 1e-4
            daily_costs.append({
                "date": ds["date"],
                "day_of_week": ds["day_of_week"],
                "day_name": ds["day_name"],
                "planned_hours": round(ds["planned_hours"], 2),
                "projected_hours_with_drift": round(ds["projected_hours_with_drift"], 2),
                "planned_cost": round(ds["planned_cost"], 2),
                "projected_cost_with_drift": round(ds["projected_cost_with_drift"], 2),
                "shifts_count": ds["shifts_count"],
                "is_most_expensive": is_max,
            })

        avg_hourly_cost = (
            round(estimated_planned_cost / total_planned_hours, 2)
            if total_planned_hours > 0
            else 0.0
        )

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_planned_hours": round(total_planned_hours, 2),
            "total_projected_hours_with_drift": round(total_projected_hours, 2),
            "estimated_planned_cost": round(estimated_planned_cost, 2),
            "projected_cost_with_drift": round(projected_cost_with_drift, 2),
            "drift_cost_delta": round(projected_cost_with_drift - estimated_planned_cost, 2),
            "avg_hourly_cost": avg_hourly_cost,
            "hours_by_role": hours_by_role,
            "daily_costs": daily_costs,
            "shift_drift_hours_map": {str(k): round(v, 4) for k, v in shift_drift_hours_map.items()},
            "overall_drift_ratio": round(overall_drift_ratio, 4),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  5. Combined WFM Analytics & Prediction Payload
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def get_full_wfm_prediction_report(cls, input_dto: WfmPredictionInputDTO) -> WfmPredictionOutputDTO:
        week_end = input_dto.end_date or (input_dto.start_date + timedelta(days=6))
        scoped_dto = input_dto.model_copy(update={"end_date": week_end})
        bottleneck_data = cls.forecast_bottlenecks(scoped_dto)
        drift_data = cls.predict_attendance_drift(scoped_dto)
        stability_data = cls.analyze_shift_stability(scoped_dto)
        cost_sim = cls.simulate_labor_cost(scoped_dto)

        return WfmPredictionOutputDTO(
            start_date=input_dto.start_date.isoformat(),
            end_date=week_end.isoformat(),
            bottleneck_forecast=bottleneck_data,
            attendance_drift=drift_data,
            shift_stability=stability_data,
            labor_cost_simulation=cost_sim,
        )
