"""
Scenario tests for Issue #24 solver logic:
- Soft progressive monthly overtime & under-target prioritization
- Cross-month boundary counter reset & lookahead separation
- Regeneration idempotency (no double-counting MTD hours)
- Multi-role bottleneck resolution
- Strict enforcement of hard constraints C1-C3
- OVER_TARGET_WARNING decisions, domain_logs, and warnings
"""
from datetime import date, time, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.auth_utils import get_password_hash
from app.contracts.wfm import (
    SolverAvailabilityItem,
    SolverEmployeeItem,
    SolverInputDTO,
    SolverLeaveDayItem,
    SolverRequirementItem,
    SolverRoleItem,
    SolverShiftItem,
)
from app.models import (
    Availability,
    AvailabilityStatus,
    JobRole,
    RoleSystem,
    Schedule,
    ShiftDefinition,
    StaffingRequirement,
    User,
    UserJobRoleLink,
)
from app.services.scheduler_service import SchedulerService
from app.services.solver import SolverService


def test_slight_overtime_preferred_over_empty_shift():
    """
    A sole available employee at 158h/160h must be assigned a 7.5h shift (+5.5h overtime)
    rather than leaving the shift unstaffed, and an OVER_TARGET_WARNING must be emitted.
    """
    target_day = "2026-11-18"
    input_dto = SolverInputDTO(
        start_date=target_day,
        end_date=target_day,
        shifts=[SolverShiftItem(id=1, name="Ranna", start_time="08:00", end_time="15:30")],
        roles=[SolverRoleItem(id=10, name="Kelner")],
        employees=[
            SolverEmployeeItem(
                id="emp-over",
                full_name="Anna Kowalska",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=158.0,
                monthly_hours_by_month={"2026-11": 158.0},
            )
        ],
        requirements=[
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=10, min_count=1)
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-over", date=target_day, shift_def_id=1, status="AVAILABLE")
        ],
    )

    result = SolverService.solve(input_dto)

    assert result.status == "success"
    assert result.count == 1
    assert result.schedules[0].user_id == "emp-over"

    expected_msg = (
        "Obsadzono: Anna Kowalska (UWAGA: przekroczono cel miesięczny o +5.5h; "
        "łącznie 165.5h / 160.0h w miesiącu 2026-11)."
    )
    over_decisions = [d for d in result.decisions if d.category == "OVER_TARGET_WARNING"]
    assert len(over_decisions) == 1
    assert over_decisions[0].message == expected_msg
    assert over_decisions[0].details == {
        "over_hours": 5.5,
        "total_month_hours": 165.5,
        "target_hours": 160.0,
        "month": "2026-11",
    }
    assert any(
        d.category == "OVER_TARGET_WARNING" and d.message == expected_msg
        for d in result.solver_explanation.decisions
    )
    assert expected_msg in result.solver_explanation.domain_logs
    assert any(
        (w == expected_msg) or (isinstance(w, dict) and w.get("message") == expected_msg)
        for w in result.warnings
    )


def test_least_overtime_candidate_selected():
    """
    When all available candidates will exceed their monthly target, the solver must
    select the candidate with the lowest progressive overtime cost (158h/160h over 231h/120h).
    """
    target_day = "2026-11-18"
    input_dto = SolverInputDTO(
        start_date=target_day,
        end_date=target_day,
        shifts=[SolverShiftItem(id=1, name="Dzienna", start_time="08:00", end_time="15:30")],
        roles=[SolverRoleItem(id=10, name="Barista")],
        employees=[
            SolverEmployeeItem(
                id="emp-heavy-over",
                full_name="Marek Nadgodzinowy",
                role_ids=[10],
                target_hours_per_month=120.0,
                worked_or_scheduled_hours=231.0,
                monthly_hours_by_month={"2026-11": 231.0},
            ),
            SolverEmployeeItem(
                id="emp-light-over",
                full_name="Kasia Lekka",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=158.0,
                monthly_hours_by_month={"2026-11": 158.0},
            ),
        ],
        requirements=[
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=10, min_count=1)
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-heavy-over", date=target_day, shift_def_id=1, status="PREFERRED"),
            SolverAvailabilityItem(user_id="emp-light-over", date=target_day, shift_def_id=1, status="AVAILABLE"),
        ],
    )

    result = SolverService.solve(input_dto)

    assert result.status == "success"
    assert result.count == 1
    assert result.schedules[0].user_id == "emp-light-over"


