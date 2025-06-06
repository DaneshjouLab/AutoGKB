# Duplicate PMIDs and Data Structure Explanation

## Overview

This document explains why there are fewer unique markdown file names than entries in `parsed_drug_annotations.jsonl` and clarifies the data structure regarding duplicate variant annotations.

## Data Structure Summary

| Data Source | Count | Description |
|-------------|-------|-------------|
| `var_drug_ann.tsv` | 12,474 entries | Original variant annotation entries |
| Unique PMIDs in original data | 4,262 | Unique research papers |
| Available markdown files | 1,432 | Papers with full text available |
| `parsed_drug_annotations.jsonl` | 4,516 entries | Annotations with paper content found |
| Unique PMIDs with paper content | ~1,431 | Unique papers that were successfully processed |

## Why There Are "Duplicate" PMIDs

### Multiple Variant Annotations Per Paper

Many research papers study multiple genetic variants and their associations with drugs. Each variant gets its own annotation entry, even though they come from the same paper.

**Example from PMID 39792745:**
- `rs2909451` in `DPP4` gene for sitagliptin efficacy
- `rs2285676` in `KCNJ11` gene for sitagliptin efficacy  
- `rs163184` in `KCNQ1` gene for sitagliptin efficacy
- `rs4664443` in `DPP4` gene for sitagliptin efficacy
- `rs1799853` in `CYP2C9` gene for sitagliptin efficacy
- And several others...

### Data Processing Approach

The conversion process in `convert_to_jsonl.ipynb`:

1. **Processes each annotation individually** - Each row in the TSV becomes one entry
2. **Adds paper content to each entry** - The full markdown content is attached to every variant annotation from the same paper
3. **Preserves granular annotations** - Each variant-drug association remains as a separate data point

## Implications

### Storage Efficiency
- The same paper content is duplicated across multiple entries
- On average, each paper has ~3-4 variant annotations
- This results in significant data duplication but preserves analytical granularity

### Analysis Benefits
- Each variant annotation can be analyzed independently
- Full paper context is available for each genetic association
- Researchers can study variant-specific effects while having access to the complete source material

### File Mapping
- 1,432 unique markdown files map to 4,516 annotation entries
- Not all PMIDs have corresponding markdown files (some papers may not have been successfully downloaded or processed)
- Only 4,516 out of 12,474 original annotations have paper content (36% success rate)

## Data Integrity

This structure is **intentional and correct**:
- ✅ Each variant annotation is treated as an independent data point
- ✅ Full paper context is preserved for each annotation
- ✅ Researchers can filter by specific variants, genes, or drugs while maintaining paper context
- ✅ The relationship between annotations and source papers is maintained via PMID

## Usage Recommendations

When analyzing this data:
- **For paper-level analysis**: Group by PMID to avoid counting papers multiple times
- **For variant-level analysis**: Use entries directly as each represents a unique genetic association
- **For summary statistics**: Be aware that paper counts and annotation counts are different metrics