

import os
import secrets
from urllib.parse import quote
from urllib.request import Request, urlopen

import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from functools import wraps
from datetime import datetime, timedelta, timezone
import json
from db import get_connection
import uuid

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
app = Flask(__name__)
 
app.config["SECRET_KEY"] = "super-secret-key"

CORS(app)

ALLOWED_ROLES = ("borrower", "lender", "rep", "admin", "agent")


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()

    return jsonify({
        "success": False,
        "message": str(e)
    }), 500
 
def serialize_university(university):
    return {
        "id": university["id"],
        "name": university["name"],
        "code": university.get("code"),
        "city": university.get("city"),
        "is_active": bool(university["is_active"]),
        "created_at": (
            university["created_at"].isoformat()
            if university.get("created_at") else None
        ),
        "updated_at": (
            university["updated_at"].isoformat()
            if university.get("updated_at") else None
        ),
    }

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def normalize_phone_number(phone_number):
    if not phone_number:
        return None

    digits = "".join(ch for ch in str(phone_number) if ch.isdigit())

    if digits.startswith("260") and len(digits) == 12:
        return digits

    if digits.startswith("0") and len(digits) == 10:
        return f"260{digits[1:]}"

    return digits
    
def generate_otp():
    return f"{secrets.randbelow(1000000):06d}"

def get_otp_expires_at():
    ttl_seconds = int(os.getenv("LOGIN_OTP_EXPIRES_SECONDS", "300"))
    return utc_now() + timedelta(seconds=ttl_seconds)
 
def serialize_user(user):

    return {
        "id": user["id"],
        "student_number": user.get("student_number"),
        "full_name": user.get("full_name"),
        "university": user.get("university"),
        "email": user.get("email"),
        "phone_number": user.get("phone_number"),
        "role": user["role"],
        "is_active": bool(user["is_active"]),
        "is_verified": bool(user["is_verified"]),
        "failed_attempts": user.get("failed_attempts", 0),
        "last_login_at": (
            user["last_login_at"].isoformat()
            if user.get("last_login_at")
            else None
        ),
        "created_at": (
            user["created_at"].isoformat()
            if user.get("created_at")
            else None
        ),
        "updated_at": (
            user["updated_at"].isoformat()
            if user.get("updated_at")
            else None
        ),
    }

def build_user_response(user):

    return {
        "id": user["id"],
        "student_number": user.get("student_number"),
        "full_name": user.get("full_name"),
        "university": user.get("university"),
        "email": user.get("email"),
        "phone_number": user.get("phone_number"),
        "role": user["role"],
        "is_verified": bool(user.get("is_verified", 0)),
    }

