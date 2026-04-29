# test_retry_manual.py
from unittest.mock import Mock, patch
from healthchain.gateway.fhir.errors import RateLimitError, RetryableError
from healthchain.gateway.fhir.request_retry import with_retry, get_delay

# Test 1 - succeeds on first attempt
print("Test 1: succeeds on first attempt")
func = Mock(return_value="ok")
result = with_retry(func)
assert result == "ok"
assert func.call_count == 1
print(f"  PASS - called {func.call_count} time")

# Test 2 - retries on RateLimitError then succeeds
print("Test 2: retries on RateLimitError")
func = Mock(side_effect=[
    RateLimitError("rate limit", "429"),
    "ok"
])
with patch("time.sleep") as mock_sleep:
    result = with_retry(func, max_retries=3)
assert result == "ok"
assert func.call_count == 2
print(f"  PASS - retried {func.call_count} times, slept {mock_sleep.call_count} time")

# Test 3 - retries on RetryableError then succeeds
print("Test 3: retries on RetryableError")
func = Mock(side_effect=[
    RetryableError("unavailable", "503", "503"),
    RetryableError("unavailable", "503", "503"),
    "ok"
])
with patch("time.sleep") as mock_sleep:
    result = with_retry(func, max_retries=3)
assert result == "ok"
assert func.call_count == 3
print(f"  PASS - retried {func.call_count} times, slept {mock_sleep.call_count} times")

# Test 4 - fails after max retries
print("Test 4: fails after max retries")
func = Mock(side_effect=RetryableError("unavailable", "503", "503"))
with patch("time.sleep"):
    try:
        with_retry(func, max_retries=2)
        print("  FAIL - should have raised")
    except RetryableError:
        print(f"  PASS - raised after {func.call_count} attempts")

# Test 5 - delay increases with each attempt
print("Test 5: delay increases with each attempt")
d0 = get_delay(0)
d1 = get_delay(1)
d2 = get_delay(2)
assert d1 > d0 and d2 > d1
print(f"  PASS - delays: {d0:.2f}s, {d1:.2f}s, {d2:.2f}s")

print()
print("All tests passed.")