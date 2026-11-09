from datetime import date, time, timedelta
import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.auth_utils import get_password_hash
from app.models import (
    Attendance,
    AttendanceStatus,
    Availability,
    AvailabilityStatus,
    GiveawayStatus,
    JobRole,
    LeaveRequest,
    LeaveStatus,
    RoleSystem,
    Schedule,
    ShiftAuditLog,
    ShiftDefinition,
    ShiftGiveaway,
    StaffingRequirement,
    User,
    UserJobRoleLink,
)
from app.services.wfm_prediction_service import WFMPredictionService
from app.workers.solver_worker import run_solver_job
from app.workers.wfm_analytics_worker import run_wfm_analytics_job


class TestWFMPredictionServiceUnit:
    """Unit tests for WFMPredictionService (Bottlenecks, Drift, Stability, Live Labor Cost Simulator)."""

    def test_forecast_bottlenecks_detects_leave_and_unavailability(self, session: Session, test_tenant):
        """
        Scenario: Saturday 14.11 requires 4 Waiters ('Kelner'), 4 employees have the role,
        1 is on APPROVED leave, 1 is UNAVAILABLE, 2 are AVAILABLE -> bottleneck detected (2 of 4 available).
        """
        role_waiter = JobRole(
            tenant_id=test_tenant.id,
            name="Kelner",
            color_hex="#FF5722",
            hourly_rate=30.0,
        )
        shift_evening = ShiftDefinition(
            tenant_id=test_tenant.id,
            name="Popołudniowa",
            start_time=time(14, 0),
            end_time=time(22, 0),
        )
        session.add_all([role_waiter, shift_evening])
        session.commit()
        session.refresh(role_waiter)
        session.refresh(shift_evening)

        # Target week starting Monday 2026-11-09 -> Saturday is 2026-11-14
        week_start = date(2026, 11, 9)
        target_saturday = date(2026, 11, 14)

        users = []
        for i in range(4):
            u = User(
                tenant_id=test_tenant.id,
                username=f"kelner_{i}",
                password_hash=get_password_hash("Pass1234"),
                full_name=f"Kelner {i}",
                role_system=RoleSystem.EMPLOYEE,
                target_hours_per_month=160,
                hourly_rate=30.0,
            )
            session.add(u)
            session.commit()
            session.refresh(u)
            session.add(UserJobRoleLink(user_id=u.id, role_id=role_waiter.id))
            users.append(u)
        session.commit()

        # Requirement: 4 waiters on Saturday 14.11
        session.add(
            StaffingRequirement(
                date=target_saturday,
                shift_def_id=shift_evening.id,
                role_id=role_waiter.id,
                min_count=4,
            )
        )

        # User 0: Approved leave covering Saturday 14.11
        session.add(
            LeaveRequest(
                user_id=users[0].id,
                start_date=date(2026, 11, 13),
                end_date=date(2026, 11, 15),
                reason="Urlop wypoczynkowy",
                status=LeaveStatus.APPROVED,
            )
        )
        # User 1: Explicitly UNAVAILABLE
        session.add(
            Availability(
                user_id=users[1].id,
                date=target_saturday,
                shift_def_id=shift_evening.id,
                status=AvailabilityStatus.UNAVAILABLE,
            )
        )
        # Users 2 & 3: AVAILABLE
        for u in users[2:]:
            session.add(
                Availability(
                    user_id=u.id,
                    date=target_saturday,
                    shift_def_id=shift_evening.id,
                    status=AvailabilityStatus.AVAILABLE,
                )
            )
        session.commit()

        svc = WFMPredictionService(session, tenant_id=test_tenant.id)
        report = svc.forecast_bottlenecks(start_date=week_start, end_date=week_start + timedelta(days=6))

        bottlenecks = report["bottlenecks"]
        assert len(bottlenecks) >= 1
        sat_bn = next((b for b in bottlenecks if b["date"] == target_saturday.isoformat()), None)
        assert sat_bn is not None
        assert sat_bn["role_name"] == "Kelner"
        assert sat_bn["required_count"] == 4
        assert sat_bn["available_count"] == 2
        assert sat_bn["on_leave_count"] == 1
        assert sat_bn["unavailable_count"] == 1
        assert sat_bn["deficit"] == 2
        assert sat_bn["severity"] == "CRITICAL"
        assert "Sobota 14.11 (Rola: Kelner)" in sat_bn["message"]
        assert "dostępnych tylko 2 z 4 wymaganych pracowników" in sat_bn["message"]

    def test_predict_attendance_drift_detects_late_shift_finish(self, session: Session, test_tenant):
        """
        Scenario: Shift scheduled until 20:30 regularly ends around 21:15 (+45 min drift)
        over the last 4-8 weeks. Verify average actual end time and monthly cost projection.
        """
        role_cook = JobRole(
            tenant_id=test_tenant.id,
            name="Kuchnia",
            color_hex="#4CAF50",
            hourly_rate=40.0,
        )
        shift_close = ShiftDefinition(
            tenant_id=test_tenant.id,
            name="Zamknięcie",
            start_time=time(12, 30),
            end_time=time(20, 30),  # 8.0h planned
        )
        session.add_all([role_cook, shift_close])
        session.commit()
        session.refresh(role_cook)
        session.refresh(shift_close)

        cook = User(
            tenant_id=test_tenant.id,
            username="cook_drift",
            password_hash=get_password_hash("Pass1234"),
            full_name="Kucharz Marek",
            role_system=RoleSystem.EMPLOYEE,
            hourly_rate=40.0,
        )
        session.add(cook)
        session.commit()
        session.refresh(cook)
        session.add(UserJobRoleLink(user_id=cook.id, role_id=role_cook.id))
        session.commit()

        ref_date = date(2026, 11, 9)
        # Create 6 historical shifts in the last 4 weeks where check_out is 21:15 instead of 20:30 (+45m)
        for w in range(1, 7):
            hist_date = ref_date - timedelta(days=w * 4)
            sched = Schedule(
                date=hist_date,
                shift_def_id=shift_close.id,
                user_id=cook.id,
                role_id=role_cook.id,
                is_published=True,
            )
            session.add(sched)
            session.commit()
            session.refresh(sched)

            att = Attendance(
                user_id=cook.id,
                date=hist_date,
                check_in=time(12, 30),
                check_out=time(21, 15),  # +45 minutes drift
                was_scheduled=True,
                status=AttendanceStatus.CONFIRMED,
                schedule_id=sched.id,
            )
            session.add(att)

        # Also add 2 scheduled shifts in the current month (November 2026) to verify monthly projection
        for d_day in (10, 11):
            session.add(
                Schedule(
                    date=date(2026, 11, d_day),
                    shift_def_id=shift_close.id,
                    user_id=cook.id,
                    role_id=role_cook.id,
                    is_published=True,
                )
            )
        session.commit()

        svc = WFMPredictionService(session, tenant_id=test_tenant.id)
        drift = svc.predict_attendance_drift(reference_date=ref_date, lookback_weeks=6)

        assert drift["matched_records_count"] == 6
        assert drift["avg_drift_minutes_per_shift"] == pytest.approx(45.0, abs=0.1)

        drifting_shifts = drift["drifting_shifts"]
        assert len(drifting_shifts) == 1
        ds = drifting_shifts[0]
        assert ds["shift_def_id"] == shift_close.id
        assert ds["planned_end_time"] == "20:30"
        assert ds["avg_actual_end_time"] == "21:15"
        assert ds["avg_end_drift_minutes"] == pytest.approx(45.0, abs=0.1)
        assert "21:15" in ds["message"]

        # Check monthly projection: 3 shifts in November (1 historical on Nov 5 + 2 on Nov 10, 11)
        # Each shift planned 8.0h, projected 8.75h (+0.75h) at 40 PLN/h
        proj = drift["monthly_projection"]
        assert proj["planned_hours"] > 0
        assert proj["projected_actual_hours"] > proj["planned_hours"]
        assert proj["projected_actual_cost"] > proj["planned_cost"]

    def test_analyze_shift_stability_giveaway_hotspots(self, session: Session, test_tenant):
        """Verify ShiftGiveaway rotation analysis identifies shifts & weekdays with highest resignations."""
        role = JobRole(tenant_id=test_tenant.id, name="Barman", color_hex="#9C27B0", hourly_rate=32.0)
        shift_fri = ShiftDefinition(
            tenant_id=test_tenant.id,
            name="Nocna Piątek",
            start_time=time(18, 0),
            end_time=time(2, 0),
        )
        session.add_all([role, shift_fri])
        session.commit()
        session.refresh(role)
        session.refresh(shift_fri)

        emp = User(
            tenant_id=test_tenant.id,
            username="barman_rot",
            password_hash=get_password_hash("Pass1234"),
            full_name="Barman Piotr",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(emp)
        session.commit()
        session.refresh(emp)

        # Create 3 Friday schedules and 2 giveaways on Fridays
        base_friday = date(2026, 11, 6)  # Friday
        for i in range(3):
            d = base_friday - timedelta(days=i * 7)
            sch = Schedule(
                date=d,
                shift_def_id=shift_fri.id,
                user_id=emp.id,
                role_id=role.id,
                is_published=True,
            )
            session.add(sch)
            session.commit()
            session.refresh(sch)
            if i < 2:
                session.add(
                    ShiftGiveaway(
                        schedule_id=sch.id,
                        offered_by=emp.id,
                        status=GiveawayStatus.OPEN,
                    )
                )
        session.commit()

        svc = WFMPredictionService(session, tenant_id=test_tenant.id)
        stability = svc.analyze_shift_stability(reference_date=date(2026, 11, 9))

        assert stability["total_giveaways"] == 2
        assert len(stability["hotspots"]) == 1
        top = stability["hotspots"][0]
        assert top["shift_def_id"] == shift_fri.id
        assert top["day_name"] == "Piątek"
        assert top["giveaway_count"] == 2

    def test_simulate_labor_cost_live_calculations(self, session: Session, test_tenant):
        """
        Verify Live Labor Cost Simulator:
        - Planned hours per role (Kelner vs Kuchnia)
        - Estimated planned cost (Y PLN) vs Projected cost with attendance drift (Z PLN)
        - Average hourly cost
        - Daily breakdown highlighting the most expensive day
        """
        role_waiter = JobRole(
            tenant_id=test_tenant.id, name="Kelner", color_hex="#2196F3", hourly_rate=28.0
        )
        role_kitchen = JobRole(
            tenant_id=test_tenant.id, name="Kuchnia", color_hex="#FF9800", hourly_rate=38.0
        )
        shift_8h = ShiftDefinition(
            tenant_id=test_tenant.id,
            name="Zmiana 8h",
            start_time=time(10, 0),
            end_time=time(18, 0),
        )
        session.add_all([role_waiter, shift_kitchen := role_kitchen, shift_8h])
        session.commit()
        session.refresh(role_waiter)
        session.refresh(role_kitchen)
        session.refresh(shift_8h)

        u_waiter = User(
            tenant_id=test_tenant.id,
            username="sim_waiter",
            password_hash=get_password_hash("Pass1234"),
            full_name="Kelner Anna",
            role_system=RoleSystem.EMPLOYEE,
            hourly_rate=30.0,  # personal override: 30 PLN/h
        )
        u_cook = User(
            tenant_id=test_tenant.id,
            username="sim_cook",
            password_hash=get_password_hash("Pass1234"),
            full_name="Kucharz Tomek",
            role_system=RoleSystem.EMPLOYEE,
            hourly_rate=None,  # uses role rate: 38 PLN/h
        )
        session.add_all([u_waiter, u_cook])
        session.commit()
        session.refresh(u_waiter)
        session.refresh(u_cook)

        # Add 1 historical shift with +30 min drift (0.5h) so drift cost > planned cost
        hist_date = date(2026, 11, 2)
        hist_sched = Schedule(
            date=hist_date,
            shift_def_id=shift_8h.id,
            user_id=u_waiter.id,
            role_id=role_waiter.id,
            is_published=True,
        )
        session.add(hist_sched)
        session.commit()
        session.refresh(hist_sched)
        session.add(
            Attendance(
                user_id=u_waiter.id,
                date=hist_date,
                check_in=time(10, 0),
                check_out=time(18, 30),  # +30m drift
                was_scheduled=True,
                status=AttendanceStatus.CONFIRMED,
                schedule_id=hist_sched.id,
            )
        )
        session.commit()

        week_start = date(2026, 11, 9)  # Monday
        week_end = date(2026, 11, 15)   # Sunday
        friday = date(2026, 11, 13)

        # Draft schedule:
        # Monday: 1 Waiter (8h * 30 = 240 PLN)
        # Friday: 1 Waiter (8h * 30 = 240 PLN) + 1 Cook (8h * 38 = 304 PLN) = 544 PLN (Most expensive day)
        draft_entries = [
            {
                "date": week_start.isoformat(),
                "shift_def_id": shift_8h.id,
                "user_id": str(u_waiter.id),
                "role_id": role_waiter.id,
            },
            {
                "date": friday.isoformat(),
                "shift_def_id": shift_8h.id,
                "user_id": str(u_waiter.id),
                "role_id": role_waiter.id,
            },
            {
                "date": friday.isoformat(),
                "shift_def_id": shift_8h.id,
                "user_id": str(u_cook.id),
                "role_id": role_kitchen.id,
            },
        ]

        svc = WFMPredictionService(session, tenant_id=test_tenant.id)
        sim = svc.simulate_labor_cost(
            start_date=week_start,
            end_date=week_end,
            draft_entries=draft_entries,
            reference_date=week_start,
        )

        # Total planned hours: 3 shifts * 8h = 24.0h
        assert sim["total_planned_hours"] == pytest.approx(24.0)
        # Planned cost: 2 * 240 + 304 = 784.0 PLN
        assert sim["estimated_planned_cost"] == pytest.approx(784.0)
        # With +0.5h drift per shift: 3 shifts * 8.5h -> 2 * (8.5*30) + 1 * (8.5*38) = 510 + 323 = 833.0 PLN
        assert sim["projected_cost_with_drift"] == pytest.approx(833.0)
        assert sim["drift_cost_delta"] == pytest.approx(49.0)
        assert sim["avg_hourly_cost"] == pytest.approx(784.0 / 24.0, abs=0.01)

        # Role breakdown
        by_role = {r["role_name"]: r for r in sim["hours_by_role"]}
        assert by_role["Kelner"]["planned_hours"] == pytest.approx(16.0)
        assert by_role["Kelner"]["planned_cost"] == pytest.approx(480.0)
        assert by_role["Kuchnia"]["planned_hours"] == pytest.approx(8.0)
        assert by_role["Kuchnia"]["planned_cost"] == pytest.approx(304.0)

        # Most expensive day is Friday (544 PLN)
        expensive_days = [d for d in sim["daily_costs"] if d["is_most_expensive"]]
        assert len(expensive_days) == 1
        assert expensive_days[0]["date"] == friday.isoformat()
        assert expensive_days[0]["planned_cost"] == pytest.approx(544.0)


class TestWFMWorkersAndEndpoints:
    """Tests for Solver/Analytics Workers and Scheduler WFM endpoints."""

    @pytest.mark.asyncio
    async def test_scheduler_wfm_endpoints_and_solver_explanation(
        self, client: AsyncClient, session: Session, auth_headers: dict, test_tenant
    ):
        role = JobRole(tenant_id=test_tenant.id, name="Kelner", color_hex="#123456", hourly_rate=30.0)
        shift = ShiftDefinition(
            tenant_id=test_tenant.id, name="Ranna", start_time=time(8, 0), end_time=time(16, 0)
        )
        session.add_all([role, shift])
        session.commit()
        session.refresh(role)
        session.refresh(shift)

        emp = User(
            tenant_id=test_tenant.id,
            username="wfm_api_emp",
            password_hash=get_password_hash("Pass1234"),
            full_name="Pracownik WFM",
            role_system=RoleSystem.EMPLOYEE,
            hourly_rate=32.0,
            target_hours_per_month=160,
        )
        session.add(emp)
        session.commit()
        session.refresh(emp)
        session.add(UserJobRoleLink(user_id=emp.id, role_id=role.id))

        week_start = date(2026, 11, 9)
        week_end = date(2026, 11, 15)

        session.add(
            StaffingRequirement(
                date=week_start,
                shift_def_id=shift.id,
                role_id=role.id,
                min_count=1,
            )
        )
        session.add(
            Availability(
                user_id=emp.id,
                date=week_start,
                shift_def_id=shift.id,
                status=AvailabilityStatus.AVAILABLE,
            )
        )
        session.commit()

        # 1. Generate schedule via worker fallback -> check solver_explanation & audit log
        gen_res = await client.post(
            "/scheduler/generate",
            headers=auth_headers,
            json={"start_date": week_start.isoformat(), "end_date": week_start.isoformat()},
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["status"] == "success"
        assert "solver_explanation" in gen_data
        assert gen_data["solver_explanation"]["executed_via"] == "sync_fallback"
        assert gen_data["solver_explanation"]["total_assigned_slots"] == 1

        audit_logs = session.exec(
            select(ShiftAuditLog).where(ShiftAuditLog.action == "SOLVER_CP_SAT_RUN")
        ).all()
        assert len(audit_logs) >= 1

        # 2. GET /scheduler/wfm-predictions
        pred_res = await client.get(
            "/scheduler/wfm-predictions",
            headers=auth_headers,
            params={"start_date": week_start.isoformat(), "end_date": week_end.isoformat()},
        )
        assert pred_res.status_code == 200
        pred_data = pred_res.json()
        assert "bottleneck_forecast" in pred_data
        assert "attendance_drift" in pred_data
        assert "shift_stability" in pred_data
        assert "labor_cost_simulation" in pred_data

        # 3. POST /scheduler/simulate-labor-cost
        sim_res = await client.post(
            "/scheduler/simulate-labor-cost",
            headers=auth_headers,
            json={
                "start_date": week_start.isoformat(),
                "end_date": week_end.isoformat(),
                "items": [
                    {
                        "date": week_start.isoformat(),
                        "shift_def_id": shift.id,
                        "user_id": str(emp.id),
                        "role_id": role.id,
                    }
                ],
            },
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["total_planned_hours"] == pytest.approx(8.0)
        assert sim_data["estimated_planned_cost"] == pytest.approx(256.0)
