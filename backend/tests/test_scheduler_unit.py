"""
Tests for Scheduler endpoints and SchedulerService
Tests schedule management, publishing, and manual assignments.
"""
import pytest
from httpx import AsyncClient
from datetime import date, timedelta
from uuid import uuid4

from backend.app.models import Schedule, ShiftDefinition, JobRole


class TestScheduleList:
    """Tests for /scheduler/list endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_schedules_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing schedules when none exist"""
        today = date.today()
        next_week = today + timedelta(days=7)
        
        response = await client.get(
            f"/scheduler/list?start_date={today}&end_date={next_week}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_list_schedules_with_data(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test listing schedules with existing data"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        
        schedule = Schedule(
            date=date.today(),
            shift_def_id=shift_definition.id,
            user_id=user.id,
            role_id=job_role.id,
            is_published=False
        )
        session.add(schedule)
        session.commit()
        
        today = date.today()
        response = await client.get(
            f"/scheduler/list?start_date={today}&end_date={today}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    @pytest.mark.asyncio
    async def test_list_schedules_date_range(self, client: AsyncClient, auth_headers: dict):
        """Test that date range filtering works correctly"""
        past = date.today() - timedelta(days=30)
        yesterday = date.today() - timedelta(days=1)
        
        response = await client.get(
            f"/scheduler/list?start_date={past}&end_date={yesterday}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestScheduleGeneration:
    """Tests for /scheduler/generate endpoint"""
    
    @pytest.mark.asyncio
    async def test_generate_schedule_success(self, client: AsyncClient, auth_headers: dict):
        """Test generating schedule (draft mode)"""
        today = date.today()
        next_week = today + timedelta(days=7)
        
        response = await client.post(
            "/scheduler/generate",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "end_date": str(next_week)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["success", "infeasible"]
    
    @pytest.mark.asyncio
    async def test_generate_schedule_single_day(self, client: AsyncClient, auth_headers: dict):
        """Test generating schedule for single day"""
        today = date.today()
        
        response = await client.post(
            "/scheduler/generate",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "end_date": str(today)
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_generate_requires_manager(self, client: AsyncClient, employee_headers: dict):
        """Test that only managers can generate schedules"""
        today = date.today()
        
        response = await client.post(
            "/scheduler/generate",
            headers=employee_headers,
            json={
                "start_date": str(today),
                "end_date": str(today)
            }
        )
        
        assert response.status_code == 403


class TestSchedulePublish:
    """Tests for /scheduler/publish endpoint"""
    
    @pytest.mark.asyncio
    async def test_publish_schedule_empty(self, client: AsyncClient, auth_headers: dict):
        """Test publishing when no schedules exist"""
        today = date.today()
        
        response = await client.post(
            f"/scheduler/publish?start_date={today}&end_date={today}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["count"] == 0
    
    @pytest.mark.asyncio
    async def test_publish_schedule_with_data(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test publishing existing schedules"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        
        # Create unpublished schedule
        schedule = Schedule(
            date=date.today(),
            shift_def_id=shift_definition.id,
            user_id=user.id,
            role_id=job_role.id,
            is_published=False
        )
        session.add(schedule)
        session.commit()
        
        today = date.today()
        response = await client.post(
            f"/scheduler/publish?start_date={today}&end_date={today}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "published"
    
    @pytest.mark.asyncio
    async def test_publish_requires_manager(self, client: AsyncClient, employee_headers: dict):
        """Test that only managers can publish schedules"""
        today = date.today()
        
        response = await client.post(
            f"/scheduler/publish?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        
        assert response.status_code == 403


class TestManualAssignment:
    """Tests for /scheduler/assignment endpoints"""
    
    @pytest.mark.asyncio
    async def test_manual_assignment_create(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test creating manual assignment"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        
        response = await client.post(
            "/scheduler/assignment",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "shift_def_id": shift_definition.id,
                "user_id": str(user.id),
                "role_id": job_role.id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["created", "updated"]
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_manual_assignment_update(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test updating existing assignment for same user/date"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        today = date.today()
        
        # Create first assignment
        await client.post(
            "/scheduler/assignment",
            headers=auth_headers,
            json={
                "date": str(today),
                "shift_def_id": shift_definition.id,
                "user_id": str(user.id),
                "role_id": job_role.id
            }
        )
        
        # Update with same user/date (different shift would apply if we had one)
        response = await client.post(
            "/scheduler/assignment",
            headers=auth_headers,
            json={
                "date": str(today),
                "shift_def_id": shift_definition.id,
                "user_id": str(user.id),
                "role_id": job_role.id
            }
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "updated"
    
    @pytest.mark.asyncio
    async def test_remove_assignment_success(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test removing an assignment"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        
        # Create assignment first
        create_resp = await client.post(
            "/scheduler/assignment",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "shift_def_id": shift_definition.id,
                "user_id": str(user.id),
                "role_id": job_role.id
            }
        )
        
        schedule_id = create_resp.json()["id"]
        
        # Delete it
        response = await client.delete(
            f"/scheduler/assignment/{schedule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
    
    @pytest.mark.asyncio
    async def test_remove_assignment_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test removing non-existent assignment"""
        fake_uuid = str(uuid4())
        
        response = await client.delete(
            f"/scheduler/assignment/{fake_uuid}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_remove_assignment_invalid_uuid(self, client: AsyncClient, auth_headers: dict):
        """Test removing with invalid UUID format"""
        response = await client.delete(
            "/scheduler/assignment/not-a-valid-uuid",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "not_found"


class TestBatchSave:
    """Tests for /scheduler/save_batch endpoint"""
    
    @pytest.mark.asyncio
    async def test_save_batch_empty(self, client: AsyncClient, auth_headers: dict):
        """Test saving empty batch"""
        today = date.today()
        
        response = await client.post(
            "/scheduler/save_batch",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "end_date": str(today),
                "items": []
            }
        )
        
        assert response.status_code == 200
        assert response.json()["count"] == 0
    
    @pytest.mark.asyncio
    async def test_save_batch_with_items(
        self, client: AsyncClient, auth_headers: dict,
        session, shift_definition, job_role
    ):
        """Test saving batch with items"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        today = date.today()
        
        response = await client.post(
            "/scheduler/save_batch",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "end_date": str(today),
                "items": [{
                    "date": str(today),
                    "shift_def_id": shift_definition.id,
                    "user_id": str(user.id),
                    "role_id": job_role.id
                }]
            }
        )
        
        assert response.status_code == 200
        assert response.json()["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
