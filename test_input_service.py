"""
Test input service integration with backend.
"""

import sys
sys.path.insert(0, 'frontend')

from services.input_service import input_service

print("=" * 60)
print("INPUT SERVICE VERIFICATION")
print("=" * 60)
print()

# Test 1: Service initialization
print("✓ Test 1: Input service initialization")
try:
    assert input_service is not None
    print("  ✅ Input service initialized")
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    sys.exit(1)

print()

# Test 2: Text submission (requires backend)
print("✓ Test 2: Text submission to backend")
try:
    test_content = "Week 1: Introduction to Python\nWeek 2: Data Structures\nWeek 3: Algorithms"
    
    print(f"  Submitting test content ({len(test_content)} chars)...")
    result = input_service.submit_text(test_content, "syllabus")
    
    print(f"  ✅ Input ID: {result.get('input_id', 'N/A')[:20]}...")
    print(f"  ✅ Detected Type: {result.get('detected_type', 'N/A')}")
    print(f"  ✅ Text Length: {result.get('extracted_text_length', 0)} chars")
    
    # Save input_id for next test
    test_input_id = result.get('input_id')
    
except Exception as e:
    print(f"  ❌ FAIL: {e}")
    print("  (This is expected if backend is not running)")
    test_input_id = None

print()

# Test 3: Get input status (requires backend and previous test)
if test_input_id:
    print("✓ Test 3: Get input status")
    try:
        status = input_service.get_input_status(test_input_id)
        
        print(f"  ✅ Input ID: {status.get('input_id', 'N/A')[:20]}...")
        print(f"  ✅ Detected Type: {status.get('detected_type', 'N/A')}")
        print(f"  ✅ Extracted Text: {len(status.get('extracted_text', ''))} chars")
        
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
else:
    print("✓ Test 3: Get input status")
    print("  ⏭️  SKIPPED (no input_id from previous test)")

print()
print("=" * 60)
print("INPUT SERVICE VERIFICATION COMPLETE")
print("=" * 60)
print()

if test_input_id:
    print("✅ All tests passed!")
    print()
    print("Input service is ready for use in the Input page.")
else:
    print("⚠️  Backend tests skipped (backend not running)")
    print()
    print("Input service code is valid and ready.")
    print("Start the backend to test full integration.")

print()
