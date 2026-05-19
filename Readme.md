# NexCredit API

Backend API for NexCredit built with Flask, JWT authentication, OTP login, MySQL, and role-based access control.

## Features

- OTP Authentication via SMS
- JWT Authentication
- Auto User Registration
- Role-Based Access Control
- Admin User Management
- University Management
- MySQL Database Integration
- Zamtel SMS Integration
- Secure Password Hashing
- Pagination & Search

---

# Base URL

Production:

 txt
https://funsa.online
 

Local:

 txt
http://127.0.0.1:5000
 

---

# Authentication

The API uses JWT Bearer Tokens.

After login verification, include the token in headers:

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

---

# Environment Variables

Create a `.env` file:

 env
SECRET_KEY=super-secret-key

ZAMTEL_API_KEY=your_api_key
ZAMTEL_SENDER_ID=your_sender_id
ZAMTEL_BASE_URL=https://bulksms.zamtel.co.zm/api/v2.1/action/send/

LOGIN_OTP_EXPIRES_SECONDS=300
 

---

# Installation

## Clone Repository

 bash
git clone https://github.com/yourusername/nexcredit.git
cd nexcredit
 

## Create Virtual Environment

 bash
python -m venv venv
 

## Activate Virtual Environment

### Windows

 bash
venv\Scripts\activate
 

### Linux / Mac

 bash
source venv/bin/activate
 

## Install Dependencies

 bash
pip install -r requirements.txt
 

## Run Server

 bash
python app.py
 

---

# API Endpoints

# Health Check

## GET /

Returns API status.

### Response

 
{
  "success": true,
  "message": "JWT API running"
}
 

---

# Authentication

## Login / Request OTP

### POST /api/login

### Request

 
{
  "phone_number": "260975223474"
}
 

### Response

 
{
  "success": true,
  "message": "OTP sent successfully",
  "otp_session_id": "uuid"
}
 

---

## Verify OTP Login

### POST /api/login/otp

### Request

 
{
  "phone_number": "260975223474",
  "otp": "123456"
}
 

### Response

 
{
  "success": true,
  "message": "Login successful",
  "token": "jwt_token",
  "user": {
    "id": 1,
    "phone_number": "260975223474",
    "role": "borrower",
    "is_verified": true
  }
}
 

---

## Get Current User

### GET /api/me

### Headers

 http
Authorization: Bearer TOKEN
 

### Response

 
{
  "success": true,
  "user": {}
}
 

---

# Admin APIs

Admin routes require:

 txt
role = admin
 

---

# Users Management

## Get Users

### GET /api/admin/users

### Query Parameters

| Parameter | Description |
|---|---|
| search | Search users |
| role | Filter by role |
| is_active | 0 or 1 |
| page | Pagination page |
| limit | Records per page |

### Example

 txt
/api/admin/users?page=1&limit=20
 

---

## Get Single User

### GET /api/admin/users/:id

---

## Create User

### POST /api/admin/users

### Request

 
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "260977000000",
  "role": "borrower",
  "password": "password123"
}
 

---

## Update User

### PATCH /api/admin/users/:id

### Request

 
{
  "full_name": "Updated Name"
}
 

---

## Activate / Deactivate User

### PATCH /api/admin/users/:id/status

### Request

 
{
  "is_active": 1
}
 

---

## Reset User Password

### PATCH /api/admin/users/:id/reset-password

### Request

 
{
  "password": "newpassword123"
}
 

---

# Universities Management

---

## Get University

### GET /api/admin/universities/:id

---

## Create University

### POST /api/admin/universities

### Request

 
{
  "name": "University of Zambia",
  "code": "UNZA",
  "city": "Lusaka"
}
 

---

## Update University

### PATCH /api/admin/universities/:id

---

## Delete University

### DELETE /api/admin/universities/:id

---

# User Roles

Supported roles:

 txt
borrower
lender
rep
admin
agent
 

---

# Security Features

- JWT Authentication
- OTP Expiration
- OTP Session Tracking
- Password Hashing
- Role-Based Authorization
- User Activation Controls
- Duplicate Prevention
- Verification Attempt Tracking

---

# OTP Login Flow

1. User submits phone number
2. API auto-registers user if not existing
3. OTP generated and sent via Zamtel SMS
4. User submits OTP
5. JWT token issued
6. Authenticated requests use Bearer Token

---

# Tech Stack

- Flask
- MySQL
- JWT
- Flask-CORS
- Werkzeug Security
- Zamtel SMS API

---

# Example CURL Requests

## Login

 bash
curl -X POST https://funsa.online/api/login ^
-H "Content-Type: application/json" ^
-d "{\"phone_number\":\"260975223474\"}"
 

---

## Verify OTP

 bash
curl -X POST https://funsa.online/api/login/otp ^
-H "Content-Type: application/json" ^
-d "{\"phone_number\":\"260975223474\",\"otp\":\"123456\"}"
 

---

## Get Current User

 bash
curl -X GET https://funsa.online/api/me ^
-H "Authorization: Bearer YOUR_TOKEN"
 

---

# Deployment

Production uses:

- Passenger WSGI
- Python 3.9
- MySQL
- Apache/Nginx

Entry point:

 python
application = app
 

---

# License

Private Proprietary Software

Copyright NexCredit