def generate_token(user):

    payload = {
        "user_id": user["id"],
        "phone_number": user.get("phone_number"),
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }

    token = jwt.encode(
        payload,
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return token

def send_otp_sms(phone_number, otp):

    api_key = os.getenv("ZAMTEL_API_KEY")
    sender_id = os.getenv("ZAMTEL_SENDER_ID")

    base_url = os.getenv(
        "ZAMTEL_BASE_URL",
        "https://bulksms.zamtel.co.zm/api/v2.1/action/send/"
    )

    if not api_key or not sender_id:
        raise RuntimeError("Zamtel SMS credentials are not configured")

    normalized_phone = normalize_phone_number(phone_number)

    message = (
        f"Your NexCredit login OTP is {otp}. "
        f"It expires in 5 minutes."
    )

    endpoint = (
        f"{base_url.rstrip('/')}/"
        f"api_key/{quote(api_key, safe='')}/"
        f"contacts/{quote(normalized_phone, safe='')}/"
        f"senderId/{quote(sender_id, safe='')}/"
        f"message/{quote(message, safe='')}"
    )

    request_obj = Request(endpoint, method="POST")

    with urlopen(request_obj, timeout=10) as response:
        body = response.read().decode("utf-8")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {
            "success": False,
            "responseText": body
        }

    if payload.get("success") is False:
        raise RuntimeError(
            payload.get("responseText", "SMS sending failed")
        )

    return payload
 
def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "success": False,
                "message": "Authorization token missing"
            }), 401

        try:
            bearer, token = auth_header.split(" ")

            if bearer.lower() != "bearer":
                raise ValueError()

        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid authorization header format"
            }), 401

        try:

            decoded = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )

            user_id = decoded.get("user_id")

            connection = get_connection()

            try:
                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT
                            id,
                            student_number,
                            full_name,
                            university,
                            email,
                            phone_number,
                            role,
                            is_active,
                            is_verified,
                            failed_attempts,
                            last_login_at,
                            created_at,
                            updated_at
                        FROM users
                        WHERE id = %s
                        """,
                        (user_id,)
                    )

                    user = cursor.fetchone()

            finally:
                connection.close()

            if not user:
                return jsonify({
                    "success": False,
                    "message": "User no longer exists"
                }), 401

            if not user["is_active"]:
                return jsonify({
                    "success": False,
                    "message": "Account disabled"
                }), 403

            request.user = user

        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token expired"
            }), 401

        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid token"
            }), 401

        return f(*args, **kwargs)

    return decorated


# =========================
# LOGIN + AUTO REGISTER
# =========================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    phone_number = normalize_phone_number(
        data.get("phone_number")
    )

    if not phone_number:
        return jsonify({
            "success": False,
            "message": "phone_number is required"
        }), 400

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # =========================
            # FIND EXISTING USER
            # =========================

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE phone_number = %s
                LIMIT 1
                """,
                (phone_number,)
            )

            user = cursor.fetchone()

            # =========================
            # AUTO REGISTER
            # =========================

            if not user:

                cursor.execute(
                    """
                    INSERT INTO users (
                        phone_number,
                        role,
                        is_active,
                        is_verified,
                        failed_attempts
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        phone_number,
                        "borrower",
                        1,
                        0,
                        0
                    )
                )

                user_id = cursor.lastrowid

                cursor.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )

                user = cursor.fetchone()

            # =========================
            # ACCOUNT STATUS
            # =========================

            if not user["is_active"]:

                return jsonify({
                    "success": False,
                    "message": "Account disabled"
                }), 403

            # =========================
            # EXPIRE OLD OTPS
            # =========================

            cursor.execute(
                """
                UPDATE login_otp_sessions
                SET state = 'EXPIRED'
                WHERE phone_number = %s
                  AND state IN (
                    'CREATED',
                    'QUEUED',
                    'SENT',
                    'DELIVERED'
                  )
                """,
                (phone_number,)
            )

            # =========================
            # GENERATE OTP
            # =========================

            otp = generate_otp()

            otp_hash = generate_password_hash(otp)

            expires_at = get_otp_expires_at()

            otp_session_id = str(uuid.uuid4())

            # =========================
            # CREATE OTP SESSION
            # =========================

            cursor.execute(
                """
                INSERT INTO login_otp_sessions (
                    otp_session_id,
                    user_id,
                    phone_number,
                    otp_hash,
                    state,
                    verification_attempts,
                    resend_count,
                    provider_name,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    otp_session_id,
                    user["id"],
                    phone_number,
                    otp_hash,
                    "CREATED",
                    0,
                    0,
                    "zamtel",
                    expires_at
                )
            )

        # =========================
        # SEND OTP SMS
        # =========================

        try:

            send_otp_sms(phone_number, otp)

        except RuntimeError as exc:

            connection.rollback()

            return jsonify({
                "success": False,
                "message": str(exc)
            }), 502

        # =========================
        # UPDATE SESSION STATUS
        # =========================

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE login_otp_sessions
                SET state = 'SENT'
                WHERE otp_session_id = %s
                """,
                (otp_session_id,)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "OTP sent successfully",
            "otp_session_id": otp_session_id
        }), 200

    finally:
        connection.close()


@app.route("/api/login/otp", methods=["POST"])
def login_otp():

    data = request.get_json(silent=True) or {}

    phone_number = normalize_phone_number(
        data.get("phone_number")
    )

    otp = data.get("otp")

    if not phone_number or not otp:
        return jsonify({
            "success": False,
            "message": "phone_number and otp are required"
        }), 400

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.*,
                    u.id AS user_id,
                    u.student_number,
                    u.full_name,
                    u.university,
                    u.email,
                    u.phone_number,
                    u.role,
                    u.is_active,
                    u.is_verified
                FROM login_otp_sessions s
                JOIN users u
                    ON u.id = s.user_id
                WHERE s.phone_number = %s
                  AND s.state IN (
                      'CREATED',
                      'QUEUED',
                      'SENT',
                      'DELIVERED'
                  )
                ORDER BY s.created_at DESC
                LIMIT 1
                """,
                (phone_number,)
            )

            otp_record = cursor.fetchone()

            if not otp_record:
                return jsonify({
                    "success": False,
                    "message": "OTP session not found"
                }), 404

            # =========================
            # EXPIRED
            # =========================

            if otp_record["expires_at"] < utc_now():

                cursor.execute(
                    """
                    UPDATE login_otp_sessions
                    SET state = 'EXPIRED'
                    WHERE id = %s
                    """,
                    (otp_record["id"],)
                )

                connection.commit()

                return jsonify({
                    "success": False,
                    "message": "OTP expired"
                }), 401

            # =========================
            # ACCOUNT STATUS
            # =========================

            if not otp_record["is_active"]:
                return jsonify({
                    "success": False,
                    "message": "Account disabled"
                }), 403

            # =========================
            # VERIFY OTP
            # =========================

            valid_otp = check_password_hash(
                otp_record["otp_hash"],
                otp
            )

            if not valid_otp:

                cursor.execute(
                    """
                    UPDATE login_otp_sessions
                    SET verification_attempts =
                        verification_attempts + 1
                    WHERE id = %s
                    """,
                    (otp_record["id"],)
                )

                connection.commit()

                return jsonify({
                    "success": False,
                    "message": "Invalid OTP"
                }), 401

            # =========================
            # CONSUME OTP
            # =========================

            cursor.execute(
                """
                UPDATE login_otp_sessions
                SET
                    state = 'CONSUMED',
                    consumed_at = UTC_TIMESTAMP()
                WHERE id = %s
                """,
                (otp_record["id"],)
            )

            # =========================
            # UPDATE USER
            # =========================

            cursor.execute(
                """
                UPDATE users
                SET
                    last_login_at = UTC_TIMESTAMP(),
                    is_verified = 1
                WHERE id = %s
                """,
                (otp_record["user_id"],)
            )

        connection.commit()

        user = {
            "id": otp_record["user_id"],
            "student_number": otp_record.get("student_number"),
            "full_name": otp_record.get("full_name"),
            "university": otp_record.get("university"),
            "email": otp_record.get("email"),
            "phone_number": otp_record["phone_number"],
            "role": otp_record["role"],
            "is_verified": 1,
        }

        token = generate_token(user)

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": build_user_response(user)
        }), 200

    finally:
        connection.close()


