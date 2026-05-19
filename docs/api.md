# Funsa API Documentation

Base URL:
[https://funsa.online] 

## Authentication

Most endpoints require a Bearer token.

Add this header to authenticated requests:

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

---

# Authentication Routes

## Login / Auto Register

Creates a new borrower account automatically if the phone number does not already exist, then sends an OTP via SMS.

### Endpoint

 http
POST /api/login
 

### Full URL

 http
https://funsa.online/api/login
 

### Request Body

 
{
  "phone_number": "0977123456"
}
 

### Success Response

 
{
  "success": true,
  "message": "OTP sent successfully",
  "otp_session_id": "8c64b4dc-74df-41cb-88a8-ef5dbef4c58"
}
 

### Error Responses

 
{
  "success": false,
  "message": "phone_number is required"
}
 

 
{
  "success": false,
  "message": "Account disabled"
}
 

---

## Verify Login OTP

Verifies OTP and returns a JWT token.

### Endpoint

 http
POST /api/login/otp
 

### Full URL

 http
https://funsa.online/api/login/otp
 

### Request Body

 
{
  "phone_number": "0977123456",
  "otp": "123456"
}
 

### Success Response

 
{
  "success": true,
  "message": "Login successful",
  "token": "JWT_TOKEN",
  "user": {
    "id": 1,
    "student_number": null,
    "full_name": null,
    "university": null,
    "email": null,
    "phone_number": "260977123456",
    "role": "borrower",
    "is_verified": true
  }
}
 

### Error Responses

 
{
  "success": false,
  "message": "Invalid OTP"
}
 

 
{
  "success": false,
  "message": "OTP expired"
}
 

---

# User Routes

## Get Current User

Returns authenticated user information.

### Endpoint

 http
GET /api/me
 

### Full URL

 http
https://funsa.online/api/me
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Success Response

 
{
  "success": true,
  "user": {
    "id": 1,
    "student_number": "20240001",
    "full_name": "John Doe",
    "university": "UNZA",
    "email": "john@example.com",
    "phone_number": "260977123456",
    "role": "borrower",
    "is_active": true,
    "is_verified": true,
    "failed_attempts": 0,
    "last_login_at": "2026-05-19T10:00:00",
    "created_at": "2026-05-01T10:00:00",
    "updated_at": "2026-05-10T10:00:00"
  }
}
 

---

# Product Routes

## Create Product

Creates a new marketplace product.

### Endpoint

 http
POST /api/products
 

### Full URL

 http
https://funsa.online/api/products
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Request Body

 
{
  "title": "MacBook Pro",
  "description": "M2 MacBook Pro 16GB RAM",
  "price": 25000,
  "category": "Electronics",
  "image_url": "https://example.com/image.jpg"
}
 

### Success Response

 
{
  "success": true,
  "message": "Product created successfully",
  "product_id": 1
}
 

---

## Get Products

Returns paginated available products.

### Endpoint

 http
GET /api/products
 

### Full URL

 http
https://funsa.online/api/products
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Query Parameters

| Parameter | Type    | Description                    |
| --------- | ------- | ------------------------------ |
| search    | string  | Search by title or description |
| category  | string  | Filter by category             |
| page      | integer | Pagination page                |
| limit     | integer | Results per page               |

### Example

 http
GET /api/products?search=laptop&category=Electronics&page=1&limit=10
 

### Success Response

 
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "MacBook Pro",
      "description": "M2 MacBook Pro",
      "price": 25000,
      "category": "Electronics",
      "image_url": "https://example.com/image.jpg",
      "owner_id": 1,
      "is_available": true,
      "created_at": "2026-05-19T10:00:00",
      "updated_at": "2026-05-19T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "total_pages": 1
  }
}
 

---

## Get Product By ID

### Endpoint

 http
GET /api/products/{product_id}
 

### Full URL

 http
https://funsa.online/api/products/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Success Response

 
{
  "success": true,
  "data": {
    "id": 1,
    "title": "MacBook Pro",
    "description": "M2 MacBook Pro",
    "price": 25000,
    "category": "Electronics",
    "image_url": "https://example.com/image.jpg",
    "owner_id": 1,
    "is_available": true,
    "created_at": "2026-05-19T10:00:00",
    "updated_at": "2026-05-19T10:00:00"
  }
}
 

