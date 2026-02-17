import pytest
from app.models import RestaurantConfig, User, RoleSystem
from app.auth_utils import create_access_token, get_password_hash
from uuid import uuid4

@pytest.fixture(name="manager_token")
def manager_token_fixture(session):
    user = User(
        username=f"mgr_{uuid4().hex[:8]}",
        password_hash=get_password_hash("secret"),
        full_name="Sprint Manager",
        role_system=RoleSystem.MANAGER
    )
    session.add(user)
    session.commit()
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

class TestConfigUpdate:
    @pytest.mark.anyio
    async def test_partial_update_validation(self, client, session, manager_token):
        # Setup initial config
        session.add(RestaurantConfig(id=1, name="Original", opening_hours="{}"))
        session.commit()

        # Try to update only name (missing opening_hours)
        resp = await client.post(
            "/manager/config",
            json={"name": "Updated Name"},
            headers=manager_token
        )
        
        # Currently this should fail with 422 because opening_hours is required
        # But we want it to succeed (200) after fix
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        # opening_hours should be unchanged if we don't send it? 
        # But backend replaces it? 
        # If schema is Optional, backend needs logic to only update provided fields.
