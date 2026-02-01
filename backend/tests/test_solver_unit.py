"""
Unit tests for SolverService (CP-SAT constraint programming solver)
Tests optimization logic, constraints, and edge cases.
"""
import pytest
from datetime import date, timedelta
from sqlmodel import Session

from backend.app.models import (
    User, JobRole, ShiftDefinition, Availability, 
    StaffingRequirement, Schedule, RoleSystem, AvailabilityStatus,
    UserJobRoleLink
)
from backend.app.services.solver import SolverService
from backend.app.auth_utils import get_password_hash


class TestSolverBasic:
    """Basic solver functionality tests"""
    
    def test_solve_empty_data(self, session: Session):
        """Test solver with no employees, shifts, or roles"""
        service = SolverService(session)
        today = date.today()
        
        result = service.solve(today, today, save=False)
        
        assert result["status"] in ["success", "infeasible"]
        assert result["count"] == 0
    
    def test_solve_no_requirements(self, session: Session, job_role, shift_definition):
        """Test solver with no staffing requirements"""
        # Create employee with role
        user = User(
            email="solver_test@test.com",
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
        
        service = SolverService(session)
        today = date.today()
        
        result = service.solve(today, today, save=False)
        
        # Without requirements, solver should produce 0 assignments
        assert result["status"] == "success"
        assert result["count"] == 0
    
    def test_solve_with_requirement(self, session: Session, job_role, shift_definition):
        """Test solver with a requirement"""
        # Create employee with role
        user = User(
            email="solver_req_test@test.com",
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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
        assert result["status"] == "success"
        assert result["count"] == 1


class TestSolverConstraints:
    """Tests for solver constraints"""
    
    def test_solve_unavailable_employee_not_assigned(
        self, session: Session, job_role, shift_definition
    ):
        """Test that unavailable employee is not assigned"""
        user = User(
            email="unavail_test@test.com",
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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
        # Should not assign unavailable employee
        assert result["count"] == 0
        # Should have warning about understaffing
        assert len(result.get("warnings", [])) > 0
    
    def test_solve_one_shift_per_day(self, session: Session, job_role):
        """Test that employee gets max 1 shift per day"""
        from datetime import time
        # Create two shifts
        shift1 = ShiftDefinition(name="Morning Test", start_time=time(6, 0), end_time=time(14, 0))
        shift2 = ShiftDefinition(name="Evening Test", start_time=time(14, 0), end_time=time(22, 0))
        session.add(shift1)
        session.add(shift2)
        session.commit()
        
        user = User(
            email="oneshift_test@test.com",
            password_hash=get_password_hash("test"),
            full_name="One Shift Test",
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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
        # With only 1 employee, max 1 shift can be assigned
        user_assignments = [s for s in result.get("schedules", []) if str(s.user_id) == str(user.id)]
        assert len(user_assignments) <= 1
    
    def test_solve_role_matching(self, session: Session, shift_definition):
        """Test that employees are only assigned to roles they have"""
        role1 = JobRole(name="Barista Test", color_hex="#8B4513")
        role2 = JobRole(name="Cashier Test", color_hex="#228B22")
        session.add(role1)
        session.add(role2)
        session.commit()
        
        # Create employee with only role1
        user = User(
            email="role_match@test.com",
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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
        # User should not be assigned since they don't have role2
        user_for_role2 = [s for s in result.get("schedules", []) if s.role_id == role2.id]
        assert len(user_for_role2) == 0


class TestSolverPreferences:
    """Tests for preference optimization"""
    
    def test_solve_prefers_preferred_employee(self, session: Session, job_role, shift_definition):
        """Test that preferred availability is prioritized"""
        # Create two employees
        user1 = User(
            email="pref_user1@test.com",
            password_hash=get_password_hash("test"),
            full_name="Preferred User",
            role_system=RoleSystem.EMPLOYEE
        )
        user2 = User(
            email="pref_user2@test.com",
            password_hash=get_password_hash("test"),
            full_name="Neutral User",
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
        
        # User1 prefers, User2 neutral
        avail1 = Availability(
            user_id=user1.id, date=today, 
            shift_def_id=shift_definition.id, status=AvailabilityStatus.PREFERRED
        )
        avail2 = Availability(
            user_id=user2.id, date=today,
            shift_def_id=shift_definition.id, status=AvailabilityStatus.NEUTRAL
        )
        session.add(avail1)
        session.add(avail2)
        
        # Require only 1 person
        req = StaffingRequirement(date=today, shift_def_id=shift_definition.id, role_id=job_role.id, min_count=1)
        session.add(req)
        session.commit()
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
        if result["count"] == 1:
            assigned = result["schedules"][0]
            # Should prefer user1 (PREFERRED > NEUTRAL)
            assert str(assigned.user_id) == str(user1.id)


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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
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
            email="nosave_test@test.com",
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
        
        service = SolverService(session)
        result = service.solve(today, today, save=False)
        
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
            email="multiday@test.com",
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
        
        service = SolverService(session)
        result = service.solve(today, tomorrow, save=False)
        
        assert result["status"] == "success"
        # Should have 2 assignments (1 per day)
        assert result["count"] == 2
    
    def test_solve_past_dates(self, session: Session):
        """Test solving for past dates"""
        service = SolverService(session)
        past = date.today() - timedelta(days=30)
        
        result = service.solve(past, past, save=False)
        
        # Should still work (just won't find data)
        assert result["status"] in ["success", "infeasible"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
