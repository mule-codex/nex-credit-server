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