def test_under_target_employee_prioritized_over_at_target():
    """
    An under-target employee (100h/160h) must win over both a near-target employee (156h/160h)
    and an at-target employee (160h/160h), even when weekly targets are omitted or equal.
    """
    target_day = "2026-11-18"
    # Case 1: 100h/160h vs 156h/160h (without precomputed effective_weekly_target_minutes)
    dto_near = SolverInputDTO(
        start_date=target_day,
        end_date=target_day,
        shifts=[SolverShiftItem(id=1, name="Dzienna", start_time="08:00", end_time="15:30")],
        roles=[SolverRoleItem(id=10, name="Kelner")],
        employees=[
            SolverEmployeeItem(
                id="emp-near",
                full_name="Blisko Celu",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=156.0,
            ),
            SolverEmployeeItem(
                id="emp-under",
                full_name="Pod Celem",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=100.0,
            ),
        ],
        requirements=[
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=10, min_count=1)
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-near", date=target_day, shift_def_id=1, status="AVAILABLE"),
            SolverAvailabilityItem(user_id="emp-under", date=target_day, shift_def_id=1, status="AVAILABLE"),
        ],
    )
    res_near = SolverService.solve(dto_near)
    assert res_near.status == "success"
    assert res_near.count == 1
    assert res_near.schedules[0].user_id == "emp-under"

    # Case 2: 100h/160h vs 160h/160h even with equal explicit effective_weekly_target_minutes
    dto_at = SolverInputDTO(
        start_date=target_day,
        end_date=target_day,
        shifts=[SolverShiftItem(id=1, name="Dzienna", start_time="08:00", end_time="15:30")],
        roles=[SolverRoleItem(id=10, name="Kelner")],
        employees=[
            SolverEmployeeItem(
                id="emp-at",
                full_name="Na Celu",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=160.0,
                effective_weekly_target_hours=40.0,
                effective_weekly_target_minutes=2400,
            ),
            SolverEmployeeItem(
                id="emp-under",
                full_name="Pod Celem",
                role_ids=[10],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=100.0,
                effective_weekly_target_hours=40.0,
                effective_weekly_target_minutes=2400,
            ),
        ],
        requirements=[
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=10, min_count=1)
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-at", date=target_day, shift_def_id=1, status="AVAILABLE"),
            SolverAvailabilityItem(user_id="emp-under", date=target_day, shift_def_id=1, status="AVAILABLE"),
        ],
    )
    res_at = SolverService.solve(dto_at)
    assert res_at.status == "success"
    assert res_at.count == 1
    assert res_at.schedules[0].user_id == "emp-under"


@pytest.mark.parametrize(
    "week_start,week_end,prev_month_days,old_ym,new_ym",
    [
        (
            date(2026, 11, 30),
            date(2026, 12, 6),
            [date(2026, 11, d) for d in range(1, 21)],  # 20 * 8h = 160h in Nov 2026
            "2026-11",
            "2026-12",
        ),
        (
            date(2026, 12, 28),
            date(2027, 1, 3),
            [date(2026, 12, d) for d in range(1, 21)],  # 20 * 8h = 160h in Dec 2026
            "2026-12",
            "2027-01",
        ),
    ],
)
def test_cross_month_week_resets_monthly_counter(
    session: Session,
    test_tenant,
    week_start: date,
    week_end: date,
    prev_month_days: list[date],
    old_ym: str,
    new_ym: str,
):
    """
    Cross-month weeks (2026-11-30..2026-12-06 and 2026-12-28..2027-01-03) must track MTD
    hours strictly per calendar month, so 160h worked in the old month does NOT leak into
    the new month's counter or cause false OVER_TARGET_WARNING on new-month shifts.
    """
    role = JobRole(tenant_id=test_tenant.id, name=f"KelnerCross_{uuid4().hex[:4]}", color_hex="#112233")
    shift = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana 8h",
        start_time=time(8, 0),
        end_time=time(16, 0),
    )
    emp_a = User(
        tenant_id=test_tenant.id,
        username=f"cross_a_{uuid4().hex[:6]}",
        password_hash=get_password_hash("Pass1234"),
        full_name="Pracownik A (pełny stary miesiąc)",
        role_system=RoleSystem.EMPLOYEE,
        target_hours_per_month=160,
        is_active=True,
    )
    emp_b = User(
        tenant_id=test_tenant.id,
        username=f"cross_b_{uuid4().hex[:6]}",
        password_hash=get_password_hash("Pass1234"),
        full_name="Pracownik B (pełny nowy miesiąc)",
        role_system=RoleSystem.EMPLOYEE,
        target_hours_per_month=160,
        is_active=True,
    )
    session.add_all([role, shift, emp_a, emp_b])
    session.commit()
    session.refresh(role)
    session.refresh(shift)
    session.refresh(emp_a)
    session.refresh(emp_b)

    session.add(UserJobRoleLink(user_id=emp_a.id, role_id=role.id))
    session.add(UserJobRoleLink(user_id=emp_b.id, role_id=role.id))

    # Employee A already has 160h (20 * 8h) in old_ym (outside [week_start, week_end])
    for d in prev_month_days:
        session.add(Schedule(date=d, shift_def_id=shift.id, user_id=emp_a.id, role_id=role.id, is_published=True))

    # Employee B already has 160h in new_ym AFTER week_end (e.g. Jan 4..23 / Dec 7..26)
    new_m_start = week_end + timedelta(days=1)
    for offset in range(20):
        session.add(
            Schedule(
                date=new_m_start + timedelta(days=offset),
                shift_def_id=shift.id,
                user_id=emp_b.id,
                role_id=role.id,
                is_published=True,
            )
        )

    # Requirements & availabilities across the cross-month week (1 slot per day)
    cur = week_start
    while cur <= week_end:
        session.add(StaffingRequirement(date=cur, shift_def_id=shift.id, role_id=role.id, min_count=1))
        session.add(Availability(user_id=emp_a.id, date=cur, shift_def_id=shift.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=emp_b.id, date=cur, shift_def_id=shift.id, status=AvailabilityStatus.AVAILABLE))
        cur += timedelta(days=1)
    session.commit()

    svc = SchedulerService(session, tenant_id=test_tenant.id)
    wt = svc.compute_weekly_targets(week_start, week_end)

    assert wt[emp_a.id]["monthly_hours_by_month"] == {old_ym: 160.0, new_ym: 0.0}
    assert wt[emp_b.id]["monthly_hours_by_month"] == {old_ym: 0.0, new_ym: 160.0}

    payload = svc.build_solver_job_payload(week_start, week_end, weekly_targets=wt)
    result = SolverService.solve(payload)

    assert result.status == "success"
    assert result.count == 7  # all 7 days filled

    # On old_ym days, emp_b (0h in old_ym) must be picked over emp_a (160h in old_ym).
    # On new_ym days, emp_a (0h in new_ym) must be picked over emp_b (160h in new_ym).
    for sched in result.schedules:
        if sched.date.startswith(old_ym):
            assert sched.user_id == str(emp_b.id)
        else:
            assert sched.date.startswith(new_ym)
            assert sched.user_id == str(emp_a.id)

    # Neither month exceeds 160h, so zero OVER_TARGET_WARNING decisions!
    over_warnings = [d for d in result.decisions if d.category == "OVER_TARGET_WARNING"]
    assert over_warnings == []


