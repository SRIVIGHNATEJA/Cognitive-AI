"""
Quick test to verify backend imports work correctly.
"""

import sys

print("Testing backend imports...")
print()

try:
    print("✓ Importing app.config...")
    from app.config import settings
    print(f"  App Name: {settings.app_name}")
    print(f"  Version: {settings.app_version}")
    print(f"  Host: {settings.host}:{settings.port}")
    print()
    
    print("✓ Importing app.models...")
    from app.models import ErrorResponse, ErrorType
    print("  Models imported successfully")
    print()
    
    print("✓ Importing app.main...")
    from app.main import app
    print("  FastAPI app imported successfully")
    print()
    
    print("✅ All backend imports successful!")
    print()
    print("Backend is ready to start with:")
    print("  ./run.sh")
    print()
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
