from functools import wraps
from datetime import datetime, timedelta
import jwt

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import get_connection


app = Flask(__name__)

# CHANGE THIS IN PRODUCTION
app.config["SECRET_KEY"] = "super-secret-key"


CORS(app)


def generate_token(user):

    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }

    token = jwt.encode(
        payload,
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return token


def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "success": False,
                "message": "Token missing"
            }), 401

        try:

            token = auth_header.split(" ")[1]

        except Exception:
            return jsonify({
                "success": False,
                "message": "Invalid authorization header"
            }), 401

        try:

            decoded = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )

            request.user = decoded

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


@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "JWT API running"
    })


# ── Auth: Register ──────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")

    if not full_name or not email or not password:

        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                return jsonify({
                    "success": False,
                    "message": "Email already exists"
                }), 409

            hashed_password = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active,
                    is_verified,
                    failed_attempts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    full_name,
                    email,
                    hashed_password,
                    "borrower",
                    1,
                    1,
                    0
                )
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User registered successfully"
        }), 201

    finally:
        connection.close()


# ── Auth: Login ─────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password required"
        }), 400

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )

            user = cursor.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "Invalid credentials"
            }), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid credentials"
            }), 401

        if not user["is_active"]:

            return jsonify({
                "success": False,
                "message": "Account disabled"
            }), 403

        token = generate_token(user)

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role"]
            }
        })

    finally:
        connection.close()


# ── Auth: Me / Protected ────────────────────────────────────────────

@app.route("/api/me", methods=["GET"])
@token_required
def me():

    return jsonify({
        "success": True,
        "user": request.user
    })


@app.route("/api/protected", methods=["GET"])
@token_required
def protected():

    return jsonify({
        "success": True,
        "message": "Protected route access granted",
        "user": request.user
    })


