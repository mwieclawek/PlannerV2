"""
Unit tests for SolverService (CP-SAT constraint programming solver)
Tests optimization logic, constraints, and edge cases.
"""
import pytest
from datetime import date, timedelta, datetime
from sqlmodel import Session

from app.models import (
    User, JobRole, ShiftDefinition, Availability, 
    StaffingRequirement, Schedule, RoleSystem, AvailabilityStatus,
    UserJobRoleLink
)
from app.contracts.wfm import (
    SolverAvailabilityItem,
    SolverEmployeeItem,
    SolverInputDTO,
    SolverRequirementItem,
    SolverResultDTO,
    SolverRoleItem,
    SolverShiftItem,
)
from app.services.scheduler_service import SchedulerService
from app.services.solver import SolverService
from app.auth_utils import get_password_hash


class TestSolverBasic:
    """Basic solver functionality tests"""
    
    def test_solve_empty_data(self, session: Session):
        """Test solver with no employees, shifts, or roles"""
        service = SchedulerService(session)
        today = date.today()
        
        result = service.solve_schedule(today, today, save=False)
        
        assert result["status"] in ["success", "infeasible"]
        assert result["count"] == 0
    
    def test_solve_no_requirements(self, session: Session, job_role, shift_definition):
        """Test solver with no staffing requirements"""
        # Create employee with role
        user = User(
            username="solver_test",
            password_hash=get_password_hash("test"),
            full_name="Solver Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        # Link role
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()
        
        service = SchedulerService(session)
        today = date.today()
        
        result = service.solve_schedule(today, today, save=False)
        
        # Without requirements, solver should produce 0 assignments
        assert result["status"] == "success"
        assert result["count"] == 0
    
    def test_solve_with_requirement(self, session: Session, job_role, shift_definition):
        """Test solver with a requirement"""
        # Create employee with role
        user = User(
            username="solver_req_test",
            password_hash=get_password_hash("test"),
            full_name="Solver Req Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        # Link role
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()
        
        today = date.today()
        
        # Create requirement
        req = StaffingRequirement(
            date=today,
            shift_def_id=shift_definition.id,
            role_id=job_role.id,
            min_count=1
        )
        session.add(req)
        session.commit()

        # Add availability
        session.add(Availability(
            user_id=user.id,
            date=today,
            shift_def_id=shift_definition.id,
            status=AvailabilityStatus.AVAILABLE
        ))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        assert result["status"] == "success"
        assert result["count"] == 1


class TestSolverConstraints:
    """Tests for solver constraints"""
    
    def test_solve_unavailable_employee_not_assigned(
        self, session: Session, job_role, shift_definition
    ):
        """Test that unavailable employee is not assigned"""
        user = User(
            username="unavail_test",
            password_hash=get_password_hash("test"),
            full_name="Unavailable Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()
        
        today = date.today()
        
        # Mark as unavailable
        avail = Availability(
            user_id=user.id,
            date=today,
            shift_def_id=shift_definition.id,
            status=AvailabilityStatus.UNAVAILABLE
        )
        session.add(avail)
        
        # Create requirement
        req = StaffingRequirement(
            date=today,
            shift_def_id=shift_definition.id,
            role_id=job_role.id,
            min_count=1
        )
        session.add(req)
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # Should not assign unavailable employee
        assert result["count"] == 0
        # Should have warning about understaffing
        assert len(result.get("warnings", [])) > 0

    def test_solve_strict_unavailability_handling(
        self, session: Session, job_role, shift_definition
    ):
        """Test that an unavailable employee is never chosen, even if it leads to severe understaffing"""
        user_unavail = User(
            username="strict_unavail",
            password_hash=get_password_hash("test"),
            full_name="Strict Unavailable",
            role_system=RoleSystem.EMPLOYEE
        )
        user_avail = User(
            username="strict_avail",
            password_hash=get_password_hash("test"),
            full_name="Strict Available",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user_unavail)
        session.add(user_avail)
        session.commit()

        session.add(UserJobRoleLink(user_id=user_unavail.id, role_id=job_role.id))
        session.add(UserJobRoleLink(user_id=user_avail.id, role_id=job_role.id))
        session.commit()

        today = date.today()

        # Mark user_unavail as explicitly UNAVAILABLE, and user_avail as AVAILABLE
        session.add(Availability(
            user_id=user_unavail.id, date=today,
            shift_def_id=shift_definition.id, status=AvailabilityStatus.UNAVAILABLE
        ))
        session.add(Availability(
            user_id=user_avail.id, date=today,
            shift_def_id=shift_definition.id, status=AvailabilityStatus.AVAILABLE
        ))

        # We need 5 employees! (We only have 1 available, 1 unavailable)
        req = StaffingRequirement(
            date=today, shift_def_id=shift_definition.id,
            role_id=job_role.id, min_count=5
        )
        session.add(req)
        session.commit()

        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)

        # The solver MUST only assign the available user, ignoring the unavailable one 
        # despite the high staffing requirement.
        assert result["count"] == 1
        assigned_user_ids = [str(s["user_id"]) for s in result.get("schedules", [])]
        assert str(user_unavail.id) not in assigned_user_ids
        assert str(user_avail.id) in assigned_user_ids
        assert len(result.get("warnings", [])) > 0
    
    def test_solve_allows_split_shifts(self, session: Session, job_role):
        """Test that employee CAN get 2 shifts per day if they don't overlap too much"""
        from datetime import time
        # Create two non-overlapping shifts
        shift1 = ShiftDefinition(name="Morning Test", start_time=time(6, 0), end_time=time(14, 0))
        shift2 = ShiftDefinition(name="Evening Test", start_time=time(15, 0), end_time=time(22, 0))
        session.add(shift1)
        session.add(shift2)
        session.commit()
        
        user = User(
            username="splitshift_test",
            password_hash=get_password_hash("test"),
            full_name="Split Shift Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()
        
        today = date.today()
        
        # Require 1 person for each shift
        req1 = StaffingRequirement(date=today, shift_def_id=shift1.id, role_id=job_role.id, min_count=1)
        req2 = StaffingRequirement(date=today, shift_def_id=shift2.id, role_id=job_role.id, min_count=1)
        session.add(req1)
        session.add(req2)
        session.commit()

        # Add availability for both shifts
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift1.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift2.id, status=AvailabilityStatus.AVAILABLE))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # With split shifts allowed, employee should get both
        user_assignments = [s for s in result.get("schedules", []) if str(s["user_id"]) == str(user.id)]
        assert len(user_assignments) == 2

    def test_solve_overlap_30min_allowed(self, session: Session, job_role):
        """Test that 30 min overlap is allowed"""
        from datetime import time
        # shift1 ends at 15:00, shift2 starts at 14:45 -> 15 min overlap
        shift1 = ShiftDefinition(name="Shift A", start_time=time(7, 0), end_time=time(15, 0))
        shift2 = ShiftDefinition(name="Shift B", start_time=time(14, 45), end_time=time(22, 0))
        session.add(shift1)
        session.add(shift2)
        
        user = User(username="overlap_ok", password_hash=get_password_hash("t"), full_name="X", role_system=RoleSystem.EMPLOYEE)
        session.add(user)
        session.add(UserJobRoleLink(user_id=user.id, role_id=job_role.id))
        session.commit()
        
        today = date.today()
        session.add(StaffingRequirement(date=today, shift_def_id=shift1.id, role_id=job_role.id, min_count=1))
        session.add(StaffingRequirement(date=today, shift_def_id=shift2.id, role_id=job_role.id, min_count=1))
        session.commit()

        # Add availability
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift1.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift2.id, status=AvailabilityStatus.AVAILABLE))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # Should be allowed (15m overlap <= 30m)
        assert len([s for s in result.get("schedules", []) if str(s["user_id"]) == str(user.id)]) == 2

    def test_solve_overlap_huge_forbidden(self, session: Session, job_role):
        """Test that > 30 min overlap is NOT allowed"""
        from datetime import time
        # shift1 ends at 15:00, shift2 starts at 14:00 -> 60 min overlap
        shift1 = ShiftDefinition(name="Shift A", start_time=time(7, 0), end_time=time(15, 0))
        shift2 = ShiftDefinition(name="Shift B", start_time=time(14, 0), end_time=time(22, 0))
        session.add(shift1)
        session.add(shift2)
        
        user = User(username="overlap_bad", password_hash=get_password_hash("t"), full_name="X", role_system=RoleSystem.EMPLOYEE)
        session.add(user)
        session.add(UserJobRoleLink(user_id=user.id, role_id=job_role.id))
        session.commit()
        
        today = date.today()
        session.add(StaffingRequirement(date=today, shift_def_id=shift1.id, role_id=job_role.id, min_count=1))
        session.add(StaffingRequirement(date=today, shift_def_id=shift2.id, role_id=job_role.id, min_count=1))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # Should NOT be allowed (60m overlap > 30m)
        assert len([s for s in result.get("schedules", []) if str(s["user_id"]) == str(user.id)]) <= 1

    def test_solve_overlap_31min_forbidden(self, session: Session, job_role):
        """Test that exactly > 30 min (e.g. 31 min) overlap is NOT allowed"""
        from datetime import time
        # shift1 ends at 15:00, shift2 starts at 14:29 -> 31 min overlap
        shift1 = ShiftDefinition(name="Shift A", start_time=time(7, 0), end_time=time(15, 0))
        shift2 = ShiftDefinition(name="Shift B", start_time=time(14, 29), end_time=time(22, 0))
        session.add(shift1)
        session.add(shift2)
        
        user = User(username="overlap_31m", password_hash=get_password_hash("t"), full_name="X", role_system=RoleSystem.EMPLOYEE)
        session.add(user)
        session.add(UserJobRoleLink(user_id=user.id, role_id=job_role.id))
        session.commit()
        
        today = date.today()
        session.add(StaffingRequirement(date=today, shift_def_id=shift1.id, role_id=job_role.id, min_count=1))
        session.add(StaffingRequirement(date=today, shift_def_id=shift2.id, role_id=job_role.id, min_count=1))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # Should NOT be allowed (31m overlap > 30m)
        assert len([s for s in result.get("schedules", []) if str(s["user_id"]) == str(user.id)]) <= 1

    def test_solve_respects_target_hours(self, session: Session, job_role):
        """Test that solver respects target_hours_per_month"""
        from datetime import time
        # shift is 8 hours
        shift1 = ShiftDefinition(name="8H Shift", start_time=time(8, 0), end_time=time(16, 0))
        session.add(shift1)
        
        # User has limit of 10 hours for the month
        user = User(
            username="target_h", 
            password_hash=get_password_hash("t"), 
            full_name="H", 
            role_system=RoleSystem.EMPLOYEE,
            target_hours_per_month=10
        )
        session.add(user)
        session.add(UserJobRoleLink(user_id=user.id, role_id=job_role.id))
        session.commit()
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Require 1 person for both days (8+8 = 16 hours)
        session.add(StaffingRequirement(date=today, shift_def_id=shift1.id, role_id=job_role.id, min_count=1))
        session.add(StaffingRequirement(date=tomorrow, shift_def_id=shift1.id, role_id=job_role.id, min_count=1))
        session.commit()

        # Add availability
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift1.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=user.id, date=tomorrow, shift_def_id=shift1.id, status=AvailabilityStatus.AVAILABLE))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, tomorrow, save=False)
        
        # Should only assign 1 day (8 hours), as 2 days (16 hours) exceeds 10.
        assert result["count"] == 1 

    
    def test_solve_role_matching(self, session: Session, shift_definition):
        """Test that employees are only assigned to roles they have"""
        role1 = JobRole(name="Barista Test", color_hex="#8B4513")
        role2 = JobRole(name="Cashier Test", color_hex="#228B22")
        session.add(role1)
        session.add(role2)
        session.commit()
        
        # Create employee with only role1
        user = User(
            username="role_match",
            password_hash=get_password_hash("test"),
            full_name="Role Match Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        link = UserJobRoleLink(user_id=user.id, role_id=role1.id)
        session.add(link)
        session.commit()
        
        today = date.today()
        
        # Require role2 (which user doesn't have)
        req = StaffingRequirement(date=today, shift_def_id=shift_definition.id, role_id=role2.id, min_count=1)
        session.add(req)
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # User should not be assigned since they don't have role2
        user_for_role2 = [s for s in result.get("schedules", []) if s.role_id == role2.id]
        assert len(user_for_role2) == 0


class TestSolverPreferences:
    """Tests for preference optimization"""
    
    def test_solve_prefers_available_employee(self, session: Session, job_role, shift_definition):
        """Test that available availability is properly considered"""
        # Create two employees
        user1 = User(
            username="pref_user1",
            password_hash=get_password_hash("test"),
            full_name="User 1",
            role_system=RoleSystem.EMPLOYEE
        )
        user2 = User(
            username="pref_user2",
            password_hash=get_password_hash("test"),
            full_name="User 2",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user1)
        session.add(user2)
        session.commit()
        
        link1 = UserJobRoleLink(user_id=user1.id, role_id=job_role.id)
        link2 = UserJobRoleLink(user_id=user2.id, role_id=job_role.id)
        session.add(link1)
        session.add(link2)
        session.commit()
        
        today = date.today()
        
        # User1 available, User2 unavailable
        avail1 = Availability(
            user_id=user1.id, date=today, 
            shift_def_id=shift_definition.id, status=AvailabilityStatus.AVAILABLE
        )
        avail2 = Availability(
            user_id=user2.id, date=today,
            shift_def_id=shift_definition.id, status=AvailabilityStatus.UNAVAILABLE
        )
        session.add(avail1)
        session.add(avail2)
        
        # Require only 1 person
        req = StaffingRequirement(date=today, shift_def_id=shift_definition.id, role_id=job_role.id, min_count=1)
        session.add(req)
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        if result["count"] == 1:
            assigned = result["schedules"][0]
            # Should prefer user1 (AVAILABLE > UNAVAILABLE)
            # assigned is a dict when save=False
            assert str(assigned["user_id"]) == str(user1.id)


class TestSolverWarnings:
    """Tests for understaffing warnings"""
    
    def test_solve_warnings_understaffed(self, session: Session, job_role, shift_definition):
        """Test that warnings are generated for understaffing"""
        today = date.today()
        
        # Require 5 people but have no employees
        req = StaffingRequirement(
            date=today,
            shift_def_id=shift_definition.id,
            role_id=job_role.id,
            min_count=5
        )
        session.add(req)
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        assert "warnings" in result
        assert len(result["warnings"]) > 0
        
        warning = result["warnings"][0]
        assert warning["required"] == 5
        assert warning["assigned"] == 0
        assert warning["missing"] == 5


class TestSolverSave:
    """Tests for save functionality"""
    
    def test_solve_save_false_does_not_persist(self, session: Session, job_role, shift_definition):
        """Test that save=False doesn't persist to database"""
        user = User(
            username="nosave_test",
            password_hash=get_password_hash("test"),
            full_name="No Save Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        
        today = date.today()
        req = StaffingRequirement(date=today, shift_def_id=shift_definition.id, role_id=job_role.id, min_count=1)
        session.add(req)
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, today, save=False)
        
        # Check database is empty
        from sqlmodel import select
        schedules = session.exec(select(Schedule).where(Schedule.date == today)).all()
        
        # With save=False, should not persist
        # (Note: result may have schedules, but DB should be empty)
        assert len([s for s in schedules if str(s.user_id) == str(user.id)]) == 0


class TestSolverEdgeCases:
    """Edge cases for solver"""
    
    def test_solve_multiple_days(self, session: Session, job_role, shift_definition):
        """Test solving for multiple days"""
        user = User(
            username="multiday",
            password_hash=get_password_hash("test"),
            full_name="Multi Day Test",
            role_system=RoleSystem.EMPLOYEE
        )
        session.add(user)
        session.commit()
        
        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Requirements for both days
        req1 = StaffingRequirement(date=today, shift_def_id=shift_definition.id, role_id=job_role.id, min_count=1)
        req2 = StaffingRequirement(date=tomorrow, shift_def_id=shift_definition.id, role_id=job_role.id, min_count=1)
        session.add(req1)
        session.add(req2)
        session.commit()

        # Add availability
        session.add(Availability(user_id=user.id, date=today, shift_def_id=shift_definition.id, status=AvailabilityStatus.AVAILABLE))
        session.add(Availability(user_id=user.id, date=tomorrow, shift_def_id=shift_definition.id, status=AvailabilityStatus.AVAILABLE))
        session.commit()
        
        service = SchedulerService(session)
        result = service.solve_schedule(today, tomorrow, save=False)
        
        assert result["status"] == "success"
        # Should have 2 assignments (1 per day)
        assert result["count"] == 2
    
    def test_solve_past_dates(self, session: Session):
        """Test solving for past dates"""
        service = SchedulerService(session)
        past = date.today() - timedelta(days=30)
        
        result = service.solve_schedule(past, past, save=False)
        
        # Should still work (just won't find data)
        assert result["status"] in ["success", "infeasible"]

    def test_monthly_target_lookahead_scarcity_distribution(
        self, session: Session, job_role, shift_definition
    ):
        """
        Test monthly target lookahead and scarcity distribution:
        - Employee A and Employee B both have 80h monthly target.
        - Employee A is 100% AVAILABLE in Week 1 (Nov 2-8) and 0% (UNAVAILABLE) in Week 2 (Nov 9-15).
        - Employee B is ~50% AVAILABLE in Week 1 (Mon-Thu, 4 days) and ~50% AVAILABLE in Week 2 (Mon-Thu, 4 days).
        - Verify that effective_weekly_target for Week 1 is higher for Employee A than Employee B,
          and that in Week 1 both receive hours aligned with their effective weekly targets
          (and Employee B is not skipped on their available days).
        """
        from app.services.scheduler_service import SchedulerService

        user_a = User(
            username="emp_a_lookahead",
            password_hash=get_password_hash("test"),
            full_name="Pracownik A",
            role_system=RoleSystem.EMPLOYEE,
            target_hours_per_month=80,
            is_active=True,
        )
        user_b = User(
            username="emp_b_lookahead",
            password_hash=get_password_hash("test"),
            full_name="Pracownik B",
            role_system=RoleSystem.EMPLOYEE,
            target_hours_per_month=80,
            is_active=True,
        )
        session.add(user_a)
        session.add(user_b)
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)

        session.add(UserJobRoleLink(user_id=user_a.id, role_id=job_role.id))
        session.add(UserJobRoleLink(user_id=user_b.id, role_id=job_role.id))
        session.commit()

        # Week 1: 2026-11-02 (Mon) .. 2026-11-08 (Sun)
        # Week 2: 2026-11-09 (Mon) .. 2026-11-15 (Sun)
        w1_start = date(2026, 11, 2)
        w1_end = date(2026, 11, 8)
        w2_start = date(2026, 11, 9)

        # Configure Week 1 staffing: Mon-Wed require 2 employees (both A and B can work),
        # Thu-Sun require 1 employee (only A is available Fri-Sun; Thu both available).
        for offset in range(7):
            d = w1_start + timedelta(days=offset)
            min_needed = 2 if offset < 3 else 1
            session.add(
                StaffingRequirement(
                    date=d,
                    shift_def_id=shift_definition.id,
                    role_id=job_role.id,
                    min_count=min_needed,
                )
            )
            # Employee A: 100% AVAILABLE in Week 1
            session.add(
                Availability(
                    user_id=user_a.id,
                    date=d,
                    shift_def_id=shift_definition.id,
                    status=AvailabilityStatus.AVAILABLE,
                )
            )
            # Employee B: AVAILABLE Mon-Thu (4 days), UNAVAILABLE Fri-Sun (3 days) in Week 1
            b_status_w1 = (
                AvailabilityStatus.AVAILABLE
                if offset < 4
                else AvailabilityStatus.UNAVAILABLE
            )
            session.add(
                Availability(
                    user_id=user_b.id,
                    date=d,
                    shift_def_id=shift_definition.id,
                    status=b_status_w1,
                )
            )

        # Configure Week 2 availability (Nov 9-15):
        # Employee A declared 0% (UNAVAILABLE all 7 days of Week 2)
        # Employee B declared ~50% (AVAILABLE Mon-Thu, UNAVAILABLE Fri-Sun)
        for offset in range(7):
            d2 = w2_start + timedelta(days=offset)
            session.add(
                Availability(
                    user_id=user_a.id,
                    date=d2,
                    shift_def_id=shift_definition.id,
                    status=AvailabilityStatus.UNAVAILABLE,
                )
            )
            b_status_w2 = (
                AvailabilityStatus.AVAILABLE
                if offset < 4
                else AvailabilityStatus.UNAVAILABLE
            )
            session.add(
                Availability(
                    user_id=user_b.id,
                    date=d2,
                    shift_def_id=shift_definition.id,
                    status=b_status_w2,
                )
            )
        session.commit()

        # 1. Verify compute_weekly_targets with monthly lookahead
        sched_service = SchedulerService(session)
        weekly_targets = sched_service.compute_weekly_targets(w1_start, w1_end)

        target_a = weekly_targets[user_a.id]
        target_b = weekly_targets[user_b.id]

        assert target_a["effective_weekly_target_hours"] > target_b["effective_weekly_target_hours"], (
            f"Expected Employee A effective target ({target_a['effective_weekly_target_hours']}h) "
            f"> Employee B ({target_b['effective_weekly_target_hours']}h)"
        )

        # 2. Run Solver for Week 1 with weekly_targets
        solver = SchedulerService(session)
        result = solver.solve_schedule(
            w1_start,
            w1_end,
            save=False,
            weekly_targets=weekly_targets,
        )

        assert result["status"] == "success"
        schedules = result["schedules"]

        shifts_a = [s for s in schedules if str(s["user_id"]) == str(user_a.id)]
        shifts_b = [s for s in schedules if str(s["user_id"]) == str(user_b.id)]

        hours_a = len(shifts_a) * 8.0
        hours_b = len(shifts_b) * 8.0

        # Employee A must get more hours in Week 1 than Employee B because A is unavailable in Week 2
        assert hours_a > hours_b, f"Expected hours_a ({hours_a}) > hours_b ({hours_b})"
        # Employee B is NOT skipped on their available days (gets at least 3 shifts = 24h)
        assert hours_b >= 24.0, f"Expected Employee B to get at least 24h in Week 1, got {hours_b}h"
        # Employee A gets at least 40h (5-6 shifts) in Week 1
        assert hours_a >= 40.0, f"Expected Employee A to get at least 40h in Week 1, got {hours_a}h"


    def test_pure_solver_input_dto_to_result_dto(self):
        """Pure Domain Engine test: SolverService.solve(SolverInputDTO) -> SolverResultDTO without DB."""
        target_day = date(2026, 11, 16).isoformat()
        input_dto = SolverInputDTO(
            start_date=target_day,
            end_date=target_day,
            shifts=[SolverShiftItem(id=1, name="Dzienna", start_time="08:00", end_time="16:00")],
            roles=[SolverRoleItem(id=10, name="Kelner")],
            employees=[
                SolverEmployeeItem(
                    id="emp-1",
                    full_name="Jan Kowalski",
                    role_ids=[10],
                    target_hours_per_month=160.0,
                )
            ],
            requirements=[
                SolverRequirementItem(date=target_day, shift_def_id=1, role_id=10, min_count=2)
            ],
            availabilities=[
                SolverAvailabilityItem(user_id="emp-1", date=target_day, shift_def_id=1, status="PREFERRED")
            ],
        )

        result = SolverService.solve(input_dto)

        assert isinstance(result, SolverResultDTO)
        assert result.status == "success"
        assert result.count == 1
        assert result.schedules[0].user_id == "emp-1"
        assert any(d.category == "ASSIGNED" and d.user_id == "emp-1" for d in result.decisions)
        assert any(d.category == "DEFICIT" and d.details.get("missing") == 1 for d in result.decisions)
        assert any(d.category == "EMPLOYEE_SUMMARY" and d.user_id == "emp-1" for d in result.decisions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