def test_regeneration_idempotency_no_double_mtd_counting(session: Session, test_tenant):
    """
    Regenerating the same week [start_date, end_date] multiple times with save=True must
    strictly exclude schedules inside [start_date, end_date] from MTD hours so MTD is never
    double-counted.
    """
    role = JobRole(tenant_id=test_tenant.id, name=f"KucharzIdem_{uuid4().hex[:4]}", color_hex="#334455")
    shift = ShiftDefinition(
        tenant_id=test_tenant.id,
        name="Zmiana 8h",
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    emp = User(
        tenant_id=test_tenant.id,
        username=f"idem_{uuid4().hex[:6]}",
        password_hash=get_password_hash("Pass1234"),
        full_name="Jan Idempotentny",
        role_system=RoleSystem.EMPLOYEE,
        target_hours_per_month=160,
        is_active=True,
    )
    session.add_all([role, shift, emp])
    session.commit()
    session.refresh(role)
    session.refresh(shift)
    session.refresh(emp)

    session.add(UserJobRoleLink(user_id=emp.id, role_id=role.id))

    # 80h (10 shifts * 8h) already scheduled in Nov 1..10 (outside target week Nov 16..22)
    for d in range(1, 11):
        session.add(
            Schedule(
                date=date(2026, 11, d),
                shift_def_id=shift.id,
                user_id=emp.id,
                role_id=role.id,
                is_published=True,
            )
        )

    week_start = date(2026, 11, 16)
    week_end = date(2026, 11, 22)
    for offset in range(5):  # Mon-Fri
        d = week_start + timedelta(days=offset)
        session.add(StaffingRequirement(date=d, shift_def_id=shift.id, role_id=role.id, min_count=1))
        session.add(Availability(user_id=emp.id, date=d, shift_def_id=shift.id, status=AvailabilityStatus.AVAILABLE))
    session.commit()

    svc = SchedulerService(session, tenant_id=test_tenant.id)

    res1 = svc.solve_schedule(week_start, week_end, save=True)
    wt_after_1 = svc.compute_weekly_targets(week_start, week_end)

    res2 = svc.solve_schedule(week_start, week_end, save=True)
    wt_after_2 = svc.compute_weekly_targets(week_start, week_end)

    res3 = svc.solve_schedule(week_start, week_end, save=True)
    wt_after_3 = svc.compute_weekly_targets(week_start, week_end)

    assert res1["count"] == res2["count"] == res3["count"] == 5
    for wt in (wt_after_1, wt_after_2, wt_after_3):
        assert wt[emp.id]["worked_or_scheduled_hours"] == 80.0
        assert wt[emp.id]["monthly_hours_by_month"] == {"2026-11": 80.0}
        assert wt[emp.id]["remaining_monthly_target"] == 80.0


def test_multi_role_bottleneck_resolution():
    """
    Employee A (158h/160h, roles=[Barman, Kelner]) and Employee B (100h/160h, roles=[Kelner]).
    When 1 Barman and 1 Kelner are needed on the same shift, A must fill Barman (even with slight
    overtime) and B must fill Kelner for 100% coverage.
    """
    target_day = "2026-11-18"
    input_dto = SolverInputDTO(
        start_date=target_day,
        end_date=target_day,
        shifts=[SolverShiftItem(id=1, name="Wieczorna", start_time="14:00", end_time="22:00")],
        roles=[
            SolverRoleItem(id=1, name="Barman"),
            SolverRoleItem(id=2, name="Kelner"),
        ],
        employees=[
            SolverEmployeeItem(
                id="emp-multi",
                full_name="Alex Dwurolowy",
                role_ids=[1, 2],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=158.0,
                monthly_hours_by_month={"2026-11": 158.0},
            ),
            SolverEmployeeItem(
                id="emp-kelner",
                full_name="Beata Kelnerka",
                role_ids=[2],
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=100.0,
                monthly_hours_by_month={"2026-11": 100.0},
            ),
        ],
        requirements=[
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=1, min_count=1),
            SolverRequirementItem(date=target_day, shift_def_id=1, role_id=2, min_count=1),
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-multi", date=target_day, shift_def_id=1, status="AVAILABLE"),
            SolverAvailabilityItem(user_id="emp-kelner", date=target_day, shift_def_id=1, status="AVAILABLE"),
        ],
    )

    result = SolverService.solve(input_dto)

    assert result.status == "success"
    assert result.count == 2
    by_role = {s.role_id: s.user_id for s in result.schedules}
    assert by_role[1] == "emp-multi"
    assert by_role[2] == "emp-kelner"


