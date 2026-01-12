# Benchmark Analysis Summary
**Generated from 5 sample articles**
**Analysis Date:** 2025-11-24 17:09:34

## Overall Performance (Excluding 'one_empty' entries)

| Benchmark | Average Score | Valid Examples |
|-----------|--------------|----------------|
| DRUG | 0.715 | 2 |
| FA | 0.375 | 1 |
| PHENO | 0.554 | 3 |
| STUDY_PARAMETERS | 0.677 | 5 |

## Key Findings

### 1. Most Problematic Fields

**Study Parameters:**
- **Study Cases**: Appears 5 times with average score 0.364
- **Characteristics**: Appears 5 times with average score 0.374
- **Biogeographical Groups**: Appears 5 times with average score 0.000
- **Study Type**: Appears 4 times with average score 0.200
- **Ratio Stat Type**: Appears 4 times with average score 0.333

**Pheno:**
- **Alleles**: Appears 3 times with average score 0.280
- **Phenotype**: Appears 3 times with average score 0.223
- **Comparison Allele(s) or Genotype(s)**: Appears 3 times with average score 0.074
- **Variant/Haplotypes**: Appears 2 times with average score 0.458
- **Phenotype Category**: Appears 2 times with average score 0.500

**Drug:**
- **PMID**: Appears 2 times with average score 0.000
- **Population types**: Appears 2 times with average score 0.450
- **Population Phenotypes or diseases**: Appears 2 times with average score 0.577
- **Comparison Allele(s) or Genotype(s)**: Appears 2 times with average score 0.000

**Fa:**
- **Variant/Haplotypes**: Appears 1 times with average score 0.000
- **Drug(s)**: Appears 1 times with average score 0.000
- **Phenotype Category**: Appears 1 times with average score 0.000
- **Alleles**: Appears 1 times with average score 0.000
- **Specialty Population**: Appears 1 times with average score 0.000

### 2. Missing Value Patterns

**Predictions Missing Critical Fields:**
- study_parameters: Frequency in Cases - Missing in 17 cases
- study_parameters: Allele of Frequency in Cases - Missing in 17 cases
- study_parameters: Frequency in Controls - Missing in 17 cases
- study_parameters: Allele of Frequency in Controls - Missing in 17 cases
- study_parameters: Study Controls - Missing in 15 cases
- study_parameters: Ratio Stat - Missing in 14 cases
- study_parameters: Confidence Interval Start - Missing in 14 cases
- study_parameters: Confidence Interval Stop - Missing in 14 cases
- study_parameters: Study Type - Missing in 3 cases
- study_parameters: P Value - Missing in 3 cases

**Ground Truth Missing but Predictions Provide:**
- study_parameters: Study Type - 14 times
- study_parameters: Ratio Stat Type - 10 times
- pheno: Alleles - 7 times
- pheno: Comparison Allele(s) or Genotype(s) - 7 times
- drug: Comparison Allele(s) or Genotype(s) - 1 times
- fa: Drug(s) - 1 times
- fa: Specialty Population - 1 times
- fa: When treated with/exposed to/when assayed with - 1 times
- fa: Multiple drugs And/or - 1 times
- fa: Cell type - 1 times

### 3. Common Mismatch Patterns

1. **Numeric Value Mismatches** (Study Cases/Controls):
   - Frequent mismatches in population counts
   - Suggests LLM may be extracting different population counts or misinterpreting study design

2. **Semantic Similarity Issues** (Characteristics, Phenotype):
   - Similar meaning but different wording causing lower scores
   - May need improved embeddings or similarity thresholds

3. **Format/Standardization Issues**:
   - Minor differences in formatting causing score reductions
   - Case sensitivity, punctuation, spacing differences

4. **Missing vs Present**:
   - Many fields where GT is None but predictions provide values (especially Study Type)
   - Many fields where GT has values but predictions are None (especially statistical fields)

### 4. Dependency Issues

- 1x: Invalid star allele format: (DPYD*2A)

## Recommendations

1. **Improve Statistical Field Extraction**:
   - Ratio Stat, Confidence Intervals, and P Values are frequently missing
   - Consider adding explicit prompts for statistical measures

2. **Study Type Handling**:
   - LLM often provides Study Type when GT is None - this may be acceptable
   - Consider whether this should be penalized or if it's useful additional information

3. **Biogeographical Groups**:
   - LLM consistently outputs "Unknown" - needs better extraction or different handling

4. **Variant/Haplotypes Matching**:
   - Improved with variant expansion/normalization (pheno benchmark fixed)
   - Still some cases where variants don't match - may need further refinement

5. **PMID Extraction**:
   - LLM never extracts PMID - consider if this should be provided as input or if extraction is needed

6. **Semantic Similarity Thresholds**:
   - Many fields with similar meanings score low due to wording differences
   - May need to adjust similarity thresholds or improve embeddings