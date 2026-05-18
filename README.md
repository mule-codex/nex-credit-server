 HelsB Credit

> **Digitising a student-run peer loan network in Zambia.**  
> Replace the WhatsApp group and the paper receipt book with a shared, trusted ledger.

---

## The problem

Students on HELSB bursaries and stipends lend to each other informally. Today that means WhatsApp messages and handwritten receipts that get lost. Nobody in the network knows how many loans someone already has. A student can borrow from five different people in the same week and nobody finds out until they default.

**HelsB Credit solves one thing:** before any money moves, the lender can check — *is this person on BC, and how many open loans do they already have?*

---

## What it does

| Feature | Description |
|---|---|
| **BC validation** | Instant check — is a student a registered HELSB bursary/stipend recipient? |
| **Loan count check** | See how many open loans a student has and total amount owed — before lending |
| **Loan ledger** | Log loans digitally instead of paper receipts. Both parties get notified. |
| **Debt dashboard** | Borrowers see everything they owe in one place |
| **Overdue tracking** | Loans auto-flag as overdue when the due date passes |
| **Rep dashboard** | The student admin gets a full view of the entire network's loan activity |

---

## What it is NOT (MVP scope)

- ❌ Not a credit scoring system
- ❌ Not a goods marketplace
- ❌ Not a mobile money integration
- ❌ Not a HELSB API consumer — BC register is maintained manually by the student rep

These are explicitly deferred. See [SRS v2.0](./docs/HelsB_Credit_SRS_v2.0.docx) for the full rationale.

---

## Tech stack

| Layer | Technology |
|---|---|
| **Frontend** | Expo (React Native) — iOS, Android, and web from one codebase |
| **Backend** | Python + Flask |
| **Database** | MariaDB |
| **Auth** | Flask-JWT-Extended |
| **Notifications** | In-app + Zamtel SMS (Zambia) |

---

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Expo CLI (`npm install -g expo-cli`)
- MariaDB 10.6+

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/your-org/helsb-credit.git
cd helsb-credit
```

---

### 2. Backend (Flask)

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env — see Environment variables section below

# Create the database
mysql -u root -p -e "CREATE DATABASE helsb_credit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations
flask db upgrade

# Seed demo data (20 fictitious students + 10 sample loans)
flask seed run

# Start the development server
flask run
```

API will be available at `http://localhost:5000`.

---

### 3. Frontend (Expo)

```bash
cd frontend

# Install dependencies
npm install

# Start the Expo development server
npx expo start
```

Then:
- Press `a` to open on Android emulator
- Press `i` to open on iOS simulator
- Scan the QR code with the Expo Go app on your physical device

---

## Environment variables

Create a `.env` file inside `backend/`:

```env
# Flask
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=helsb_credit
DB_USER=root
DB_PASSWORD=your-db-password

# JWT
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ACCESS_TOKEN_EXPIRES=86400      # 24 hours in seconds

# Login OTP SMS
LOGIN_OTP_EXPIRES_SECONDS=300
ZAMTEL_API_KEY=your-zamtel-api-key
ZAMTEL_SENDER_ID=your-zamtel-sender-id
ZAMTEL_BASE_URL=https://bulksms.zamtel.co.zm/api/v2.1/action/send/
```

---

## Project structure

```
helsb-credit/
│
├── backend/                        # Python + Flask API
│   ├── app.py                      # App factory and entry point
│   ├── config.py                   # Environment config
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── routes/
│   │   ├── auth.py                 # POST /api/register, /api/login
│   │   ├── students.py             # GET /students/<number>/check  ← core feature
│   │   ├── loans.py                # POST /loans, PATCH /loans/<id>/repaid
│   │   ├── bc_register.py          # BC register management (rep only)
│   │   └── dashboard.py            # GET /dashboard/rep
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── loan.py
│   │   ├── bc_register.py
│   │   └── audit_log.py
│   │
│   ├── middleware/
│   │   ├── auth.py                 # JWT verification decorator
│   │   └── roles.py                # Role-based access control
│   │
│   └── migrations/                 # Flask-Migrate / Alembic
│
├── frontend/                       # Expo (React Native)
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login.tsx
│   │   │   └── register.tsx
│   │   ├── (borrower)/
│   │   │   └── dashboard.tsx       # Debt dashboard
│   │   ├── (lender)/
│   │   │   ├── check.tsx           # Pre-loan check — the core screen
│   │   │   ├── log-loan.tsx
│   │   │   └── dashboard.tsx
│   │   └── (rep)/
│   │       ├── dashboard.tsx
│   │       └── bc-register.tsx
│   │
│   ├── components/
│   │   ├── BCStatusBadge.tsx       # Active BC / Inactive / Not found
│   │   ├── LoanCard.tsx
│   │   └── PreLoanSummary.tsx
│   │
│   ├── services/
│   │   └── api.ts                  # Axios client pointing to Flask backend
│   │
│   ├── app.json
│   └── package.json
│
└── docs/
    └── HelsB_Credit_SRS_v2.0.docx
```