# ── Users: List all ─────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@token_required
def list_users():

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    role = request.args.get("role")
    search = request.args.get("search")

    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            where_clauses = []
            params = []

            if role:
                where_clauses.append("role = %s")
                params.append(role)

            if search:
                where_clauses.append(
                    "(full_name LIKE %s OR email LIKE %s OR student_number LIKE %s)"
                )
                like_term = f"%{search}%"
                params.extend([like_term, like_term, like_term])

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            cursor.execute(
                f"SELECT COUNT(*) AS total FROM users {where_sql}",
                params
            )
            total = cursor.fetchone()["total"]

            cursor.execute(
                f"""
                SELECT id, student_number, full_name, university,
                       email, phone_number, role, is_active, is_verified,
                       last_login_at, created_at, updated_at
                FROM users
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [per_page, offset]
            )

            users = cursor.fetchall()

        for u in users:
            for key in ("last_login_at", "created_at", "updated_at"):
                if u.get(key) and isinstance(u[key], datetime):
                    u[key] = u[key].isoformat()

        return jsonify({
            "success": True,
            "data": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })

    finally:
        connection.close()


# ── Users: Get by ID ────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>", methods=["GET"])
@token_required
def get_user(user_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id, student_number, full_name, university,
                       email, phone_number, role, is_active, is_verified,
                       last_login_at, created_at, updated_at
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

        for key in ("last_login_at", "created_at", "updated_at"):
            if user.get(key) and isinstance(user[key], datetime):
                user[key] = user[key].isoformat()

        return jsonify({
            "success": True,
            "data": user
        })

    finally:
        connection.close()


# ── Users: Create (admin) ──────────────────────────────────────────

@app.route("/api/users", methods=["POST"])
@token_required
def create_user():

    data = request.get_json()

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "borrower")
    student_number = data.get("student_number")
    university = data.get("university")
    phone_number = data.get("phone_number")

    if not full_name or not email or not password:
        return jsonify({
            "success": False,
            "message": "full_name, email, and password are required"
        }), 400

    valid_roles = ("borrower", "lender", "rep", "admin", "agent")
    if role not in valid_roles:
        return jsonify({
            "success": False,
            "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "Email already exists"
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

            hashed_password = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (
                    student_number, full_name, university, email,
                    phone_number, role, password_hash,
                    is_active, is_verified, failed_attempts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_number, full_name, university, email,
                    phone_number, role, hashed_password,
                    1, 0, 0
                )
            )

            new_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "data": {"id": new_id}
        }), 201

    finally:
        connection.close()


# ── Users: Update ───────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>", methods=["PUT"])
@token_required
def update_user(user_id):

    data = request.get_json()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            updatable = {
                "full_name": data.get("full_name"),
                "email": data.get("email"),
                "student_number": data.get("student_number"),
                "university": data.get("university"),
                "phone_number": data.get("phone_number"),
                "role": data.get("role"),
                "is_active": data.get("is_active"),
                "is_verified": data.get("is_verified"),
            }

            set_clauses = []
            params = []

            for field, value in updatable.items():
                if value is not None:
                    set_clauses.append(f"`{field}` = %s")
                    params.append(value)

            if data.get("password"):
                set_clauses.append("`password_hash` = %s")
                params.append(generate_password_hash(data["password"]))

            if not set_clauses:
                return jsonify({
                    "success": False,
                    "message": "No fields to update"
                }), 400

            if data.get("email"):
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (data["email"], user_id)
                )
                if cursor.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "Email already in use"
                    }), 409

            params.append(user_id)

            cursor.execute(
                f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s",
                params
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User updated successfully"
        })

    finally:
        connection.close()


# ── Users: Delete ───────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@token_required
def delete_user(user_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404

            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User deleted successfully"
        })

    finally:
        connection.close()


# ── Loans: Create ───────────────────────────────────────────────────

@app.route("/api/loans", methods=["POST"])
@token_required
def create_loan():

    data = request.get_json()

    lender_id = request.user.get("user_id")
    borrower_id = data.get("borrower_id")
    amount_zmw = data.get("amount_zmw")
    due_date = data.get("due_date")
    note = data.get("note")

    if not borrower_id or not amount_zmw or not due_date:
        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO loans (
                    id,
                    reference_code,
                    lender_id,
                    borrower_id,
                    amount_zmw,
                    due_date,
                    status,
                    note
                )
                VALUES (
                    UUID(),
                    CONCAT('LN-', FLOOR(RAND() * 1000000)),
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    lender_id,
                    borrower_id,
                    amount_zmw,
                    due_date,
                    "pending",
                    note
                )
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Loan created successfully"
        }), 201

    finally:
        connection.close()


# ── Loans: My loans ─────────────────────────────────────────────────

@app.route("/api/loans/my", methods=["GET"])
@token_required
def get_my_loans():

    user_id = request.user.get("user_id")

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM loans
                WHERE lender_id = %s
                   OR borrower_id = %s
                ORDER BY logged_at DESC
                """,
                (user_id, user_id)
            )

            loans = cursor.fetchall()

        for loan in loans:
            for key in ("due_date", "logged_at", "repaid_at", "created_at", "updated_at"):
                if loan.get(key) and hasattr(loan[key], "isoformat"):
                    loan[key] = loan[key].isoformat()

        return jsonify({
            "success": True,
            "data": loans
        })

    finally:
        connection.close()


# ── Loans: Get by ID ────────────────────────────────────────────────

@app.route("/api/loans/<loan_id>", methods=["GET"])
@token_required
def get_loan(loan_id):

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM loans WHERE id = %s",
                (loan_id,)
            )

            loan = cursor.fetchone()

        if not loan:
            return jsonify({
                "success": False,
                "message": "Loan not found"
            }), 404

        for key in ("due_date", "logged_at", "repaid_at", "created_at", "updated_at"):
            if loan.get(key) and hasattr(loan[key], "isoformat"):
                loan[key] = loan[key].isoformat()

        return jsonify({
            "success": True,
            "data": loan
        })

    finally:
        connection.close()


if __name__ == "__main__":
    app.run(debug=True)

application = app