# =========================================
# SERIALIZERS
# =========================================

def serialize_product(product):
    return {
        "id": product["id"],
        "title": product["title"],
        "description": product.get("description"),
        "price": float(product["price"]),
        "category": product.get("category"),
        "image_url": product.get("image_url"),
        "owner_id": product["owner_id"],
        "is_available": bool(product["is_available"]),
        "created_at": (
            product["created_at"].isoformat()
            if product.get("created_at")
            else None
        ),
        "updated_at": (
            product["updated_at"].isoformat()
            if product.get("updated_at")
            else None
        ),
    }


def serialize_loan_listing(loan):
    return {
        "id": loan["id"],
        "borrower_id": loan["borrower_id"],
        "amount": float(loan["amount"]),
        "interest_rate": float(loan["interest_rate"]),
        "duration_months": loan["duration_months"],
        "purpose": loan.get("purpose"),
        "status": loan["status"],
        "created_at": (
            loan["created_at"].isoformat()
            if loan.get("created_at")
            else None
        ),
        "updated_at": (
            loan["updated_at"].isoformat()
            if loan.get("updated_at")
            else None
        ),
    }


# =========================================
# PRODUCT ROUTES
# =========================================

@app.route("/api/products", methods=["POST"])
@token_required
def create_product():

    data = request.get_json(silent=True) or {}

    title = data.get("title")
    description = data.get("description")
    price = data.get("price")
    category = data.get("category")
    image_url = data.get("image_url")

    if not title:
        return jsonify({
            "success": False,
            "message": "title is required"
        }), 400

    if price is None:
        return jsonify({
            "success": False,
            "message": "price is required"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO products (
                    title,
                    description,
                    price,
                    category,
                    image_url,
                    owner_id,
                    is_available
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    title,
                    description,
                    price,
                    category,
                    image_url,
                    request.user["id"],
                    1
                )
            )

            product_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Product created successfully",
            "product_id": product_id
        }), 201

    finally:
        connection.close()


