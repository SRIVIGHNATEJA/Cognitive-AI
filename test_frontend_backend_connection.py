"""
Test frontend can connect to backend.
"""

import sys
sys.path.insert(0, 'frontend')

from services.api_client import api_client

print("Testing frontend → backend connection...")
print()

# Test 1: Health check
print("1. Testing health check...")
try:
    is_healthy = api_client.health_check()
    if is_healthy:
        print("   ✅ Backend is healthy")
    else:
        print("   ❌ Backend health check failed")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# Test 2: Get session
print("2. Testing session endpoint...")
try:
    session_data = api_client.get("/api/session")
    print(f"   ✅ Session ID: {session_data.get('session_id', 'N/A')[:20]}...")
    print(f"   ✅ Session created: {session_data.get('created_at', 'N/A')}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# Test 3: Get root endpoint
print("3. Testing root endpoint...")
try:
    root_data = api_client.get("/")
    print(f"   ✅ Message: {root_data.get('message')}")
    print(f"   ✅ Version: {root_data.get('version')}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✅ All connection tests passed!")
print("=" * 60)
print()
print("Frontend can successfully connect to backend.")
print("Streamlit app should now show '✅ Connected to backend'")
print()
