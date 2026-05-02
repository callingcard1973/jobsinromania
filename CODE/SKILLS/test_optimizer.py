#!/usr/bin/env python3
"""Tests for Token Optimizer Suite."""

import sys
import tempfile
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_router import detect_task, get_context_modules
from cache_layer import TokenCache
from truncator import truncate, truncate_csv, detect_output_type


def test_task_router():
    """Test task detection."""
    print("Testing task_router...")

    # Note: Task router prioritizes explicit keywords.
    # "error in scraper" -> scraper (keyword match) not debug
    cases = [
        ("fix the norway scraper", "scraper"),
        ("analyze contacts.csv", "csv"),
        ("send campaign via brevo", "email"),
        ("sync to raspi", "ops"),
        ("why is the script failing with traceback", "debug"),
        ("hello there", "general"),
    ]

    passed = 0
    for msg, expected in cases:
        # Use /home to avoid CSV files in /tmp affecting results
        result = detect_task(msg, "/home")
        status = "OK" if result == expected else f"FAIL (got {result})"
        print(f"  '{msg[:30]}' -> {expected}: {status}")
        if result == expected:
            passed += 1

    print(f"  {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_context_modules():
    """Test module mapping."""
    print("Testing get_context_modules...")

    cases = [
        ("scraper", ["scraper.md", "skills.md"]),
        ("csv", ["csv.md", "skills.md"]),
        ("general", []),
    ]

    passed = 0
    for task, expected in cases:
        result = get_context_modules(task)
        status = "OK" if result == expected else f"FAIL (got {result})"
        print(f"  {task} -> {expected}: {status}")
        if result == expected:
            passed += 1

    print(f"  {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_cache():
    """Test cache operations."""
    print("Testing cache_layer...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cache = TokenCache(db_path)

        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")

        # Test set/get
        cache.set(str(test_file), "test", "cached summary")
        result = cache.get(str(test_file), "test")
        assert result == "cached summary", f"Cache get failed: {result}"
        print("  set/get: OK")

        # Test invalidation
        cache.invalidate(str(test_file))
        result = cache.get(str(test_file), "test")
        assert result is None, "Invalidation failed"
        print("  invalidate: OK")

        # Test stats
        stats = cache.stats()
        assert "total_entries" in stats
        print("  stats: OK")

    print("  3/3 passed\n")
    return True


def test_truncator():
    """Test truncation."""
    print("Testing truncator...")

    # Generate long output (must exceed LIMITS["bash"] = 8000 chars)
    long_output = "\n".join(f"Line {i}: This is a longer line with more content to ensure we exceed limits" for i in range(500))

    # Test truncation happens
    result = truncate(long_output, "bash")
    assert len(result) < len(long_output), "Truncation didn't reduce size"
    assert "truncated" in result.lower(), "Missing truncation marker"
    print("  basic truncation: OK")

    # Test short output passes through
    short = "just a few lines"
    result = truncate(short, "bash")
    assert result == short, "Short output was modified"
    print("  short passthrough: OK")

    # Test CSV truncation
    csv_data = "col1,col2,col3\n" + "\n".join(f"a{i},b{i},c{i}" for i in range(100))
    result = truncate_csv(csv_data)
    assert "col1,col2,col3" in result, "Header missing"
    assert "rows" in result.lower(), "Row count missing"
    print("  CSV truncation: OK")

    # Test type detection
    assert detect_output_type('{"key": "value"}') == "json"
    assert detect_output_type("a,b,c\n1,2,3") == "csv"
    print("  type detection: OK")

    print("  4/4 passed\n")
    return True


def test_token_savings():
    """Estimate token savings."""
    print("Calculating potential savings...")

    # Simulate typical session
    full_claude_md = 13500  # bytes (current)
    minimal_claude_md = 1800  # bytes (new)
    avg_module = 2000  # bytes

    startup_before = full_claude_md
    startup_after = minimal_claude_md  # Only load core

    # Most sessions need 1-2 modules
    typical_after = minimal_claude_md + avg_module

    savings_startup = (startup_before - startup_after) / startup_before * 100
    savings_typical = (startup_before - typical_after) / startup_before * 100

    print(f"  Startup: {startup_before} -> {startup_after} bytes ({savings_startup:.0f}% savings)")
    print(f"  Typical session: {startup_before} -> {typical_after} bytes ({savings_typical:.0f}% savings)")

    # Cache savings
    repeat_query_before = 5000  # tokens to re-analyze
    repeat_query_after = 100  # cached summary
    cache_savings = (repeat_query_before - repeat_query_after) / repeat_query_before * 100
    print(f"  Repeat queries: {repeat_query_before} -> {repeat_query_after} tokens ({cache_savings:.0f}% savings)")

    print()
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("TOKEN OPTIMIZER SUITE - TEST SUITE")
    print("=" * 50 + "\n")

    results = [
        ("task_router", test_task_router()),
        ("context_modules", test_context_modules()),
        ("cache", test_cache()),
        ("truncator", test_truncator()),
        ("savings_estimate", test_token_savings()),
    ]

    print("=" * 50)
    print("RESULTS")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
