#!/usr/bin/env python3
"""
Security credentials initialization script for Blacklist Management System
"""
import os
import json
import secrets
import hashlib
from pathlib import Path
from datetime import datetime


def generate_secure_key(length=32):
    """Generate a secure random key"""
    return secrets.token_urlsafe(length)


def init_security():
    """Initialize security configuration"""
    # Create security directory
    security_dir = Path.home() / ".blacklist"
    security_dir.mkdir(exist_ok=True)

    # Generate security configuration
    config = {
        "created_at": datetime.now().isoformat(),
        "secret_key": generate_secure_key(32),
        "jwt_secret_key": generate_secure_key(32),
        "api_key": f"blk_{generate_secure_key(24)}",
        "admin_password": generate_secure_key(16),
        "encryption_key": generate_secure_key(32),
        "database_key": generate_secure_key(24),
    }

    # Save encrypted credentials
    cred_file = security_dir / "credentials.json"
    with open(cred_file, "w") as f:
        json.dump(config, f, indent=2)

    # Set restrictive permissions
    os.chmod(cred_file, 0o600)

    # Create .env file if not exists
    env_file = Path(".env")
    if not env_file.exists():
        env_content = f"""# Blacklist Security Configuration
# Generated: {datetime.now().isoformat()}

# Security Keys
SECRET_KEY={config['secret_key']}
JWT_SECRET_KEY={config['jwt_secret_key']}
DEFAULT_API_KEY={config['api_key']}

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD={config['admin_password']}

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/blacklist
REDIS_URL=redis://localhost:6379/0

# Collection Settings
FORCE_DISABLE_COLLECTION=false
COLLECTION_ENABLED=true

# Security Settings
API_KEY_ENABLED=true
JWT_ENABLED=true
MAX_AUTH_ATTEMPTS=5
BLOCK_DURATION_HOURS=1
"""
        with open(env_file, "w") as f:
            f.write(env_content)
        os.chmod(env_file, 0o600)
        print(f"✅ Created .env file with security configuration")

    print(f"✅ Security credentials initialized at {cred_file}")
    print(f"📋 Admin password: {config['admin_password']}")
    print(f"🔑 API Key: {config['api_key']}")
    print("⚠️  Please save these credentials securely!")

    return config


if __name__ == "__main__":
    init_security()
