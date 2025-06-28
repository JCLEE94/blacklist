# REGTECH Authentication Issue

## Current Status (2025-06-27)

REGTECH data collection is failing due to authentication issues:
- Login fails with `error=true` when using credentials
- Bearer token in code has expired
- Last successful collection: 2025-06-25 (1000 IPs in database)

## Root Cause

1. **Expired Bearer Token**: The hardcoded JWT token expired
2. **Login Failure**: Username/password login returns `error=true`
   - Possible reasons: Account locked, password changed, or additional verification required

## Solution

### Option 1: Manual Bearer Token Update (Recommended)

1. **Get New Bearer Token**:
   ```bash
   # In browser:
   1. Visit https://regtech.fsec.or.kr
   2. Login with nextrade / Sprtmxm1@3
   3. Open DevTools (F12) → Application → Cookies
   4. Copy 'regtech-va' cookie value (starts with "Bearer")
   ```

2. **Set Environment Variable**:
   ```bash
   export REGTECH_BEARER_TOKEN="BearereyJ0eXA..."
   ```

3. **Deploy with Token**:
   ```bash
   # Local testing
   REGTECH_BEARER_TOKEN="BearereyJ0eXA..." python3 main.py
   
   # Docker deployment
   REGTECH_BEARER_TOKEN="BearereyJ0eXA..." docker-compose up -d
   
   # Or add to .env file
   echo 'REGTECH_BEARER_TOKEN=BearereyJ0eXA...' >> .env
   ```

### Option 2: Fix Login Issues

1. **Check Account Status**:
   - Try manual login in browser
   - Account may be locked (5 failed attempts = 10 min lock)
   - Password may have changed
   - OTP/additional verification may be required

2. **Update Credentials**:
   ```bash
   # Update docker-compose.yml
   REGTECH_USERNAME=new_username
   REGTECH_PASSWORD=new_password
   ```

## Code Changes Made

1. **Updated `src/core/regtech_collector.py`**:
   - Now checks `REGTECH_BEARER_TOKEN` environment variable
   - Falls back to hardcoded token if not set
   - Better error handling for authentication failures

2. **Updated `deployment/docker-compose.yml`**:
   - Added `REGTECH_BEARER_TOKEN` environment variable support

## Temporary Workaround

Since 1000 REGTECH IPs are already in the database from 2 days ago:
- The system continues to serve these IPs
- Other sources (SECUDIUM) are working normally
- No immediate impact on FortiGate integration

## Long-term Solution

Consider implementing:
1. Automated Bearer token refresh mechanism
2. Alternative authentication methods
3. Monitoring/alerting for collection failures
4. Fallback to cached data when collection fails

## Testing

```bash
# Test with new Bearer token
export REGTECH_BEARER_TOKEN="Bearer..."
python3 test_regtech_correct_method.py

# Check collection status
curl http://localhost:8541/api/collection/status

# Trigger manual collection
curl -X POST http://localhost:8541/api/collection/regtech/trigger
```