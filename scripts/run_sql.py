#!/usr/bin/env python3
"""Run SQL files against the local Supabase Postgres database.

Usage:
    cd /Users/snjain/github/ai-local
    python scripts/run_sql.py

Or via rav:
    rav run db-setup
"""

import os
import sys
from pathlib import Path

# Try psycopg2 first, fall back to psycopg (psycopg3)
try:
    import psycopg2
    DB_DRIVER = "psycopg2"
except ImportError:
    try:
        import psycopg
        DB_DRIVER = "psycopg"
    except ImportError:
        print("Error: Neither psycopg2 nor psycopg is installed.")
        print("Install with: uv pip install psycopg2-binary")
        sys.exit(1)


def get_connection():
    """Create database connection from environment variables."""
    # Try DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if DB_DRIVER == "psycopg2":
            return psycopg2.connect(database_url)
        else:
            return psycopg.connect(database_url)

    # Fall back to individual parameters
    host = os.getenv("POSTGRES_HOST", "localhost")
    database = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    port = int(os.getenv("POSTGRES_PORT", "5434"))

    if not password:
        print("Error: Database connection not configured.")
        print("")
        print("Set one of these in your environment:")
        print("  1. DATABASE_URL=postgresql://postgres:password@localhost:5434/postgres")
        print("  2. POSTGRES_HOST, POSTGRES_PASSWORD, etc.")
        print("")
        print("Or set them in your .env file and run:")
        print("  source .venv/bin/activate")
        print("  export $(grep -v '^#' .env | xargs)")
        sys.exit(1)

    if DB_DRIVER == "psycopg2":
        return psycopg2.connect(
            host=host, database=database, user=user,
            password=password, port=port
        )
    else:
        return psycopg.connect(
            host=host, dbname=database, user=user,
            password=password, port=port
        )


def run_sql_file(cursor, filepath: Path) -> None:
    """Execute a single SQL file."""
    sql = filepath.read_text()
    cursor.execute(sql)


def main():
    project_root = Path(__file__).resolve().parent.parent
    sql_dir = project_root / "sql"

    sql_files = [
        "documents.sql",
        "document_metadata.sql",
        "document_rows.sql",
        "execute_sql_rpc.sql",
        "conversations_messages.sql",
    ]

    print("═══════════════════════════════════════════════════════════════")
    print("  Local AI Packaged — Database Setup")
    print("═══════════════════════════════════════════════════════════════")
    print()

    # Load .env if present
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)
        print()

    conn = None
    try:
        print("Connecting to database...")
        conn = get_connection()

        if DB_DRIVER == "psycopg2":
            cursor = conn.cursor()
        else:
            cursor = conn.cursor()

        for filename in sql_files:
            filepath = sql_dir / filename
            if not filepath.exists():
                print(f"  ⚠️  Skipping {filename} (not found)")
                continue

            print(f"Running {filename}...")
            run_sql_file(cursor, filepath)
            conn.commit()
            print(f"  ✅ {filename}")

        cursor.close()
        print()
        print("🎉 All SQL files executed successfully!")

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