@app.route("/api/products", methods=["GET"])
@token_required
def get_products():

    search = request.args.get("search")
    category = request.args.get("category")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    page = max(page, 1)

    if limit < 1 or limit > 100:
        limit = 20

    filters = ["is_available = 1"]
    params = []

    if search:
        filters.append(
            """
            (
                title LIKE %s
                OR description LIKE %s
            )
            """
        )

        search_term = f"%{search}%"

        params.extend([search_term, search_term])

    if category:
        filters.append("category = %s")
        params.append(category)

    where_sql = "WHERE " + " AND ".join(filters)

    offset = (page - 1) * limit

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM products
                {where_sql}
                """,
                params
            )

            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT *
                FROM products
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )

            products = cursor.fetchall()

        return jsonify({
            "success": True,
            "data": [
                serialize_product(product)
                for product in products
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (
                    (total + limit - 1) // limit
                )
            }
        }), 200

    finally:
        connection.close()


@app.route("/api/products/<int:product_id>", methods=["GET"])
@token_required
def get_product(product_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM products
                WHERE id = %s
                """,
                (product_id,)
            )

            product = cursor.fetchone()

        if not product:
            return jsonify({
                "success": False,
                "message": "Product not found"
            }), 404

        return jsonify({
            "success": True,
            "data": serialize_product(product)
        }), 200

    finally:
        connection.close()


@app.route("/api/products/<int:product_id>", methods=["PATCH"])
@token_required
def update_product(product_id):

    data = request.get_json(silent=True) or {}

    allowed_fields = (
        "title",
        "description",
        "price",
        "category",
        "image_url",
        "is_available"
    )

    updates = []
    params = []

    for field in allowed_fields:

        if field in data:

            updates.append(f"`{field}` = %s")

            if field == "is_available":
                params.append(int(bool(data[field])))
            else:
                params.append(data[field])

    if not updates:
        return jsonify({
            "success": False,
            "message": "No valid fields provided"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM products
                WHERE id = %s
                """,
                (product_id,)
            )

            product = cursor.fetchone()

            if not product:
                return jsonify({
                    "success": False,
                    "message": "Product not found"
                }), 404

            if product["owner_id"] != request.user["id"]:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 403

            params.append(product_id)

            cursor.execute(
                f"""
                UPDATE products
                SET {', '.join(updates)}
                WHERE id = %s
                """,
                params
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Product updated successfully"
        }), 200

    finally:
        connection.close()


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@token_required
def delete_product(product_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM products
                WHERE id = %s
                """,
                (product_id,)
            )

            product = cursor.fetchone()

            if not product:
                return jsonify({
                    "success": False,
                    "message": "Product not found"
                }), 404

            if product["owner_id"] != request.user["id"]:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 403

            cursor.execute(
                """
                DELETE FROM products
                WHERE id = %s
                """,
                (product_id,)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Product deleted successfully"
        }), 200

    finally:
        connection.close()


# =========================================
# LOAN LISTING ROUTES
# =========================================

@app.route("/api/loan-listings", methods=["POST"])
@token_required
def create_loan_listing():

    data = request.get_json(silent=True) or {}

    amount = data.get("amount")
    interest_rate = data.get("interest_rate")
    duration_months = data.get("duration_months")
    purpose = data.get("purpose")

    if amount is None:
        return jsonify({
            "success": False,
            "message": "amount is required"
        }), 400

    if interest_rate is None:
        return jsonify({
            "success": False,
            "message": "interest_rate is required"
        }), 400

    if duration_months is None:
        return jsonify({
            "success": False,
            "message": "duration_months is required"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO loan_listings (
                    borrower_id,
                    amount,
                    interest_rate,
                    duration_months,
                    purpose,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    request.user["id"],
                    amount,
                    interest_rate,
                    duration_months,
                    purpose,
                    "OPEN"
                )
            )

            loan_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Loan listing created successfully",
            "loan_listing_id": loan_id
        }), 201

    finally:
        connection.close()


