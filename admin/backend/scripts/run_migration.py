#!/usr/bin/env python3
"""
Run database migration scripts
Usage: python run_migration.py <migration_file>
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Database connection details
DB_HOST = "postgres-01.xmojo.net"
DB_PORT = 5432
DB_NAME = "athena_admin"
DB_USER = "psadmin"
DB_PASSWORD = "Ibucej1!"  # From Kubernetes secret athena-admin-db


async def run_migration(migration_file: str):
    """Run a SQL migration file"""

    # Read migration file
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    print(f"📄 Reading migration: {migration_path.name}")
    sql_content = migration_path.read_text()

    # Connect to database
    print(f"🔌 Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    print("✅ Connected successfully")

    # Execute migration
    try:
        print(f"⚙️  Running migration...")
        await conn.execute(sql_content)
        print("✅ Migration completed successfully")

        # Verify tables created
        print("\n📊 Verifying tables:")
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE '%conversation%'
            OR tablename LIKE '%clarification%'
            ORDER BY tablename;
        """)

        for table in tables:
            print(f"  ✓ {table['tablename']}")

        # Verify default data
        print("\n📈 Verifying default data:")

        conv_settings = await conn.fetchrow("SELECT * FROM conversation_settings LIMIT 1")
        if conv_settings:
            print(f"  ✓ Conversation settings: max_messages={conv_settings['max_messages']}, timeout={conv_settings['timeout_seconds']}s")

        clar_types = await conn.fetch("SELECT type, enabled FROM clarification_types ORDER BY priority")
        print(f"  ✓ Clarification types ({len(clar_types)}):")
        for ct in clar_types:
            status = "✓" if ct['enabled'] else "✗"
            print(f"    {status} {ct['type']}")

        sports_teams = await conn.fetch("SELECT team_name FROM sports_team_disambiguation")
        print(f"  ✓ Sports teams ({len(sports_teams)}): {', '.join([st['team_name'] for st in sports_teams])}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await conn.close()
        print("\n🔌 Database connection closed")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <migration_file>")
        sys.exit(1)

    migration_file = sys.argv[1]
    asyncio.run(run_migration(migration_file))


if __name__ == "__main__":
    main()
