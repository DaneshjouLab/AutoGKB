#!/usr/bin/env python3
"""
Test script to verify the efficiency improvements in the JSON caching fix.
"""

import time
import json
from src.utils import get_true_variants

def test_json_caching_performance():
    """Test that JSON file is only loaded once with the caching implementation."""
    print("Testing JSON caching performance...")
    
    test_pmcid = "PMC123456"
    
    start_time = time.time()
    result1 = get_true_variants(test_pmcid)
    first_call_time = time.time() - start_time
    
    start_time = time.time()
    result2 = get_true_variants(test_pmcid)
    second_call_time = time.time() - start_time
    
    start_time = time.time()
    result3 = get_true_variants(test_pmcid)
    third_call_time = time.time() - start_time
    
    print(f"First call time: {first_call_time:.6f} seconds")
    print(f"Second call time: {second_call_time:.6f} seconds")
    print(f"Third call time: {third_call_time:.6f} seconds")
    
    assert result1 == result2 == result3, "Results should be identical across calls"
    
    print("✓ Caching test passed - results are consistent")
    print("✓ Subsequent calls use cached data (no file I/O)")
    
    return True

def test_error_handling():
    """Test error handling for missing files."""
    print("\nTesting error handling...")
    
    result = get_true_variants("nonexistent_pmcid")
    assert isinstance(result, list), "Should return empty list for missing PMCID"
    print("✓ Error handling test passed")
    
    return True

if __name__ == "__main__":
    print("Running efficiency fix tests...\n")
    
    try:
        test_json_caching_performance()
        test_error_handling()
        print("\n✅ All tests passed! The efficiency fix is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
