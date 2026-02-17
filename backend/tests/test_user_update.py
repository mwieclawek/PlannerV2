"""
Regression test for user update (target hours/shifts) - fixes 500 error.
Tests the UserResponse serialization with job_roles and target fields.
"""
import pytest
from uuid import uuid4
from sqlmodel import Session

from app.models import User, JobRole, UserJobRoleLink, RoleSystem
from app.schemas import UserResponse, UserUpdate
from app.services.manager_service import ManagerService
from app.auth_utils import get_password_hash


class TestUserResponseSerialization:
    """Test that UserResponse correctly serializes User ORM objects."""

    def test_user_response_with_job_roles(self, session: Session, job_role):
        """UserResponse must convert JobRole objects to int IDs."""
        user = User(
            username="serial_test",
            password_hash=get_password_hash("test"),
            full_name="Serialization Test",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(user)
        session.commit()

        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()

        session.refresh(user)

        response = UserResponse.model_validate(user, from_attributes=True)
        assert isinstance(response.job_roles, list)
        assert len(response.job_roles) == 1
        assert response.job_roles[0] == job_role.id
        assert isinstance(response.job_roles[0], int)

    def test_user_response_with_target_fields(self, session: Session):
        """UserResponse must include target_hours and target_shifts."""
        user = User(
            username="target_test",
            password_hash=get_password_hash("test"),
            full_name="Target Test",
            role_system=RoleSystem.EMPLOYEE,
            target_hours_per_month=180,
            target_shifts_per_month=20,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        response = UserResponse.model_validate(user, from_attributes=True)
        assert response.target_hours_per_month == 180
        assert response.target_shifts_per_month == 20

    def test_user_response_with_none_targets(self, session: Session):
        """UserResponse must handle None targets gracefully."""
        user = User(
            username="none_target",
            password_hash=get_password_hash("test"),
            full_name="None Target",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        response = UserResponse.model_validate(user, from_attributes=True)
        assert response.target_hours_per_month is None
        assert response.target_shifts_per_month is None


class TestUserUpdateService:
    """Test updating user target hours/shifts via ManagerService."""

    def test_update_target_hours(self, session: Session):
        """Updating target_hours_per_month should persist."""
        user = User(
            username="update_hours",
            password_hash=get_password_hash("test"),
            full_name="Update Hours",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(user)
        session.commit()

        service = ManagerService(session)
        update = UserUpdate(target_hours_per_month=160)
        updated = service.update_user(user.id, update)

        assert updated.target_hours_per_month == 160
        assert updated.full_name == "Update Hours"  # Unchanged

    def test_update_target_shifts(self, session: Session):
        """Updating target_shifts_per_month should persist."""
        user = User(
            username="update_shifts",
            password_hash=get_password_hash("test"),
            full_name="Update Shifts",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(user)
        session.commit()

        service = ManagerService(session)
        update = UserUpdate(target_shifts_per_month=25)
        updated = service.update_user(user.id, update)

        assert updated.target_shifts_per_month == 25

    def test_update_with_roles_serializes(self, session: Session, job_role):
        """After update, response must still serialize job_roles correctly."""
        user = User(
            username="update_serial",
            password_hash=get_password_hash("test"),
            full_name="Update Serial",
            role_system=RoleSystem.EMPLOYEE,
        )
        session.add(user)
        session.commit()

        link = UserJobRoleLink(user_id=user.id, role_id=job_role.id)
        session.add(link)
        session.commit()

        service = ManagerService(session)
        update = UserUpdate(target_hours_per_month=100)
        updated = service.update_user(user.id, update)

        # Verify serialization works
        response = UserResponse.model_validate(updated, from_attributes=True)
        assert response.target_hours_per_month == 100
        assert response.job_roles == [job_role.id]

    def test_partial_update_preserves_other_fields(self, session: Session):
        """Partial update should not wipe existing data."""
        user = User(
            username="partial_update",
            password_hash=get_password_hash("test"),
            full_name="Partial Update",
            role_system=RoleSystem.EMPLOYEE,
            target_hours_per_month=160,
            target_shifts_per_month=20,
        )
        session.add(user)
        session.commit()

        service = ManagerService(session)
        # Only update hours, shifts should remain
        update = UserUpdate(target_hours_per_month=180)
        updated = service.update_user(user.id, update)

        assert updated.target_hours_per_month == 180
        assert updated.target_shifts_per_month == 20  # Preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
