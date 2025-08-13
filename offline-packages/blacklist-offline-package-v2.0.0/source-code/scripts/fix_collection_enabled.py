#!/usr/bin/env python3
"""
Fix collection_enabled to be False in database and config file
"""
import json
import os
import sqlite3
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fix_collection_enabled():
    """Set collection_enabled to false in database and config file"""
    db_path = "/app/instance/blacklist.db"
    config_path = "/app/instance/collection_config.json"

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current value
        cursor.execute("SELECT value FROM app_settings WHERE key='collection_enabled'")
        result = cursor.fetchone()

        if result:
            current_value = result[0]
            print(f"Current collection_enabled value: {current_value}")

            if current_value.lower() == "true":
                # Update to false
                cursor.execute(
                    """
                    UPDATE app_settings 
                    SET value = 'false', updated_at = CURRENT_TIMESTAMP
                    WHERE key = 'collection_enabled'
                """
                )
                conn.commit()
                print(
                    f"Updated collection_enabled to 'false' (affected rows: {cursor.rowcount})"
                )

                # Verify update
                cursor.execute(
                    "SELECT value FROM app_settings WHERE key='collection_enabled'"
                )
                new_value = cursor.fetchone()[0]
                print(f"New value: {new_value}")
            else:
                print("collection_enabled is already false")
        else:
            print("collection_enabled not found in app_settings table")
            # Insert it as false
            cursor.execute(
                """
                INSERT INTO app_settings (key, value, setting_type, category, encrypted, created_at, updated_at)
                VALUES ('collection_enabled', 'false', 'boolean', 'collection', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            )
            conn.commit()
            print("Inserted collection_enabled as 'false'")

        conn.close()

        # Also update the JSON config file
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)

                if config.get("collection_enabled", True):
                    config["collection_enabled"] = False

                    with open(config_path, "w") as f:
                        json.dump(config, f, indent=2)

                    print(f"Updated {config_path} to set collection_enabled to false")
                else:
                    print(f"{config_path} already has collection_enabled as false")

            except Exception as e:
                print(f"Error updating config file: {e}")
        else:
            print(f"Config file not found at {config_path}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = fix_collection_enabled()
    sys.exit(0 if success else 1)