---

## Update Product

Only the product owner can update the product.

### Endpoint

 http
PATCH /api/products/{product_id}
 

### Full URL

 http
https://funsa.online/api/products/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Request Body

 
{
  "price": 23000,
  "is_available": true
}
 

### Success Response

 
{
  "success": true,
  "message": "Product updated successfully"
}
 

---

## Delete Product

Only the product owner can delete the product.

### Endpoint

 http
DELETE /api/products/{product_id}
 

### Full URL

 http
https://funsa.online/api/products/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Success Response

 
{
  "success": true,
  "message": "Product deleted successfully"
}
 

---

# Loan Listing Routes

## Create Loan Listing

Creates a new loan request/listing.

### Endpoint

 http
POST /api/loan-listings
 

### Full URL

 http
https://funsa.online/api/loan-listings
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Request Body

 
{
  "amount": 5000,
  "interest_rate": 15,
  "duration_months": 6,
  "purpose": "School fees"
}
 

### Success Response

 
{
  "success": true,
  "message": "Loan listing created successfully",
  "loan_listing_id": 1
}
 

---

## Get Loan Listings

Returns paginated loan listings.

### Endpoint

 http
GET /api/loan-listings
 

### Full URL

 http
https://funsa.online/api/loan-listings
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Query Parameters

| Parameter | Type    | Description           |
| --------- | ------- | --------------------- |
| status    | string  | Filter by loan status |
| page      | integer | Pagination page       |
| limit     | integer | Results per page      |

### Example

 http
GET /api/loan-listings?status=OPEN&page=1&limit=10
 

### Success Response

 
{
  "success": true,
  "data": [
    {
      "id": 1,
      "borrower_id": 1,
      "amount": 5000,
      "interest_rate": 15,
      "duration_months": 6,
      "purpose": "School fees",
      "status": "OPEN",
      "created_at": "2026-05-19T10:00:00",
      "updated_at": "2026-05-19T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "total_pages": 1
  }
}
 

---

## Get Loan Listing By ID

### Endpoint

 http
GET /api/loan-listings/{loan_id}
 

### Full URL

 http
https://funsa.online/api/loan-listings/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Success Response

 
{
  "success": true,
  "data": {
    "id": 1,
    "borrower_id": 1,
    "amount": 5000,
    "interest_rate": 15,
    "duration_months": 6,
    "purpose": "School fees",
    "status": "OPEN",
    "created_at": "2026-05-19T10:00:00",
    "updated_at": "2026-05-19T10:00:00"
  }
}
 

---

## Update Loan Listing

Only the borrower who created the listing can update it.

### Endpoint

 http
PATCH /api/loan-listings/{loan_id}
 

### Full URL

 http
https://funsa.online/api/loan-listings/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Request Body

 
{
  "amount": 6000,
  "interest_rate": 12,
  "status": "OPEN"
}
 

### Success Response

 
{
  "success": true,
  "message": "Loan listing updated successfully"
}
 

---

## Delete Loan Listing

Only the borrower who created the listing can delete it.

### Endpoint

 http
DELETE /api/loan-listings/{loan_id}
 

### Full URL

 http
https://funsa.online/api/loan-listings/1
 

### Headers

 http
Authorization: Bearer YOUR_JWT_TOKEN
 

### Success Response

 
{
  "success": true,
  "message": "Loan listing deleted successfully"
}
 

---

# Health Check

## API Status

### Endpoint

 http
GET /
 

### Full URL

 http
https://funsa.online/
 

### Success Response

 
{
  "success": true,
  "message": "JWT API running"
}
 

---

# Common Error Responses

## Unauthorized

 
{
  "success": false,
  "message": "Authorization token missing"
}
 

 
{
  "success": false,
  "message": "Invalid token"
}
 

 
{
  "success": false,
  "message": "Token expired"
}
 

---

## Forbidden

 
{
  "success": false,
  "message": "Unauthorized"
}
 

 
{
  "success": false,
  "message": "Account disabled"
}
 

---

## Validation Errors

 
{
  "success": false,
  "message": "No valid fields provided"
}
 

 
{
  "success": false,
  "message": "Product not found"
}
 

 
{
  "success": false,
  "message": "Loan listing not found"
}
 
