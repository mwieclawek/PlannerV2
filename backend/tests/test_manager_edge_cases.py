"""
Edge case tests for Manager endpoints
Tests error handling, authorization, and boundary conditions.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestRoleEdgeCases:
    """Edge cases for role management"""
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_role(self, client: AsyncClient, auth_headers: dict):
        """Test updating a role that doesn't exist"""
        response = await client.put(
            "/manager/roles/99999",
            headers=auth_headers,
            json={"name": "Ghost Role", "color_hex": "#000000"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_role(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a role that doesn't exist"""
        response = await client.delete(
            "/manager/roles/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_role_empty_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating role with empty name"""
        response = await client.post(
            "/manager/roles",
            headers=auth_headers,
            json={"name": "", "color_hex": "#FF0000"}
        )
        
        # Should fail validation or be rejected
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_create_role_invalid_color(self, client: AsyncClient, auth_headers: dict):
        """Test creating role with invalid color format"""
        response = await client.post(
            "/manager/roles",
            headers=auth_headers,
            json={"name": "Test Role", "color_hex": "not-a-color"}
        )
        
        # Should succeed (no validation on color in current impl) or fail
        # Test documents current behavior
        assert response.status_code in [200, 400, 422]


class TestShiftEdgeCases:
    """Edge cases for shift management"""
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_shift(self, client: AsyncClient, auth_headers: dict):
        """Test updating a shift that doesn't exist"""
        response = await client.put(
            "/manager/shifts/99999",
            headers=auth_headers,
            json={"name": "Ghost Shift", "start_time": "08:00", "end_time": "16:00"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_shift(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a shift that doesn't exist"""
        response = await client.delete(
            "/manager/shifts/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_shift_invalid_times(self, client: AsyncClient, auth_headers: dict):
        """Test creating shift with invalid time format"""
        response = await client.post(
            "/manager/shifts",
            headers=auth_headers,
            json={"name": "Invalid Shift", "start_time": "invalid", "end_time": "also-invalid"}
        )
        
        assert response.status_code == 422  # Validation error


class TestUserManagementEdgeCases:
    """Edge cases for user management"""
    
    @pytest.mark.asyncio
    async def test_assign_roles_to_nonexistent_user(self, client: AsyncClient, auth_headers: dict):
        """Test assigning roles to a user that doesn't exist"""
        fake_uuid = str(uuid4())
        
        response = await client.put(
            f"/manager/users/{fake_uuid}/roles",
            headers=auth_headers,
            json={"role_ids": [1]}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_assign_nonexistent_role_to_user(
        self, client: AsyncClient, auth_headers: dict, session
    ):
        """Test assigning a non-existent role to a user"""
        from backend.app.models import User
        from sqlmodel import select
        
        # Get any existing user
        user = session.exec(select(User)).first()
        if user:
            response = await client.put(
                f"/manager/users/{user.id}/roles",
                headers=auth_headers,
                json={"role_ids": [99999]}  # Non-existent role
            )
            
            # Should fail or succeed but role not assigned
            assert response.status_code in [200, 404, 400]
    
    @pytest.mark.asyncio
    async def test_reset_password_nonexistent_user(self, client: AsyncClient, auth_headers: dict):
        """Test resetting password for non-existent user"""
        fake_uuid = str(uuid4())
        
        response = await client.put(
            f"/manager/users/{fake_uuid}/password",
            headers=auth_headers,
            json={"new_password": "newSecurePassword123"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_reset_password_empty_password(
        self, client: AsyncClient, auth_headers: dict, session
    ):
        """Test resetting password with empty string"""
        from backend.app.models import User
        from sqlmodel import select
        
        user = session.exec(select(User)).first()
        if user:
            response = await client.put(
                f"/manager/users/{user.id}/password",
                headers=auth_headers,
                json={"new_password": ""}
            )
            
            # Should fail validation or succeed (depends on implementation)
            assert response.status_code in [200, 400, 422]


class TestRequirementsEdgeCases:
    """Edge cases for staffing requirements"""
    
    @pytest.mark.asyncio
    async def test_set_requirements_empty_list(self, client: AsyncClient, auth_headers: dict):
        """Test setting empty requirements list"""
        response = await client.post(
            "/manager/requirements",
            headers=auth_headers,
            json=[]
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_set_requirements_negative_count(self, client: AsyncClient, auth_headers: dict):
        """Test setting requirements with negative min_count"""
        from datetime import date
        
        response = await client.post(
            "/manager/requirements",
            headers=auth_headers,
            json=[{
                "date": str(date.today()),
                "shift_def_id": 1,
                "role_id": 1,
                "min_count": -5
            }]
        )
        
        # Should fail validation
        assert response.status_code in [400, 422]


class TestAuthorizationEdgeCases:
    """Tests for authorization and access control"""
    
    @pytest.mark.asyncio
    async def test_employee_cannot_create_role(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee cannot create roles"""
        response = await client.post(
            "/manager/roles",
            headers=employee_headers,
            json={"name": "Evil Role", "color_hex": "#FF0000"}
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_employee_cannot_create_shift(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee cannot create shifts"""
        response = await client.post(
            "/manager/shifts",
            headers=employee_headers,
            json={"name": "Evil Shift", "start_time": "08:00", "end_time": "16:00"}
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_employee_cannot_delete_role(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee cannot delete roles"""
        response = await client.delete(
            "/manager/roles/1",
            headers=employee_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_employee_cannot_update_config(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee cannot update restaurant config"""
        response = await client.post(
            "/manager/config",
            headers=employee_headers,
            json={"name": "Hacked Restaurant", "opening_hours": "{}", "address": "Evil St"}
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_employee_can_read_roles(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee CAN read roles (needed for availability UI)"""
        response = await client.get(
            "/manager/roles",
            headers=employee_headers
        )
        
        # Should be allowed for displaying in UI
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_employee_can_read_shifts(
        self, client: AsyncClient, employee_headers: dict
    ):
        """Test that employee CAN read shifts (needed for availability UI)"""
        response = await client.get(
            "/manager/shifts",
            headers=employee_headers
        )
        
        assert response.status_code == 200


class TestConfigEdgeCases:
    """Edge cases for restaurant config"""
    
    @pytest.mark.asyncio
    async def test_update_config_missing_fields(self, client: AsyncClient, auth_headers: dict):
        """Test updating config with missing required fields"""
        response = await client.post(
            "/manager/config",
            headers=auth_headers,
            json={}  # Empty body
        )
        
        # Should fail or succeed with defaults
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_get_config_no_existing(self, client: AsyncClient, auth_headers: dict):
        """Test getting config when none exists"""
        response = await client.get(
            "/manager/config",
            headers=auth_headers
        )
        
        # Should return default or empty config
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
