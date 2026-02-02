"""
Unit tests for auth_utils.py
Tests password hashing, token creation, and token validation.
"""
import pytest
from datetime import timedelta
from jose import jwt, JWTError

from backend.app.auth_utils import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    SECRET_KEY,
    ALGORITHM
)


class TestPasswordHashing:
    """Password hashing and verification tests"""
    
    def test_password_hash_and_verify_success(self):
        """Test that hashed password can be verified"""
        password = "securePassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password  # Hash should be different
        assert verify_password(password, hashed) is True
    
    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)"""
        password = "samePassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salting
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_password_verify_wrong_password(self):
        """Test that wrong password fails verification"""
        password = "correctPassword"
        wrong_password = "wrongPassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_empty_string(self):
        """Test hashing empty password (edge case)"""
        password = ""
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False
    
    def test_password_hash_unicode(self):
        """Test hashing unicode passwords"""
        password = "hasło_z_polskimi_znakami_ąęść"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_hash_long_password(self):
        """Test hashing very long password"""
        password = "a" * 1000
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True


class TestTokenCreation:
    """JWT token creation tests"""
    
    def test_create_access_token_default_expiry(self):
        """Test token creation with default expiry"""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)
        
        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should be decodable
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@example.com"
        assert "exp" in payload
    
    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry"""
        data = {"sub": "test@test.com"}
        expires = timedelta(hours=2)
        token = create_access_token(data, expires_delta=expires)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@test.com"
    
    def test_create_access_token_preserves_data(self):
        """Test that additional data is preserved in token"""
        data = {"sub": "user@test.com", "role": "admin", "custom_field": 123}
        token = create_access_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@test.com"
        assert payload["role"] == "admin"
        assert payload["custom_field"] == 123
    
    def test_create_access_token_expired(self):
        """Test that expired tokens raise error on decode"""
        data = {"sub": "user@test.com"}
        # Create token that expires immediately (negative delta)
        expires = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires)
        
        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TestTokenValidation:
    """JWT token validation edge cases"""
    
    def test_token_decode_invalid_signature(self):
        """Test that token with wrong secret fails"""
        data = {"sub": "user@test.com"}
        token = create_access_token(data)
        
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong_secret_key", algorithms=[ALGORITHM])
    
    def test_token_decode_invalid_algorithm(self):
        """Test that token with wrong algorithm fails"""
        data = {"sub": "user@test.com"}
        token = create_access_token(data)
        
        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=["HS384"])
    
    def test_token_malformed(self):
        """Test that malformed token raises error"""
        with pytest.raises(JWTError):
            jwt.decode("not.a.valid.token", SECRET_KEY, algorithms=[ALGORITHM])
    
    def test_token_empty(self):
        """Test that empty token raises error"""
        with pytest.raises(JWTError):
            jwt.decode("", SECRET_KEY, algorithms=[ALGORITHM])


class TestAuthMeEndpoint:
    """Tests for /auth/me endpoint response format"""
    
    @pytest.mark.asyncio
    async def test_auth_me_returns_required_fields(self, client, auth_headers):
        """Test that /auth/me returns all fields expected by frontend"""
        response = await client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Frontend User.fromJson expects these fields
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert "role_system" in data
        assert "created_at" in data  # Critical field for frontend
        
    @pytest.mark.asyncio
    async def test_auth_me_created_at_is_parseable(self, client, auth_headers):
        """Test that created_at is a valid ISO datetime string"""
        response = await client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify created_at can be parsed as datetime
        from datetime import datetime
        created_at = data.get("created_at")
        assert created_at is not None
        # Should not raise exception
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    
    @pytest.mark.asyncio
    async def test_auth_me_role_system_is_string(self, client, auth_headers):
        """Test that role_system is a string value (MANAGER or EMPLOYEE)"""
        response = await client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role_system"] in ["MANAGER", "EMPLOYEE"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
