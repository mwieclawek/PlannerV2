"""
Tests for Employee endpoints
Tests availability and schedule retrieval for employees.
"""
import pytest
from httpx import AsyncClient
from datetime import date, timedelta

from backend.app.models import ShiftDefinition, Availability, Schedule, JobRole, AvailabilityStatus


class TestEmployeeAvailability:
    """Tests for /employee/availability endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_availability_empty(self, client: AsyncClient, employee_headers: dict):
        """Test getting availability when none exists"""
        today = date.today()
        next_week = today + timedelta(days=7)
        
        response = await client.get(
            f"/employee/availability?start_date={today}&end_date={next_week}",
            headers=employee_headers
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_get_availability_with_data(
        self, client: AsyncClient, employee_headers: dict, 
        session, shift_definition
    ):
        """Test getting availability when data exists"""
        from backend.app.models import User
        from sqlmodel import select
        
        # Get user from token
        user = session.exec(select(User).where(User.email == "employee@test.com")).first()
        
        # Create availability
        avail = Availability(
            user_id=user.id,
            date=date.today(),
            shift_def_id=shift_definition.id,
            status=AvailabilityStatus.PREFERRED
        )
        session.add(avail)
        session.commit()
        
        today = date.today()
        response = await client.get(
            f"/employee/availability?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "PREFERRED"
    
    @pytest.mark.asyncio
    async def test_update_availability_single(
        self, client: AsyncClient, employee_headers: dict, shift_definition
    ):
        """Test updating single availability entry"""
        today = date.today()
        
        response = await client.post(
            "/employee/availability",
            headers=employee_headers,
            json=[{
                "date": str(today),
                "shift_def_id": shift_definition.id,
                "status": "PREFERRED"
            }]
        )
        
        assert response.status_code == 200
        assert response.json()["updated"] == 1
    
    @pytest.mark.asyncio
    async def test_update_availability_multiple(
        self, client: AsyncClient, employee_headers: dict, shift_definition
    ):
        """Test updating multiple availability entries"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        response = await client.post(
            "/employee/availability",
            headers=employee_headers,
            json=[
                {"date": str(today), "shift_def_id": shift_definition.id, "status": "PREFERRED"},
                {"date": str(tomorrow), "shift_def_id": shift_definition.id, "status": "UNAVAILABLE"}
            ]
        )
        
        assert response.status_code == 200
        assert response.json()["updated"] == 2
    
    @pytest.mark.asyncio
    async def test_update_availability_overwrites_existing(
        self, client: AsyncClient, employee_headers: dict, shift_definition
    ):
        """Test that updating availability overwrites existing entry"""
        today = date.today()
        
        # First update
        await client.post(
            "/employee/availability",
            headers=employee_headers,
            json=[{"date": str(today), "shift_def_id": shift_definition.id, "status": "PREFERRED"}]
        )
        
        # Second update (should overwrite)
        await client.post(
            "/employee/availability",
            headers=employee_headers,
            json=[{"date": str(today), "shift_def_id": shift_definition.id, "status": "UNAVAILABLE"}]
        )
        
        # Check result
        response = await client.get(
            f"/employee/availability?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have only one entry with UNAVAILABLE status
        matching = [a for a in data if a["shift_def_id"] == shift_definition.id]
        assert len(matching) == 1
        assert matching[0]["status"] == "UNAVAILABLE"


class TestEmployeeSchedule:
    """Tests for /employee/my-schedule endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_my_schedule_empty(self, client: AsyncClient, employee_headers: dict):
        """Test getting schedule when none exists"""
        today = date.today()
        next_week = today + timedelta(days=7)
        
        response = await client.get(
            f"/employee/my-schedule?start_date={today}&end_date={next_week}",
            headers=employee_headers
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_get_my_schedule_with_data(
        self, client: AsyncClient, employee_headers: dict,
        session, shift_definition, job_role
    ):
        """Test getting schedule when data exists"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User).where(User.email == "employee@test.com")).first()
        
        # Create schedule entry
        schedule = Schedule(
            date=date.today(),
            shift_def_id=shift_definition.id,
            user_id=user.id,
            role_id=job_role.id,
            is_published=True
        )
        session.add(schedule)
        session.commit()
        
        today = date.today()
        response = await client.get(
            f"/employee/my-schedule?start_date={today}&end_date={today}",
            headers=employee_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestEmployeeUnauthorized:
    """Tests for unauthorized access"""
    
    @pytest.mark.asyncio
    async def test_get_availability_no_token(self, client: AsyncClient):
        """Test that availability endpoint requires authentication"""
        today = date.today()
        
        response = await client.get(
            f"/employee/availability?start_date={today}&end_date={today}"
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_availability_no_token(self, client: AsyncClient):
        """Test that update availability requires authentication"""
        response = await client.post(
            "/employee/availability",
            json=[{"date": str(date.today()), "shift_def_id": 1, "status": "PREFERRED"}]
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_my_schedule_no_token(self, client: AsyncClient):
        """Test that my-schedule endpoint requires authentication"""
        today = date.today()
        
        response = await client.get(
            f"/employee/my-schedule?start_date={today}&end_date={today}"
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_availability_invalid_token(self, client: AsyncClient):
        """Test that invalid token is rejected"""
        today = date.today()
        
        response = await client.get(
            f"/employee/availability?start_date={today}&end_date={today}",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
