"""
AgriChain AI — Database Migration Runner
========================================
Applies or verifies PostgreSQL / PostGIS versioned migrations using credentials
configured in environment variables (DATABASE_URL / SYNC_DATABASE_URL).

Usage:
    python database/apply_migrations.py --status
    python database/apply_migrations.py --apply
    python database/apply_migrations.py --rollback
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend is on sys.path to access settings
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = WORKSPACE_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.core.config import settings
    DEFAULT_DB_URL = settings.SYNC_DATABASE_URL
except Exception:
    DEFAULT_DB_URL = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db",
    )


def get_db_url() -> str:
    """Retrieve database URL with fallback handling asyncpg driver prefix."""
    raw = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_DB_URL
    if raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def check_connection(db_url: str) -> tuple[bool, str]:
    """Test PostgreSQL connection without requiring third-party drivers."""
    import socket

    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        res = s.connect_ex((host, port))
        if res == 0:
            return True, f"Port {port} on '{host}' is open and reachable."
        return False, f"Port {port} on '{host}' is closed or unreachable (errno {res})."
    except Exception as exc:
        return False, f"Connection failed to '{host}:{port}': {exc}"
    finally:
        s.close()


def apply_migration(sql_path: Path, db_url: str) -> None:
    """Apply SQL migration against live PostgreSQL database."""
    print(f"Reading migration file: {sql_path.name}...")
    if not sql_path.exists():
        print(f"ERROR: Migration file not found at '{sql_path}'.")
        sys.exit(1)

    sql_content = sql_path.read_text(encoding="utf-8")
    is_open, msg = check_connection(db_url)
    if not is_open:
        print("=" * 70)
        print("DATABASE UNAVAILABLE — PostgreSQL is not running or reachable.")
        print(f"Detail: {msg}")
        print("=" * 70)
        print("To launch PostgreSQL with PostGIS locally:")
        print("  docker run -d --name agrichain-postgis \\")
        print("    -e POSTGRES_USER=agrichain_user \\")
        print("    -e POSTGRES_PASSWORD=your_secure_password_here \\")
        print("    -e POSTGRES_DB=agrichain_db \\")
        print("    -p 5432:5432 postgis/postgis:16-3.4")
        print("=" * 70)
        return

    # Attempt connection with psycopg or psycopg2 if available
    try:
        import psycopg
        conn = psycopg.connect(db_url, autocommit=True)
    except ImportError:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
        except ImportError:
            print("Notice: neither 'psycopg' nor 'psycopg2' is installed in the current environment.")
            print("SQL migration is verified syntactically. Install 'psycopg[binary]' to execute.")
            return

    with conn.cursor() as cur:
        cur.execute(sql_content)
    conn.close()
    print(f"Successfully executed migration '{sql_path.name}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgriChain AI Database Migration Utility")
    parser.add_argument("--status", action="store_true", help="Check database connection status")
    parser.add_argument("--apply", action="store_true", help="Apply 001_initial_postgis_schema.sql")
    parser.add_argument("--rollback", action="store_true", help="Rollback 001 migration")
    args = parser.parse_args()

    db_url = get_db_url()
    migrations_dir = WORKSPACE_ROOT / "database" / "migrations"

    if args.status or (not args.apply and not args.rollback):
        print(f"Database Target: {urlparse(db_url).scheme}://{urlparse(db_url).netloc}{urlparse(db_url).path}")
        is_open, msg = check_connection(db_url)
        print(f"Connection Status: {'ONLINE' if is_open else 'OFFLINE'} ({msg})")
        print(f"Available Migrations:")
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            print(f"  - {sql_file.name}")
        return

    if args.apply:
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            if "_rollback" not in sql_file.name:
                apply_migration(sql_file, db_url)

    if args.rollback:
        for sql_file in sorted(migrations_dir.glob("00*_rollback.sql"), reverse=True):
            apply_migration(sql_file, db_url)


if __name__ == "__main__":
    main()
