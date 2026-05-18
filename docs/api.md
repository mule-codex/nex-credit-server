# API Documentation

Base URL for local development: `http://localhost:5000`

All request and response bodies are JSON.

## Authentication

### Register

Creates a user account. Login is phone-based, so include `phone_number` for users who need to sign in.

`POST /api/register`

Request:

```json
{
  "full_name": "Chanda Banda",
  "email": "chanda@example.com",
  "phone_number": "0970000000",
  "password": "pass123"
}
```

Success response:

```json
{
  "success": true,
  "message": "User registered successfully"
}
```

Common errors:

| Status | Message |
|---|---|
| `400` | `Missing required fields` |
| `409` | `Email already exists` |
| `409` | `Phone number already exists` |

### Request login OTP

Starts login with only the user's phone number. The server generates a 6-digit OTP, saves it in `login_otps`, and sends it using the configured Zamtel SMS API.

`POST /api/login`

Request:

```json
{
  "phone_number": "0970000000"
}
```

Success response:

```json
{
  "success": true,
  "message": "OTP sent successfully"
}
```

Common errors:

| Status | Message |
|---|---|
| `400` | `Phone number required` |
| `404` | `Phone number not registered` |
| `403` | `Account disabled` |
| `502` | `Zamtel SMS credentials are not configured` |

### Submit login OTP

Completes login with the phone number and OTP. A valid, unexpired, unused OTP is marked consumed and the response returns a JWT plus the user object.

`POST /api/login/otp`

Request:

```json
{
  "phone_number": "0970000000",
  "otp": "123456"
}
```

Success response:

```json
{
  "success": true,
  "message": "Login successful",
  "token": "jwt-token",
  "user": {
    "id": 1,
    "full_name": "Chanda Banda",
    "email": "chanda@example.com",
    "phone_number": "0970000000",
    "role": "borrower"
  }
}
```

Common errors:

| Status | Message |
|---|---|
| `400` | `Phone number and OTP required` |
| `401` | `OTP validation failed` |
| `403` | `Account disabled` |

### Authenticated requests

Send the JWT from `POST /api/login/otp` as a bearer token.

```http
Authorization: Bearer jwt-token
```

Protected examples:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/me` | Returns the decoded authenticated user token payload |
| `GET` | `/api/protected` | Confirms protected route access |

## Admin user management

Admin routes require a bearer token whose user has `role: "admin"`.

### List users

`GET /api/admin/users`

Query parameters:

| Name | Description |
|---|---|
| `search` | Optional search across `full_name`, `email`, `student_number`, and `phone_number` |
| `role` | Optional role filter: `borrower`, `lender`, `rep`, `admin`, or `agent` |
| `is_active` | Optional status filter: `0` or `1` |
| `page` | Optional page number, defaults to `1` |
| `limit` | Optional page size from `1` to `100`, defaults to `20` |

### Get a user

`GET /api/admin/users/{user_id}`

Returns the full serialized user record, including status, verification, failed attempts, and timestamps.

### Create a user

`POST /api/admin/users`

Request:

```json
{
  "full_name": "Lender User",
  "email": "lender@example.com",
  "phone_number": "0970000001",
  "password": "password123",
  "role": "lender",
  "is_active": 1,
  "is_verified": 0
}
```

Success response:

```json
{
  "success": true,
  "message": "User created successfully",
  "user_id": 2
}
```

### Update a user

`PATCH /api/admin/users/{user_id}`

Allowed fields: `student_number`, `full_name`, `university`, `email`, `phone_number`, `role`, `is_active`, `is_verified`.

### Update user status

`PATCH /api/admin/users/{user_id}/status`

Request:

```json
{
  "is_active": 0
}
```

### Reset user password

`PATCH /api/admin/users/{user_id}/reset-password`

Request:

```json
{
  "password": "newpassword123"
}
```

Common admin errors:

| Status | Message |
|---|---|
| `400` | `Invalid role. Must be one of: borrower, lender, rep, admin, agent` |
| `400` | `Password must be at least 8 characters` |
| `401` | `Token missing` |
| `403` | `Admin access required` |
| `404` | `User not found` |
| `409` | `Email already exists` |
| `409` | `Phone number already exists` |
| `409` | `Student number already exists` |

## Admin university management

The list route is public. Get, create, update, and delete routes require a bearer token whose user has `role: "admin"`.

### List universities

`GET /api/admin/universities`

This route does not require authentication.

Query parameters:

| Name | Description |
|---|---|
| `search` | Optional search across `name`, `code`, and `city` |
| `is_active` | Optional status filter: `0` or `1` |
| `page` | Optional page number, defaults to `1` |
| `limit` | Optional page size from `1` to `100`, defaults to `20` |

### Get a university

`GET /api/admin/universities/{university_id}`

### Create a university

`POST /api/admin/universities`

Request:

```json
{
  "name": "University of Zambia",
  "code": "UNZA",
  "city": "Lusaka",
  "is_active": 1
}
```

Success response:

```json
{
  "success": true,
  "message": "University created successfully",
  "university_id": 1
}
```

### Update a university

`PATCH /api/admin/universities/{university_id}`

Allowed fields: `name`, `code`, `city`, `is_active`.

### Delete a university

`DELETE /api/admin/universities/{university_id}`

Common university errors:

| Status | Message |
|---|---|
| `400` | `name is required` |
| `400` | `No valid fields provided` |
| `401` | `Token missing` |
| `403` | `Admin access required` |
| `404` | `University not found` |
| `409` | `University name already exists` |
| `409` | `University code already exists` |

## Zamtel SMS configuration

Set these variables in `backend/.env`:

```env
LOGIN_OTP_EXPIRES_SECONDS=300
ZAMTEL_API_KEY=your-zamtel-api-key
ZAMTEL_SENDER_ID=your-zamtel-sender-id
ZAMTEL_BASE_URL=https://bulksms.zamtel.co.zm/api/v2.1/action/send/
```

The OTP sender implements the Bulk SMS third-party interface v2.1.1. It sends a `POST` request using this official path shape:

```text
https://bulksms.zamtel.co.zm/api/v2.1/action/send/api_key/:api_key/contacts/:contacts/senderId/:sender_id/message/:message
```

Phone numbers are normalized to Zamtel's `260...` contact format before sending. For example, `0970000000`, `+260970000000`, and `260970000000` are sent as `260970000000`.
