#!/usr/bin/env python3
"""
Add secrets directly to the admin database.
"""
import os
import sys
import psycopg2
from cryptography.fernet import Fernet
from datetime import datetime

# Get encryption key from environment or database
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    print("Error: ENCRYPTION_KEY environment variable not set")
    sys.exit(1)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://athena_admin:secure_password@localhost:5432/athena_admin")

# Secrets to add
SECRETS = {
    "home-assistant": {
        "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4NjNhNWIwMDM3OTE0ODE1YTVlODkyZWUwNTMxMmIwZCIsImlhdCI6MTc2MjE4MzY0MiwiZXhwIjoyMDc3NTQzNjQyfQ.M-vSeDlQl3NvGrpeZ35QKat8OjTXXA2z3559Hy96EC4A",
        "description": "Home Assistant long-lived access token"
    },
    "openweathermap-api-key": {
        "value": "779f35a5c12b85e9841f835db8694408",
        "description": "OpenWeatherMap API key for weather data"
    }
}

def encrypt_value(plaintext: str) -> str:
    """Encrypt a value using Fernet."""
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(plaintext.encode()).decode()

def add_secrets():
    """Add secrets to the database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Get the first user ID (assuming there's at least one user)
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("Error: No users found in database")
            return False

        created_by_id = result[0]

        for service_name, secret_data in SECRETS.items():
            # Check if secret already exists
            cursor.execute(
                "SELECT id FROM secrets WHERE service_name = %s",
                (service_name,)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"✓ Secret '{service_name}' already exists (ID: {existing[0]})")
                continue

            # Encrypt the value
            encrypted_value = encrypt_value(secret_data["value"])

            # Insert the secret
            cursor.execute(
                """
                INSERT INTO secrets (service_name, encrypted_value, description, created_by_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    service_name,
                    encrypted_value,
                    secret_data["description"],
                    created_by_id,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            )

            secret_id = cursor.fetchone()[0]
            conn.commit()

            print(f"✓ Added secret '{service_name}' (ID: {secret_id})")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Error adding secrets: {e}")
        return False

if __name__ == "__main__":
    print("Adding secrets to admin database...")
    if add_secrets():
        print("\n✓ All secrets added successfully")
    else:
        print("\n✗ Failed to add secrets")
        sys.exit(1)
