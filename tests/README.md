# Tests

This directory contains test files for the AutoGKB project.

## Files

- `variant_list_tests.py` - Tests for variant list extraction functionality
- `utils.py` - Utility functions for test comparisons
- `data/true_variant_list.json` - Ground truth data for variant list testing

## Variant List Tests

The `variant_list_tests.py` module tests the variant extraction component:

- `load_ground_truth(pmcid)` - Loads ground truth variant data for a given PMCID
- `parse_variant_list(variant_list)` - Extracts variant IDs from variant list data (variant_list is a list of class Variant)
- `calc_contingencies(ground_truth, extracted)` - Calculates TP, TN, FP, FN metrics comparing two lists of strings
- `calc_metrics(contingencies)` - Calculates precision, recall, and F1 score from {"true_positives": int, "true_negatives: int, ...}
- `test_extract_function(pmcids, verbose)` - Main test function that evaluates extraction performance

## Test Utilities

The `utils.py` module provides:

- `compare_lists(experimental_list, ground_truth_list, pmcid)` - Visually compares experimental vs ground truth lists with color coding (green for matches, red for mismatches)

## Running Tests

```python
from tests.variant_list_tests import test_extract_function

# Test single PMCID
test_extract_function("PMC11730665", verbose=True)

# Test multiple PMCIDs
test_extract_function(["PMC11730665", "PMC5712579"])
```