import pytest
from datetime import date, timedelta, time
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models import (
    User, JobRole, ShiftDefinition, Schedule, Shift,
    ShiftGiveaway, GiveawayStatus, ShiftRoleLink, UserJobRoleLink,
    Attendance, AttendanceStatus, ShiftAuditLog, RoleSystem
)

@pytest.mark.asyncio
class TestDraftScheduleAndPublish:
    """Feature 1: Draft schedule mode and publish flow"""

    async def test_draft_schedule_invisible_to_employee(
        self, client: AsyncClient, session: Session, auth_headers: dict, employee_headers: dict,
        shift_definition: ShiftDefinition, job_role: JobRole
    ):
        # 1. Fetch employee user
        emp_user = session.exec(select(User).where(User.role_system == RoleSystem.EMPLOYEE)).first()
        today = date.today() + timedelta(days=2)

        # 2. Manager creates draft shift (is_published=False)
        draft_shift = Schedule(
            date=today,
            shift_def_id=shift_definition.id,
            user_id=emp_user.id,
            role_id=job_role.id,
            is_published=False
        )
        session.add(draft_shift)
        session.commit()

        # 3. Employee checks my-schedule: must NOT see draft shift
        res = await client.get(
            f"/employee/my-schedule?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        assert res.status_code == 200
        emp_shifts = res.json()
        assert len(emp_shifts) == 0

        # Employee checks team schedule: must NOT see draft shift
        res_team = await client.get(
            f"/employee/schedules/all?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        assert res_team.status_code == 200
        assert len(res_team.json()) == 0

        # 4. Manager publishes schedule via /manager/schedules/publish
        pub_res = await client.post(
            "/manager/schedules/publish",
            headers=auth_headers,
            json={"start_date": str(today), "end_date": str(today)}
        )
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "published"
        assert pub_res.json()["count"] >= 1

        # 5. Employee checks my-schedule again: now shift is visible
        res_after = await client.get(
            f"/employee/my-schedule?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        assert res_after.status_code == 200
        emp_shifts_after = res_after.json()
        assert len(emp_shifts_after) == 1
        assert emp_shifts_after[0]["id"] == str(draft_shift.id)

    async def test_save_batch_saves_as_draft(
        self, client: AsyncClient, session: Session, auth_headers: dict, employee_headers: dict,
        shift_definition: ShiftDefinition, job_role: JobRole
    ):
        emp_user = session.exec(select(User).where(User.role_system == RoleSystem.EMPLOYEE)).first()
        target_date = date.today() + timedelta(days=5)

        # Manager calls save_batch without is_published (defaults to False)
        save_res = await client.post(
            "/scheduler/save_batch",
            headers=auth_headers,
            json={
                "start_date": str(target_date),
                "end_date": str(target_date),
                "items": [{
                    "date": str(target_date),
                    "shift_def_id": shift_definition.id,
                    "user_id": str(emp_user.id),
                    "role_id": job_role.id
                }]
            }
        )
        assert save_res.status_code == 200
        assert save_res.json()["count"] == 1

        # Check DB directly: is_published must be False
        saved_sched = session.exec(select(Schedule).where(Schedule.date == target_date)).first()
        assert saved_sched is not None
        assert saved_sched.is_published is False

        # Employee cannot see it
        emp_res = await client.get(
            f"/employee/my-schedule?start_date={target_date}&end_date={target_date}",
            headers=employee_headers
        )
        assert len(emp_res.json()) == 0


@pytest.mark.asyncio
class TestSolverClopeningAvoidance:
    """Feature 2: Labor law compliance - 11h daily rest soft penalty"""

    async def test_solver_penalizes_clopening(self, session: Session, test_tenant):
        from app.services.solver import SolverService
        from app.models import Availability, AvailabilityStatus, StaffingRequirement

        tenant_id = test_tenant.id

        # Role
        role = JobRole(name="Kelner Clopening", color_hex="#3498db", tenant_id=tenant_id)
        session.add(role)
        session.commit()
        session.refresh(role)

        # Shift 1 (Evening: 14:00 - 23:00)
        s_eve = ShiftDefinition(name="Wieczor", start_time=time(14, 0), end_time=time(23, 0), tenant_id=tenant_id)
        # Shift 2 (Morning: 06:00 - 14:00 -> only 7h rest from 23:00 to 06:00!)
        s_morn = ShiftDefinition(name="Rano", start_time=time(6, 0), end_time=time(14, 0), tenant_id=tenant_id)
        session.add_all([s_eve, s_morn])
        session.commit()
        session.refresh(s_eve)
        session.refresh(s_morn)

        # Worker A (available for both shifts)
        worker_a = User(
            username=f"worker_a_{uuid4().hex[:6]}",
            email=f"worker_a_{uuid4().hex[:6]}@test.com",
            password_hash="fakehash",
            full_name="Worker A",
            role_system=RoleSystem.EMPLOYEE,
            tenant_id=tenant_id,
            is_active=True
        )
        # Worker B (available only for Morning shift on Day 2)
        worker_b = User(
            username=f"worker_b_{uuid4().hex[:6]}",
            email=f"worker_b_{uuid4().hex[:6]}@test.com",
            password_hash="fakehash",
            full_name="Worker B",
            role_system=RoleSystem.EMPLOYEE,
            tenant_id=tenant_id,
            is_active=True
        )
        session.add_all([worker_a, worker_b])
        session.commit()
        session.refresh(worker_a)
        session.refresh(worker_b)

        # Link roles
        session.add(UserJobRoleLink(user_id=worker_a.id, role_id=role.id))
        session.add(UserJobRoleLink(user_id=worker_b.id, role_id=role.id))
        session.commit()

        d1 = date(2026, 11, 2)
        d2 = date(2026, 11, 3)

        # Availabilities: Worker A available on d1 (evening) and d2 (morning)
        # Worker B available on d2 (morning)
        session.add(Availability(user_id=worker_a.id, date=d1, shift_def_id=s_eve.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=worker_a.id, date=d2, shift_def_id=s_morn.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=worker_b.id, date=d2, shift_def_id=s_morn.id, status=AvailabilityStatus.AVAILABLE))

        # Staffing requirements: 1 person for evening on d1, 1 person for morning on d2
        session.add(StaffingRequirement(shift_def_id=s_eve.id, role_id=role.id, min_count=1, date=d1))
        session.add(StaffingRequirement(shift_def_id=s_morn.id, role_id=role.id, min_count=1, date=d2))
        session.commit()

        # Run solver
        solver = SolverService(session, tenant_id=tenant_id)
        res = solver.solve(d1, d2, save=False)

        assert res["status"] == "success"
        schedules = res["schedules"]
        assert len(schedules) == 2

        assignments = {(s["date"], s["shift_def_id"]): s["user_id"] for s in schedules}
        # Evening d1 should be assigned to worker A (only one available)
        assert assignments.get((d1, s_eve.id)) == worker_a.id
        # Morning d2 should be assigned to Worker B to avoid clopening (< 11h rest for worker A)
        assert assignments.get((d2, s_morn.id)) == worker_b.id


@pytest.mark.asyncio
class TestShiftSwapAndAuditLog:
    """Feature 3 & 4: Shift swap validation, single-transaction swap, and audit log"""

    async def test_shift_swap_role_validation_and_execution(
        self, client: AsyncClient, session: Session, auth_headers: dict,
        test_tenant
    ):
        tenant_id = test_tenant.id

        # 1. Setup Roles
        role_waiter = JobRole(name="Waiter", color_hex="#2ecc71", tenant_id=tenant_id)
        role_cook = JobRole(name="Cook", color_hex="#e74c3c", tenant_id=tenant_id)
        session.add_all([role_waiter, role_cook])
        session.commit()
        session.refresh(role_waiter)
        session.refresh(role_cook)

        # 2. Setup Shift Definitions
        shift_waiter_def = ShiftDefinition(name="Waiter Shift", start_time=time(10, 0), end_time=time(18, 0), tenant_id=tenant_id)
        shift_cook_def = ShiftDefinition(name="Cook Shift", start_time=time(12, 0), end_time=time(20, 0), tenant_id=tenant_id)
        session.add_all([shift_waiter_def, shift_cook_def])
        session.commit()
        session.refresh(shift_waiter_def)
        session.refresh(shift_cook_def)

        # ShiftRoleLink
        session.add(ShiftRoleLink(shift_def_id=shift_waiter_def.id, role_id=role_waiter.id))
        session.add(ShiftRoleLink(shift_def_id=shift_cook_def.id, role_id=role_cook.id))
        session.commit()

        # 3. Setup Users
        user_a = User(
            username=f"usera_{uuid4().hex[:6]}",
            email=f"usera_{uuid4().hex[:6]}@test.com",
            password_hash="fakehash",
            full_name="User A",
            role_system=RoleSystem.EMPLOYEE,
            tenant_id=tenant_id,
            is_active=True
        )
        user_b = User(
            username=f"userb_{uuid4().hex[:6]}",
            email=f"userb_{uuid4().hex[:6]}@test.com",
            password_hash="fakehash",
            full_name="User B",
            role_system=RoleSystem.EMPLOYEE,
            tenant_id=tenant_id,
            is_active=True
        )
        session.add_all([user_a, user_b])
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)

        # User A initially only Waiter; User B initially only Cook
        session.add(UserJobRoleLink(user_id=user_a.id, role_id=role_waiter.id))
        session.add(UserJobRoleLink(user_id=user_b.id, role_id=role_cook.id))
        session.commit()

        d_a = date.today() + timedelta(days=3)
        d_b = date.today() + timedelta(days=4)

        sched_a = Schedule(date=d_a, shift_def_id=shift_waiter_def.id, user_id=user_a.id, role_id=role_waiter.id, is_published=True)
        sched_b = Schedule(date=d_b, shift_def_id=shift_cook_def.id, user_id=user_b.id, role_id=role_cook.id, is_published=True)
        session.add_all([sched_a, sched_b])
        session.commit()
        session.refresh(sched_a)
        session.refresh(sched_b)

        # 4. Test Role Incompatibility: User A tries to swap with Sched B (Cook), but User A is not a Cook!
        from app.auth_utils import create_access_token
        token_a = create_access_token(data={"sub": user_a.username, "tenant_id": tenant_id})
        headers_a = {"Authorization": f"Bearer {token_a}"}

        swap_fail = await client.post(
            f"/employee/giveaway/{sched_a.id}",
            headers=headers_a,
            json={"target_shift_id": str(sched_b.id)}
        )
        assert swap_fail.status_code == 400
        assert "matching roles" in swap_fail.json()["detail"]

        # 5. Give both users both roles so they are qualified to swap
        session.add(UserJobRoleLink(user_id=user_a.id, role_id=role_cook.id))
        session.add(UserJobRoleLink(user_id=user_b.id, role_id=role_waiter.id))
        session.commit()

        # Now offer swap should succeed
        swap_ok = await client.post(
            f"/employee/giveaway/{sched_a.id}",
            headers=headers_a,
            json={"target_shift_id": str(sched_b.id)}
        )
        assert swap_ok.status_code == 200
        giveaway_id = swap_ok.json()["id"]

        giveaway = session.get(ShiftGiveaway, UUID(giveaway_id))
        assert giveaway.target_shift_id == str(sched_b.id)
        assert giveaway.status == GiveawayStatus.OPEN

        # 6. Manager approves the swap via /manager/giveaways/{giveaway_id}/swap (or /reassign)
        mgr_swap_res = await client.post(
            f"/manager/giveaways/{giveaway_id}/swap",
            headers=auth_headers,
            json={"target_shift_id": str(sched_b.id)}
        )
        assert mgr_swap_res.status_code == 200
        assert mgr_swap_res.json()["status"] == "swapped"

        # Verify atomic swap in DB:
        session.expire_all()
        sched_a_updated = session.get(Schedule, sched_a.id)
        sched_b_updated = session.get(Schedule, sched_b.id)
        giveaway_updated = session.get(ShiftGiveaway, giveaway.id)

        assert sched_a_updated.user_id == user_b.id
        assert sched_b_updated.user_id == user_a.id
        assert giveaway_updated.status == GiveawayStatus.TAKEN
        assert giveaway_updated.taken_by == user_b.id

        # 7. Check ShiftAuditLog for both shifts
        audit_res_a = await client.get(
            f"/manager/shifts/{sched_a.id}/audit-log",
            headers=auth_headers
        )
        assert audit_res_a.status_code == 200
        logs_a = audit_res_a.json()
        assert len(logs_a) >= 1
        assert logs_a[0]["action"] == "SWAP_ASSIGNMENT"
        assert logs_a[0]["old_value"] == str(user_a.id)
        assert logs_a[0]["new_value"] == str(user_b.id)

        audit_res_b = await client.get(
            f"/manager/shifts/{sched_b.id}/audit-log",
            headers=auth_headers
        )
        assert audit_res_b.status_code == 200
        logs_b = audit_res_b.json()
        assert len(logs_b) >= 1
        assert logs_b[0]["action"] == "SWAP_ASSIGNMENT"
        assert logs_b[0]["old_value"] == str(user_b.id)
        assert logs_b[0]["new_value"] == str(user_a.id)

    async def test_audit_log_on_attendance_confirm_and_reject(
        self, client: AsyncClient, session: Session, auth_headers: dict,
        test_tenant
    ):
        tenant_id = test_tenant.id
        user = session.exec(select(User).where(User.tenant_id == tenant_id)).first()

        att = Attendance(
            user_id=user.id,
            date=date.today(),
            check_in=time(9, 0),
            check_out=time(17, 0),
            was_scheduled=False,
            status=AttendanceStatus.PENDING
        )
        session.add(att)
        session.commit()
        session.refresh(att)

        # Confirm attendance
        conf_res = await client.put(f"/manager/attendance/{att.id}/confirm", headers=auth_headers)
        assert conf_res.status_code == 200

        # Check audit log
        audit_res = await client.get(f"/manager/shifts/{att.id}/audit-log", headers=auth_headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "CONFIRM_ATTENDANCE"
        assert logs[0]["old_value"] == "PENDING"
        assert logs[0]["new_value"] == "CONFIRMED"

    async def test_audit_log_on_shift_update_and_assignment(
        self, client: AsyncClient, session: Session, auth_headers: dict,
        shift_definition: ShiftDefinition, job_role: JobRole
    ):
        user = session.exec(select(User).where(User.role_system == RoleSystem.EMPLOYEE)).first()
        if not user:
            user = User(
                username=f"emp_{uuid4().hex[:6]}",
                email=f"emp_{uuid4().hex[:6]}@test.com",
                password_hash="fakehash",
                full_name="Employee User",
                role_system=RoleSystem.EMPLOYEE,
                tenant_id=job_role.tenant_id,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        # 1. Update shift definition hours
        update_res = await client.put(
            f"/manager/shifts/{shift_definition.id}",
            headers=auth_headers,
            json={
                "name": "Updated Shift Name",
                "start_time": "11:00",
                "end_time": "19:00",
                "applicable_days": [0, 1, 2],
                "allowed_role_ids": [job_role.id]
            }
        )
        assert update_res.status_code == 200

        # Check audit log for shift_definition
        audit_res = await client.get(
            f"/manager/shifts/{shift_definition.id}/audit-log",
            headers=auth_headers
        )
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) >= 1
        assert logs[0]["action"] == "UPDATE_SHIFT_HOURS"
        assert "11:00" in logs[0]["new_value"]

        # 2. Manual assign
        today = date.today() + timedelta(days=10)
        assign_res = await client.post(
            "/scheduler/assignment",
            headers=auth_headers,
            json={
                "date": str(today),
                "shift_def_id": shift_definition.id,
                "user_id": str(user.id),
                "role_id": job_role.id
            }
        )
        assert assign_res.status_code == 200
        sched_id = assign_res.json()["id"]

        audit_sched = await client.get(
            f"/manager/shifts/{sched_id}/audit-log",
            headers=auth_headers
        )
        assert audit_sched.status_code == 200
        sched_logs = audit_sched.json()
        assert len(sched_logs) >= 1
        assert sched_logs[0]["action"] == "ASSIGNMENT_CHANGE"

    async def test_audit_log_tenant_isolation(
        self, client: AsyncClient, session: Session, auth_headers: dict, test_tenant
    ):
        from app.models import RestaurantConfig
        from app.auth_utils import create_access_token

        # Create another restaurant and manager
        tenant2 = RestaurantConfig(name="Other Restaurant", slug="other-rest")
        session.add(tenant2)
        session.commit()
        session.refresh(tenant2)

        mgr2 = User(
            username=f"mgr2_{uuid4().hex[:6]}",
            email=f"mgr2_{uuid4().hex[:6]}@test.com",
            password_hash="fakehash",
            full_name="Manager 2",
            role_system=RoleSystem.MANAGER,
            tenant_id=tenant2.id,
            is_active=True
        )
        session.add(mgr2)

        # Audit log for tenant 1
        log1 = ShiftAuditLog(
            restaurant_id=test_tenant.id,
            shift_id="secret_shift_123",
            action="TOP_SECRET_ACTION",
            old_value="val1",
            new_value="val2"
        )
        session.add(log1)
        session.commit()

        token2 = create_access_token(data={"sub": mgr2.username, "tenant_id": tenant2.id})
        headers_mgr2 = {"Authorization": f"Bearer {token2}"}

        # Manager 2 tries to fetch audit log for secret_shift_123
        res = await client.get(
            "/manager/shifts/secret_shift_123/audit-log",
            headers=headers_mgr2
        )
        assert res.status_code == 200
        # Must be empty because it belongs to test_tenant, not tenant2
        assert len(res.json()) == 0