---

## Core API endpoints

```
POST   /api/register                       Create user account
POST   /api/login                          Send OTP to phone number
POST   /api/login/otp                      Validate OTP → JWT + user

GET    /students/<student_number>/check    Pre-loan check (BC status + loan count)
GET    /students/<id>/profile              Student profile

POST   /loans                              Log a new loan (lender or rep)
PATCH  /loans/<id>/repaid                  Mark loan as repaid
GET    /loans?status=open                  List loans with filters

POST   /bc-register                        Add student to BC register (rep only)
PATCH  /bc-register/<id>                   Update BC record (rep only)
GET    /dashboard/rep                      Rep summary
```

The `/students/<student_number>/check` endpoint is the most critical in the system. It returns:

```json
{
  "student_number": "14025831",
  "bc_status": "active",
  "bc_type": "stipend",
  "open_loans_count": 3,
  "total_owed_zmw": 900,
  "has_overdue": true,
  "overdue_days": 12
}
```

---

## Database schema (MariaDB)

```sql
-- Source of truth for who is on BC
CREATE TABLE bc_register (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  student_number  VARCHAR(20) NOT NULL UNIQUE,
  full_name       VARCHAR(120) NOT NULL,
  university      VARCHAR(100) NOT NULL,
  bc_type         ENUM('bursary', 'stipend', 'both') NOT NULL,
  academic_year   VARCHAR(10) NOT NULL,
  is_active       BOOLEAN DEFAULT TRUE,
  added_by        INT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Everyone with an account
CREATE TABLE users (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  student_number  VARCHAR(20),
  full_name       VARCHAR(120) NOT NULL,
  university      VARCHAR(100),
  role            ENUM('borrower', 'lender', 'rep') NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_number) REFERENCES bc_register(student_number)
);

-- Every loan ever logged — never deleted, only status-changed
CREATE TABLE loans (
  id              CHAR(36) PRIMARY KEY,           -- UUID
  reference_code  VARCHAR(12) NOT NULL UNIQUE,    -- e.g. HC-2025-0042
  lender_id       INT NOT NULL,
  borrower_id     INT NOT NULL,
  amount_zmw      DECIMAL(10,2) NOT NULL,
  logged_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  due_date        DATE NOT NULL,
  status          ENUM('open','repaid','overdue','disputed') DEFAULT 'open',
  note            TEXT,
  FOREIGN KEY (lender_id)   REFERENCES users(id),
  FOREIGN KEY (borrower_id) REFERENCES users(id)
);

-- Full audit trail — every status change timestamped
CREATE TABLE audit_log (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  entity_type     VARCHAR(50),
  entity_id       VARCHAR(36),
  action          VARCHAR(100),
  changed_by      INT,
  changed_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  metadata        JSON
);
```

---

## User roles

| Role | Can do |
|---|---|
| **Borrower** | View own loans and debt dashboard, see own BC status |
| **Lender** | Run pre-loan check on any student, log loans, mark loans repaid |
| **Rep / Admin** | Everything above + manage BC register, view all loans, resolve disputes |

---

## Demo script (hackathon)

A 3-minute judge pitch:

1. **Show the problem** — open a WhatsApp screenshot of a student asking for a loan in a group. *"This is how it works today. No one knows how many loans this person already has."*

2. **Rep dashboard** — log in as the rep. *"The student who kept the notebook now has this."*

3. **Pre-loan check** — tap "Check before lending", enter student number `14025831`. Result: `Active BC · 3 open loans · K900 owed · 1 overdue`. *"For the first time, a lender can see this before any money moves."*

4. **Log a loan** — fill in amount and due date, confirm. *"Instead of a paper receipt, it goes here. Both parties get notified."*

5. **Borrower dashboard** — show Chanda's view: 4 loans, amounts, due dates. *"No more surprise defaults."*

6. **Rep overdue view** — show loans flagged red. *"The rep doesn't chase on WhatsApp anymore."*

---

## Hackathon context

Built at **Cursor Hackathon Zambia 2025** under the **Fintech + Education** theme.

The system being digitised already exists — students have been running this informally for years via WhatsApp and paper receipts. HelsB Credit is not a new behaviour. It is the same behaviour, made transparent and trustworthy.

---

## Roadmap (post-hackathon)

- [ ] SMS reminders via Zamtel (2 days before due date)
- [ ] Dispute resolution workflow
- [ ] CSV export for rep backup
- [ ] Multi-campus rollout
- [ ] HELSB API integration (requires government partnership)
- [ ] Credit scoring (requires 6+ months of repayment history data)
- [ ] Mobile money disbursement (requires BoZ licensing)

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/sms-reminders`)
3. Commit your changes
4. Open a pull request

---

## License

MIT — do whatever helps Zambian students.

---

*Built with purpose in Lusaka, Zambia.*
