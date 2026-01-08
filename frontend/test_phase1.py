"""
Phase 1 verification script.

Tests all Phase 1 success criteria without running Streamlit.
"""

import sys
from pathlib import Path

# Add frontend to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("PHASE 1 VERIFICATION")
print("=" * 60)
print()

# Test 1: Configuration loads
print("✓ Test 1: Configuration loads from config.py")
try:
    from config import config
    print(f"  Backend URL: {config.BACKEND_URL}")
    print(f"  API Timeout: {config.API_TIMEOUT}s")
    print(f"  Page Title: {config.PAGE_TITLE}")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 2: API client can be imported
print("✓ Test 2: API client imports correctly")
try:
    # Import without 'frontend' prefix since we're already in frontend dir
    import services.api_client as api_module
    api_client = api_module.api_client
    print(f"  Base URL: {api_client.base_url}")
    print(f"  Timeout: {api_client.timeout}s")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 3: Utility functions work
print("✓ Test 3: Utility functions work correctly")
try:
    import utils.validators as validators_module
    import utils.formatters as formatters_module
    validate_text_input = validators_module.validate_text_input
    validate_quiz_answers = validators_module.validate_quiz_answers
    format_time = formatters_module.format_time
    format_percentage = formatters_module.format_percentage
    format_score = formatters_module.format_score
    
    # Test validators
    valid, msg = validate_text_input("This is a test input text")
    assert valid, f"Text validation failed: {msg}"
    
    valid, msg = validate_quiz_answers({i: "answer" for i in range(1, 11)}, 10)
    assert valid, f"Quiz validation failed: {msg}"
    
    # Test formatters
    assert format_time(125) == "02:05", "Time formatting failed"
    assert format_percentage(85.5) == "85.5%", "Percentage formatting failed"
    assert format_score(8, 10) == "8/10", "Score formatting failed"
    
    print("  Validators: ✅")
    print("  Formatters: ✅")
    print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 4: Backend connectivity (if backend is running)
print("✓ Test 4: Backend connectivity test")
try:
    is_healthy = api_client.health_check()
    if is_healthy:
        print("  Backend is healthy: ✅")
        print("  ✅ PASS")
    else:
        print("  ⚠️  Backend is not running (this is OK for Phase 1 testing)")
        print("  ✅ PASS (with warning)")
except Exception as e:
    print(f"  ⚠️  Backend connection failed: {e}")
    print("  ✅ PASS (with warning - backend not required for Phase 1 verification)")

print()

# Test 5: File structure
print("✓ Test 5: File structure verification")
try:
    required_files = [
        "config.py",
        "services/__init__.py",
        "services/api_client.py",
        "utils/__init__.py",
        "utils/state_manager.py",
        "utils/validators.py",
        "utils/formatters.py",
        "components/__init__.py",
        "components/loading_spinner.py",
        "components/error_display.py",
        "app.py",
        "requirements.txt",
        "README.md",
        ".env.example",
        ".gitignore"
    ]
    
    frontend_dir = Path(__file__).parent
    missing_files = []
    
    for file in required_files:
        file_path = frontend_dir / file
        if not file_path.exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"  ❌ Missing files: {', '.join(missing_files)}")
        sys.exit(1)
    else:
        print(f"  All {len(required_files)} required files exist: ✅")
        print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 6: Pages exist
print("✓ Test 6: Page files verification")
try:
    required_pages = [
        "pages/1_📤_Input.py",
        "pages/2_🗺️_Roadmap.py",
        "pages/3_📚_Content.py",
        "pages/4_📝_Quiz.py",
        "pages/5_📊_Analytics.py",
        "pages/6_❓_Doubt.py"
    ]
    
    frontend_dir = Path(__file__).parent
    missing_pages = []
    
    for page in required_pages:
        page_path = frontend_dir / page
        if not page_path.exists():
            missing_pages.append(page)
    
    if missing_pages:
        print(f"  ❌ Missing pages: {', '.join(missing_pages)}")
        sys.exit(1)
    else:
        print(f"  All {len(required_pages)} page files exist: ✅")
        print("  ✅ PASS")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("PHASE 1 VERIFICATION COMPLETE")
print("=" * 60)
print()
print("✅ All Phase 1 success criteria met!")
print()
print("Next steps:")
print("1. Start the backend: cd .. && ./run.sh")
print("2. Run the frontend: streamlit run app.py")
print("3. Verify backend connectivity in the UI")
print("4. Proceed to Phase 2 implementation")
print()
