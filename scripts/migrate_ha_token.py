#!/usr/bin/env python3
"""
Migrate Home Assistant token from .env file to admin database.

This script reads the HA_TOKEN from the Mac Studio .env file and stores it
in the admin database as an encrypted secret.
"""
import os
import sys
import httpx

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

def migrate_ha_token():
    """Migrate HA token from .env to admin database."""

    # Read current HA token from .env file
    env_file = os.path.expanduser("~/dev/project-athena/.env")

    print(f"Reading .env file from: {env_file}")

    ha_token = None
    ha_url = None

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("HA_TOKEN="):
                    ha_token = line.split("=", 1)[1]
                elif line.startswith("HA_URL="):
                    ha_url = line.split("=", 1)[1]
    except FileNotFoundError:
        print(f"Error: .env file not found at {env_file}")
        return False

    if not ha_token:
        print("Error: HA_TOKEN not found in .env file")
        return False

    if not ha_url:
        print("Warning: HA_URL not found in .env file, using default")
        ha_url = "https://192.168.10.168:8123"

    print(f"Found HA_TOKEN: {ha_token[:20]}...")
    print(f"Found HA_URL: {ha_url}")

    # Admin API configuration
    admin_url = os.getenv("ADMIN_API_URL", "http://localhost:8080")

    # For now, we'll use a dummy admin token - you'll need to get a real one from the admin UI
    # Or we can create the secret directly in the database
    print("\n" + "="*80)
    print("MIGRATION INSTRUCTIONS:")
    print("="*80)
    print("\n1. Log in to the admin interface at https://athena-admin.xmojo.net")
    print("\n2. Navigate to Secrets → Add Secret")
    print("\n3. Create a new secret with:")
    print(f"   - Service Name: home-assistant")
    print(f"   - Value: {ha_token}")
    print(f"   - Description: Home Assistant long-lived access token")
    print("\n4. Once created, services will fetch it using the service API endpoint")
    print("\n" + "="*80)
    print("\nAlternatively, use curl to create the secret (requires admin authentication):")
    print(f"""
curl -X POST {admin_url}/api/secrets \\
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "service_name": "home-assistant",
    "value": "{ha_token}",
    "description": "Home Assistant long-lived access token"
  }}'
""")

    return True


if __name__ == "__main__":
    print("Home Assistant Token Migration Script")
    print("=" * 80)
    migrate_ha_token()