@app.route("/api/loan-listings", methods=["GET"])
@token_required
def get_loan_listings():

    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    page = max(page, 1)

    if limit < 1 or limit > 100:
        limit = 20

    filters = []
    params = []

    if status:
        filters.append("status = %s")
        params.append(status)

    where_sql = ""

    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    offset = (page - 1) * limit

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM loan_listings
                {where_sql}
                """,
                params
            )

            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT *
                FROM loan_listings
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )

            loans = cursor.fetchall()

        return jsonify({
            "success": True,
            "data": [
                serialize_loan_listing(loan)
                for loan in loans
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (
                    (total + limit - 1) // limit
                )
            }
        }), 200

    finally:
        connection.close()


@app.route("/api/loan-listings/<int:loan_id>", methods=["GET"])
@token_required
def get_loan_listing(loan_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM loan_listings
                WHERE id = %s
                """,
                (loan_id,)
            )

            loan = cursor.fetchone()

        if not loan:
            return jsonify({
                "success": False,
                "message": "Loan listing not found"
            }), 404

        return jsonify({
            "success": True,
            "data": serialize_loan_listing(loan)
        }), 200

    finally:
        connection.close()


@app.route("/api/loan-listings/<int:loan_id>", methods=["PATCH"])
@token_required
def update_loan_listing(loan_id):

    data = request.get_json(silent=True) or {}

    allowed_fields = (
        "amount",
        "interest_rate",
        "duration_months",
        "purpose",
        "status"
    )

    updates = []
    params = []

    for field in allowed_fields:

        if field in data:
            updates.append(f"`{field}` = %s")
            params.append(data[field])

    if not updates:
        return jsonify({
            "success": False,
            "message": "No valid fields provided"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM loan_listings
                WHERE id = %s
                """,
                (loan_id,)
            )

            loan = cursor.fetchone()

            if not loan:
                return jsonify({
                    "success": False,
                    "message": "Loan listing not found"
                }), 404

            if loan["borrower_id"] != request.user["id"]:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 403

            params.append(loan_id)

            cursor.execute(
                f"""
                UPDATE loan_listings
                SET {', '.join(updates)}
                WHERE id = %s
                """,
                params
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Loan listing updated successfully"
        }), 200

    finally:
        connection.close()


@app.route("/api/loan-listings/<int:loan_id>", methods=["DELETE"])
@token_required
def delete_loan_listing(loan_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM loan_listings
                WHERE id = %s
                """,
                (loan_id,)
            )

            loan = cursor.fetchone()

            if not loan:
                return jsonify({
                    "success": False,
                    "message": "Loan listing not found"
                }), 404

            if loan["borrower_id"] != request.user["id"]:
                return jsonify({
                    "success": False,
                    "message": "Unauthorized"
                }), 403

            cursor.execute(
                """
                DELETE FROM loan_listings
                WHERE id = %s
                """,
                (loan_id,)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Loan listing deleted successfully"
        }), 200

    finally:
        connection.close()
# =========================
# GET CURRENT USER
# =========================

@app.route("/api/me", methods=["GET"])
@token_required
def me():

    return jsonify({
        "success": True,
        "user": serialize_user(request.user)
    }), 200
 