def test_hard_constraints_never_violated_despite_soft_overtime():
    """
    Even though slot filling dominates soft overtime penalties, hard constraints C1 (no overlapping
    shifts), C2 (UNAVAILABLE, UNKNOWN, approved leave_days), and C3 (role match & min_count)
    must NEVER be violated.
    """
    d1 = "2026-11-18"
    d2 = "2026-11-19"
    d3 = "2026-11-20"
    input_dto = SolverInputDTO(
        start_date=d1,
        end_date=d3,
        shifts=[
            SolverShiftItem(id=1, name="Ranna", start_time="08:00", end_time="16:00"),
            SolverShiftItem(id=2, name="Nakładająca", start_time="12:00", end_time="20:00"),
        ],
        roles=[
            SolverRoleItem(id=10, name="Kucharz"),
            SolverRoleItem(id=20, name="Barman"),
        ],
        employees=[
            SolverEmployeeItem(
                id="emp-1",
                full_name="Piotr Twardy",
                role_ids=[10],  # lacks role 20 (Barman)
                target_hours_per_month=160.0,
                worked_or_scheduled_hours=100.0,
            )
        ],
        requirements=[
            # d1: both overlapping shifts for role 10 -> at most 1 can be assigned (C1)
            SolverRequirementItem(date=d1, shift_def_id=1, role_id=10, min_count=1),
            SolverRequirementItem(date=d1, shift_def_id=2, role_id=10, min_count=1),
            # d1: Barman required, emp-1 lacks role 20 -> 0 assigned (C3)
            SolverRequirementItem(date=d1, shift_def_id=1, role_id=20, min_count=1),
            # d2: emp-1 is UNAVAILABLE -> 0 assigned (C2)
            SolverRequirementItem(date=d2, shift_def_id=1, role_id=10, min_count=1),
            # d3: emp-1 has APPROVED leave -> 0 assigned despite PREFERRED (C2)
            SolverRequirementItem(date=d3, shift_def_id=1, role_id=10, min_count=1),
        ],
        availabilities=[
            SolverAvailabilityItem(user_id="emp-1", date=d1, shift_def_id=1, status="AVAILABLE"),
            SolverAvailabilityItem(user_id="emp-1", date=d1, shift_def_id=2, status="AVAILABLE"),
            SolverAvailabilityItem(user_id="emp-1", date=d2, shift_def_id=1, status="UNAVAILABLE"),
            SolverAvailabilityItem(user_id="emp-1", date=d3, shift_def_id=1, status="PREFERRED"),
        ],
        leave_days=[
            SolverLeaveDayItem(user_id="emp-1", date=d3),
        ],
    )

    result = SolverService.solve(input_dto)

    assert result.status == "success"
    assert result.count == 1
    assert result.schedules[0].date == d1
    assert result.schedules[0].role_id == 10
    assert result.schedules[0].user_id == "emp-1"
