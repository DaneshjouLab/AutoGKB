# Ontology Module

This module provides normalization and standardization capabilities for biological entities (variants and drugs) used in the AutoGKB system. It enables consistent identification and mapping of genetic variants and pharmaceutical compounds to standardized ontologies and databases.

## Overview

The ontology module contains normalizers that:
- **Standardize variant nomenclature** using dbSNP, PharmGKB, and star allele databases
- **Normalize drug names** using PubChem, PharmGKB, and RxNorm APIs
- **Provide consistent data structures** for normalized results
- **Handle multiple input formats** (rsIDs like "rs1799853", star alleles like "CYP2D6*4", brand/generic drug names like "Gleevec"/"imatinib") and return structured metadata like PubChem CIDs, SMILES strings, enzyme activity levels, PharmGKB IDs, and molecular formulas

## Module Structure

```
src/ontology/
├── __init__.py           # Module exports
├── variant_ontology.py   # Variant normalization classes
├── drug_ontology.py      # Drug normalization classes
└── README.md            # This file
```

## Core Classes

### Data Structures

#### `NormalizationResult`
A dataclass that standardizes normalization outputs across all normalizers.

**Fields:**
- `raw_input: str` - Original input string
- `normalized_output: str` - Standardized/normalized result
- `entity_type: str` - Type of entity ("variant", "drug", etc.)
- `source: str` - Database/API source of normalization
- `metadata: Dict[str, Any]` - Additional structured data

### Base Classes

#### `BaseNormalizer` (Abstract)
Base class for all normalizers providing:
- Handler registration system
- Standardized normalization workflow
- Error handling and logging
- Abstract `name()` method

## Variant Normalization

### `RSIDNormalizer`
Normalizes rsID variants (e.g., `rs1799853`) using:
- **dbSNP** via NCBI Entrez API
- **PharmGKB** variant database

**Usage:**
```python
from src.ontology import RSIDNormalizer

normalizer = RSIDNormalizer(email="your@email.com", api_key="optional")
result = normalizer.normalize("rs1799853")
```

### `StarAlleleNormalizer`
Normalizes star allele nomenclature (e.g., `CYP2D6*4`) using:
- **PharmVar** via Clinical Tables API
- Comprehensive metadata including enzyme activity, protein changes

**Usage:**
```python
from src.ontology import StarAlleleNormalizer

normalizer = StarAlleleNormalizer()
result = normalizer.normalize("CYP2D6*4")
```

## Drug Normalization

### `DrugNormalizer`
Normalizes drug names using multiple cascading sources:
1. **PubChem** - Chemical structure and IUPAC names
2. **PharmGKB** - Pharmacogenomic drug information
3. **RxNorm** - Clinical drug terminology

**Usage:**
```python
from src.ontology import DrugNormalizer

normalizer = DrugNormalizer()
result = normalizer.normalize("imatinib")  # or "Gleevec"
```

**Features:**
- Brand name to generic conversion
- Chemical structure data (SMILES, molecular formula)
- Cross-reference between multiple drug databases
- Comprehensive metadata preservation

## API Endpoints Used

| Database | Endpoint | Purpose |
|----------|----------|---------|
| dbSNP | NCBI Entrez | Variant information lookup |
| PharmGKB | `api.pharmgkb.org/v1/data/variant` | Variant annotations |
| PharmGKB | `api.pharmgkb.org/v1/data/chemical` | Drug information |
| PubChem | `pubchem.ncbi.nlm.nih.gov/rest/pug` | Chemical properties |
| RxNorm | `rxnav.nlm.nih.gov/REST` | Clinical drug terminology |
| Clinical Tables | `clinicaltables.nlm.nih.gov/api/star_alleles` | Star allele data |

## Example Usage

### Basic Normalization
```python
from src.ontology import RSIDNormalizer, DrugNormalizer

# Normalize a variant
variant_normalizer = RSIDNormalizer(email="test@example.com")
variant_result = variant_normalizer.normalize("rs1799853")

if variant_result:
    print(f"Normalized: {variant_result.normalized_output}")
    print(f"Source: {variant_result.source}")
    print(f"Metadata: {variant_result.metadata}")

# Normalize a drug
drug_normalizer = DrugNormalizer()
drug_result = drug_normalizer.normalize("imatinib")

if drug_result:
    print(f"IUPAC Name: {drug_result.normalized_output}")
    print(f"PubChem CID: {drug_result.metadata.get('cid')}")
    print(f"SMILES: {drug_result.metadata.get('canonical_smiles')}")
```

### Processing Annotation Files
Both modules include demonstration functions:
- `extract_variants_from_annotations()` - Extract and normalize variants from JSON files
- `extract_drugs_from_annotations()` - Extract and normalize drugs from JSON files

## Error Handling

All normalizers implement robust error handling:
- **Network timeouts** (5-10 second limits)
- **API rate limiting** awareness
- **Graceful degradation** when services are unavailable
- **Comprehensive logging** using loguru

## Configuration Requirements

### Required Dependencies
- `requests` - HTTP API calls
- `biopython` - NCBI Entrez access
- `loguru` - Structured logging

### API Keys/Configuration
- **NCBI Entrez**: Email required, API key optional but recommended
- **Other APIs**: No authentication required

### Environment Setup
```python
# For NCBI access
Entrez.email = "your@email.com"  # Required
Entrez.api_key = "your_api_key"  # Optional but recommended
```

## Testing

Run the test functions included in each module:
```bash
python -m src.ontology.variant_ontology
python -m src.ontology.drug_ontology
```

These will test both individual normalizers and demonstrate processing of annotation files from the `data/annotations` directory.

## Integration Points

This module integrates with:
- **Annotation processing pipeline** - Normalizes extracted entities
- **Knowledge graph construction** - Provides standardized identifiers
- **Cross-reference mapping** - Links entities across databases
- **Data validation** - Ensures entity consistency