def admin_required(f):

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if request.user.get("role") != "admin":
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        return f(*args, **kwargs)

    return decorated

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "JWT API running"
    })
  
 
 
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_get_users():

    search = request.args.get("search")
    role = request.args.get("role")
    is_active = request.args.get("is_active")
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)

    page = max(page, 1)
    if limit < 1 or limit > 100:
        limit = 20

    if role and role not in ALLOWED_ROLES:
        return jsonify({
            "success": False,
            "message": f"Invalid role. Must be one of: {', '.join(ALLOWED_ROLES)}"
        }), 400

    if is_active is not None and is_active not in ("0", "1"):
        return jsonify({
            "success": False,
            "message": "is_active must be 0 or 1"
        }), 400

    filters = []
    params = []

    if search:
        filters.append(
            """
            (
                full_name LIKE %s
                OR email LIKE %s
                OR student_number LIKE %s
                OR phone_number LIKE %s
            )
            """
        )
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    if role:
        filters.append("role = %s")
        params.append(role)

    if is_active is not None:
        filters.append("is_active = %s")
        params.append(int(is_active))

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    offset = (page - 1) * limit
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM users {where_sql}",
                params
            )
            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT id, student_number, full_name, university, email,
                       phone_number, role, is_active, is_verified,
                       failed_attempts, last_login_at, created_at, updated_at
                FROM users
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )
            users = cursor.fetchall()

        return jsonify({
            "success": True,
            "data": [serialize_user(user) for user in users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            }
        })

    finally:
        connection.close()
 
@app.route("/api/admin/users/<int:user_id>", methods=["GET"])
@admin_required
def admin_get_user(user_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, student_number, full_name, university, email,
                       phone_number, role, is_active, is_verified,
                       failed_attempts, last_login_at, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        return jsonify({
            "success": True,
            "data": serialize_user(user)
        })

    finally:
        connection.close()
 
@app.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_create_user():

    data = request.get_json(silent=True) or {}

    student_number = data.get("student_number")
    full_name = data.get("full_name")
    university = data.get("university")
    email = data.get("email")
    phone_number = data.get("phone_number")
    role = data.get("role", "borrower")
    password = data.get("password")
    is_active = data.get("is_active", 1)
    is_verified = data.get("is_verified", 0)

    if not full_name or not password:
        return jsonify({
            "success": False,
            "message": "full_name and password are required"
        }), 400

    if not email and not phone_number:
        return jsonify({
            "success": False,
            "message": "Either email or phone_number is required"
        }), 400

    if role not in ALLOWED_ROLES:
        return jsonify({
            "success": False,
            "message": f"Invalid role. Must be one of: {', '.join(ALLOWED_ROLES)}"
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            if email:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Email already exists"
                    }), 409

            if phone_number:
                cursor.execute(
                    "SELECT id FROM users WHERE phone_number = %s",
                    (phone_number,)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Phone number already exists"
                    }), 409

            if student_number:
                cursor.execute(
                    "SELECT id FROM users WHERE student_number = %s",
                    (student_number,)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Student number already exists"
                    }), 409

            cursor.execute(
                """
                INSERT INTO users (
                    student_number, full_name, university, email, phone_number,
                    role, password_hash, is_active, is_verified, failed_attempts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_number,
                    full_name,
                    university,
                    email,
                    phone_number,
                    role,
                    generate_password_hash(password),
                    int(bool(is_active)),
                    int(bool(is_verified)),
                    0
                )
            )
            new_user_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user_id": new_user_id
        }), 201

    finally:
        connection.close()
 
@app.route("/api/admin/users/<int:user_id>", methods=["PATCH"])
@admin_required
def admin_update_user(user_id):

    data = request.get_json(silent=True) or {}
    allowed_fields = (
        "student_number",
        "full_name",
        "university",
        "email",
        "phone_number",
        "role",
        "is_active",
        "is_verified",
    )

    if "role" in data and data["role"] not in ALLOWED_ROLES:
        return jsonify({
            "success": False,
            "message": f"Invalid role. Must be one of: {', '.join(ALLOWED_ROLES)}"
        }), 400

    updates = []
    params = []

    for field in allowed_fields:
        if field in data:
            updates.append(f"`{field}` = %s")
            if field in ("is_active", "is_verified"):
                params.append(int(bool(data[field])))
            else:
                params.append(data[field])

    if not updates:
        return jsonify({
            "success": False,
            "message": "No valid fields provided"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            if data.get("email"):
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (data["email"], user_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Email already exists"
                    }), 409

            if data.get("phone_number"):
                cursor.execute(
                    "SELECT id FROM users WHERE phone_number = %s AND id != %s",
                    (data["phone_number"], user_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Phone number already exists"
                    }), 409

            if data.get("student_number"):
                cursor.execute(
                    "SELECT id FROM users WHERE student_number = %s AND id != %s",
                    (data["student_number"], user_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Student number already exists"
                    }), 409

            params.append(user_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
                params
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User updated successfully"
        })

    finally:
        connection.close()
 
@app.route("/api/admin/users/<int:user_id>/status", methods=["PATCH"])
@admin_required
def admin_update_user_status(user_id):

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")

    if is_active is None:
        return jsonify({
            "success": False,
            "message": "is_active is required"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (int(bool(is_active)), user_id)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User status updated successfully"
        })

    finally:
        connection.close()
 
@app.route("/api/admin/users/<int:user_id>/reset-password", methods=["PATCH"])
@admin_required
def admin_reset_user_password(user_id):

    data = request.get_json(silent=True) or {}
    new_password = data.get("password")

    if not new_password:
        return jsonify({
            "success": False,
            "message": "password is required"
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s, failed_attempts = 0
                WHERE id = %s
                """,
                (generate_password_hash(new_password), user_id)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Password reset successfully"
        })

    finally:
        connection.close()
 
 
 
