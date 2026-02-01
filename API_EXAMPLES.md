# API Examples

Base URL: `http://localhost:8000`

## Authentication

### Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User",
    "role_system": "EMPLOYEE"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Login
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"
```

### Get Current User
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Manager Endpoints

### Create Role
```bash
curl -X POST http://localhost:8000/manager/roles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Barista",
    "color_hex": "#10B981"
  }'
```

### Get All Roles
```bash
curl -X GET http://localhost:8000/manager/roles \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Shift
```bash
curl -X POST http://localhost:8000/manager/shifts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Poranna",
    "start_time": "06:00",
    "end_time": "14:00"
  }'
```

### Set Staffing Requirements
```bash
curl -X POST http://localhost:8000/manager/requirements \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "date": "2026-02-01",
      "shift_def_id": 1,
      "role_id": 1,
      "min_count": 2
    },
    {
      "date": "2026-02-01",
      "shift_def_id": 2,
      "role_id": 1,
      "min_count": 3
    }
  ]'
```

### Assign Role to User
```bash
curl -X POST http://localhost:8000/manager/users/roles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID_HERE",
    "role_id": 1
  }'
```

## Employee Endpoints

### Get My Availability
```bash
curl -X GET "http://localhost:8000/employee/availability?start_date=2026-02-01&end_date=2026-02-07" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Availability
```bash
curl -X POST http://localhost:8000/employee/availability \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "date": "2026-02-01",
      "shift_def_id": 1,
      "status": "PREFERRED"
    },
    {
      "date": "2026-02-01",
      "shift_def_id": 2,
      "status": "UNAVAILABLE"
    },
    {
      "date": "2026-02-02",
      "shift_def_id": 1,
      "status": "NEUTRAL"
    }
  ]'
```

## Scheduler Endpoints

### Generate Schedule
```bash
curl -X POST http://localhost:8000/scheduler/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-02-01",
    "end_date": "2026-02-07"
  }'
```

Response (Success):
```json
{
  "status": "success",
  "count": 14,
  "schedules": [
    {
      "id": "uuid",
      "date": "2026-02-01",
      "shift_def_id": 1,
      "user_id": "user_uuid",
      "role_id": 1,
      "is_published": false
    }
  ]
}
```

Response (Infeasible):
```json
{
  "status": "infeasible",
  "count": 0
}
```

## Status Codes

- `200` - Success
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (not a manager)
- `400` - Bad Request (validation error)
- `500` - Internal Server Error

## Availability Status Values

- `PREFERRED` - Employee wants to work
- `NEUTRAL` - Employee can work
- `AVAILABLE` - Default, no preference
- `UNAVAILABLE` - Employee cannot work

## Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI with interactive API testing.
