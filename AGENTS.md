# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

HelsB Credit is a Flask REST API for a student peer-loan network. The backend lives entirely in `backend/`.

### Services

| Service | How to start | Port |
|---|---|---|
| MariaDB | `sudo service mariadb start` | 3306 |
| Flask API | `cd backend && source venv/bin/activate && flask run` | 5000 |

### Key gotchas

- **MariaDB root auth**: After a fresh MariaDB install the root user uses `unix_socket` auth, which blocks PyMySQL connections. Fix with:
  ```
  sudo mariadb -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('');"
  sudo mariadb -u root -e "FLUSH PRIVILEGES;"
  ```
- The database name is `citafina_nexcredit_server` (not `helsb_credit` as the README says).
- The `.env` file in `backend/` must exist for `db.py` to connect. Copy from `.env.example` if missing.

### Common commands

```bash
# Lint
cd backend && source venv/bin/activate && flake8 app.py db.py --max-line-length=100

# Tests
cd backend && source venv/bin/activate && python -m pytest tests/ -v

# Dev server
cd backend && source venv/bin/activate && flask run --host=0.0.0.0 --port=5000

# Import schema (first time)
sudo mariadb -u root -e "CREATE DATABASE IF NOT EXISTS citafina_nexcredit_server CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mariadb -u root citafina_nexcredit_server < backend/schema.sql
```