@app.route("/api/admin/universities/<int:university_id>", methods=["GET"])
@admin_required
def admin_get_university(university_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, code, city, is_active, created_at, updated_at
                FROM universities
                WHERE id = %s
                """,
                (university_id,)
            )
            university = cursor.fetchone()

        if not university:
            return jsonify({
                "success": False,
                "message": "University not found"
            }), 404

        return jsonify({
            "success": True,
            "data": serialize_university(university)
        })

    finally:
        connection.close()
 
@app.route("/api/admin/universities", methods=["POST"])
@admin_required
def admin_create_university():

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    code = data.get("code")
    city = data.get("city")
    is_active = data.get("is_active", 1)

    if not name:
        return jsonify({
            "success": False,
            "message": "name is required"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM universities WHERE name = %s", (name,))
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "University name already exists"
                }), 409

            if code:
                cursor.execute(
                    "SELECT id FROM universities WHERE code = %s",
                    (code,)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "University code already exists"
                    }), 409

            cursor.execute(
                """
                INSERT INTO universities (name, code, city, is_active)
                VALUES (%s, %s, %s, %s)
                """,
                (name, code, city, int(bool(is_active)))
            )
            university_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "University created successfully",
            "university_id": university_id
        }), 201

    finally:
        connection.close()
 
@app.route("/api/admin/universities/<int:university_id>", methods=["PATCH"])
@admin_required
def admin_update_university(university_id):

    data = request.get_json(silent=True) or {}
    allowed_fields = ("name", "code", "city", "is_active")
    updates = []
    params = []

    for field in allowed_fields:
        if field in data:
            updates.append(f"`{field}` = %s")
            if field == "is_active":
                params.append(int(bool(data[field])))
            else:
                params.append(data[field])

    if not updates:
        return jsonify({
            "success": False,
            "message": "No valid fields provided"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM universities WHERE id = %s",
                (university_id,)
            )
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "University not found"
                }), 404

            if data.get("name"):
                cursor.execute(
                    "SELECT id FROM universities WHERE name = %s AND id != %s",
                    (data["name"], university_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "University name already exists"
                    }), 409

            if data.get("code"):
                cursor.execute(
                    "SELECT id FROM universities WHERE code = %s AND id != %s",
                    (data["code"], university_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "University code already exists"
                    }), 409

            params.append(university_id)
            cursor.execute(
                f"UPDATE universities SET {', '.join(updates)} WHERE id = %s",
                params
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "University updated successfully"
        })

    finally:
        connection.close()
 
@app.route("/api/admin/universities/<int:university_id>", methods=["DELETE"])
@admin_required
def admin_delete_university(university_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM universities WHERE id = %s",
                (university_id,)
            )
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "University not found"
                }), 404

            cursor.execute(
                "DELETE FROM universities WHERE id = %s",
                (university_id,)
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "University deleted successfully"
        })

    finally:
        connection.close()
 
 
 
 

if __name__ == "__main__":
    app.run(debug=True)

application = app