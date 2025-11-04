# Term Normalization

## Goal
Take incoming variant annotations and replace all terms with normalized identifiers that map to current entries in ClinPGx and PharmGKB. This ensures consistent terminology across pharmacogenomic data.

## Overview

The term normalization module provides automated lookup and normalization for:
- **Variants/Alleles**: rsIDs and star alleles
- **Drugs**: Drug names, generic names, and trade names

## Architecture

### Main Components

1. **`term_lookup.py`**: Main entry point providing `TermLookup` class and `normalize_annotation()` function
2. **`variant_search.py`**: Handles variant/allele normalization via `VariantLookup` class
3. **`drug_search.py`**: Handles drug normalization via `DrugLookup` class
4. **`search_utils.py`**: Shared utilities for similarity matching

## Usage

### Normalizing an Annotation File

```python
from pathlib import Path
from src.term_normalization.term_lookup import normalize_annotation

input_path = Path("data/example_annotation.json")
output_path = Path("data/example_annotation_normalized.json")

normalize_annotation(input_path, output_path)
```

This will:
1. Load the annotation JSON file
2. Normalize all `Variant/Haplotypes` and `Drug(s)` fields in annotation types: `var_pheno_ann`, `var_fa_ann`, `var_drug_ann`
3. Add normalized fields with `_normalized` suffix (e.g., `Variant/Haplotypes_normalized`)
4. Include a `term_mappings` section with details about each normalized term

### Using TermLookup Directly

```python
from src.term_normalization.term_lookup import TermLookup, TermType

lookup = TermLookup()

# Search for a variant
variant_results = lookup.search("rs12345", term_type=TermType.VARIANT, threshold=0.8, top_k=1)

# Search for a drug
drug_results = lookup.search("aspirin", term_type=TermType.DRUG, threshold=0.8, top_k=1)
```

## Variant Normalization

The `VariantLookup` class handles variant normalization with the following features:

### Search Strategy

1. **rsID Lookup** (for variants starting with "rs"):
   - Queries PharmGKB API (`/v1/data/variant`)
   - Searches local ClinPGx variant database (`data/term_lookup_info/variants.tsv`)
   - Searches variant names and synonyms

2. **Star Allele Lookup** (for variants like *1, *2):
   - Queries PharmGKB API (`/v1/data/haplotype`)
   - Searches local ClinPGx variant database

### Return Format

```python
VariantSearchResult(
    raw_input="rs12345",
    id="PA166154595",
    normalized_term="rs12345",
    url="https://www.clinpgx.org/variant/PA166154595",
    score=1.0
)
```

## Drug Normalization

The `DrugLookup` class handles drug normalization with the following features:

### Search Strategy

1. **ClinPGx Lookup** (primary):
   - Searches drug name in local database (`data/term_lookup_info/drugs.tsv`)
   - Searches generic names and trade names
   - Returns PharmGKB Accession IDs

2. **RxNorm Lookup** (fallback):
   - Queries RxNorm API when ClinPGx search yields no results
   - Converts RxCUI to PharmGKB Accession ID using local mapping
   - Provides broader drug name coverage

### Return Format

```python
DrugSearchResult(
    raw_input="aspirin",
    id="PA449552",
    normalized_term="etoposide",
    url="https://www.clinpgx.org/chemical/PA449552",
    score=1.0
)
```

## Data Requirements

The module requires local TSV files in the `data/term_lookup_info/` directory:

- `variants.tsv`: Variant names, IDs, and synonyms from ClinPGx
- `drugs.tsv`: Drug names, generic names, trade names, RxNorm IDs, and PharmGKB IDs

## Configuration

### Parameters

- **`threshold`** (default: 0.8): Minimum similarity score for fuzzy matching (0.0-1.0)
- **`top_k`** (default: 1): Number of top results to return
- **`data_dir`** (default: "data"): Base directory for lookup TSV files

### Similarity Matching

The module uses string similarity (via `calc_similarity` in `search_utils.py`) to match input terms against database entries, allowing for:
- Typos and spelling variations
- Case insensitivity
- Partial matches

## Output Format

The `normalize_annotation()` function adds:

1. **Normalized fields** in each annotation object:
   - `Variant/Haplotypes_normalized`: PharmGKB variant ID
   - `Drug(s)_normalized`: PharmGKB drug ID

2. **Term mappings section** at the root level:
```json
{
  "term_mappings": {
    "rs6539870": {
      "raw_input": "rs6539870",
      "id": "PA166154595",
      "normalized_term": "rs6539870",
      "url": "https://www.clinpgx.org/variant/PA166154595",
      "score": 1.0
    },
    "etoposide": {
      "raw_input": "etoposide",
      "id": "PA449552",
      "normalized_term": "etoposide",
      "url": "https://www.clinpgx.org/chemical/PA449552",
      "score": 1.0
    }
  }
}
```

## Future Work

### Gene Normalization
Currently not implemented. Will require:
- HGNC gene symbol lookup
- Gene ID normalization
- Alias resolution

### Phenotype Normalization
Currently not implemented. Will require:
- Ontology mapping (HPO, MeSH, etc.)
- Phenotype term standardization
