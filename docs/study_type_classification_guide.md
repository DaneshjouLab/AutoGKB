# Study Type Classification Guide

## Overview

This guide provides a systematic framework for assigning study type labels to pharmacogenomics research papers. Study types are composite labels that describe multiple dimensions of a study's design, temporal characteristics, and analysis approach.

## Classification Framework

Study type labels consist of up to three dimensions combined with commas:

```
[PRIMARY METHOD(S)], [TEMPORAL COMPONENT], [ANALYSIS TYPE]
```

**Example:** `cohort, GWAS, retrospective`

## Dimension 1: Primary Study Method

The primary method describes the fundamental study design and data collection approach. Multiple primary methods can coexist.

### Single Primary Methods

#### Cohort Study
- **Definition:** Observes a defined group over time to study incidence, causes, and prognosis of disease
- **Key indicators:**
  - "followed over X years"
  - "longitudinal study"
  - "incidence rate"
  - "cohort of patients"
  - Measures outcomes in a defined population
- **Examples in data:** 6,434 occurrences
- **Typical combinations:** `cohort, prospective`, `cohort, retrospective`, `cohort, GWAS`

#### Case/Control Study
- **Definition:** Compares individuals with a condition (cases) to those without (controls) to identify associated factors
- **Key indicators:**
  - "cases and controls"
  - "matched controls"
  - "odds ratio"
  - Retrospective comparison of exposure between groups
- **Examples in data:** 1,486 occurrences
- **Typical combinations:** `case/control, GWAS`, `case/control, retrospective`

#### Clinical Trial
- **Definition:** Interventional study where participants are assigned treatments and outcomes are measured
- **Key indicators:**
  - "randomized controlled trial"
  - "intervention group"
  - "treatment arm"
  - "placebo-controlled"
  - Active manipulation of exposure
- **Examples in data:** 524 occurrences
- **Typical combinations:** `clinical trial, prospective`, `clinical trial, GWAS`

#### GWAS (Genome-Wide Association Study)
- **Definition:** Analyzes genetic variants across genomes to find associations with traits or diseases
- **Key indicators:**
  - "genome-wide association"
  - "SNP array"
  - "genotyping platform"
  - "Manhattan plot"
  - Tests hundreds of thousands to millions of variants
- **Examples in data:** 407 occurrences
- **Typical combinations:** `GWAS`, `cohort, GWAS`, `case/control, GWAS`

#### Case Series
- **Definition:** Descriptive study tracking patients with a known exposure or treatment; no control group
- **Key indicators:**
  - "series of patients"
  - "consecutive cases"
  - No control group mentioned
  - Purely observational description
- **Examples in data:** 306 occurrences
- **Typical combinations:** `case series`, `case series, clinical trial`

#### Cross-Sectional Study
- **Definition:** Observational study measuring exposure and outcome simultaneously in a population
- **Key indicators:**
  - "cross-sectional survey"
  - "prevalence study"
  - Single time point measurement
  - No follow-up period
- **Examples in data:** 19 occurrences
- **Typical combinations:** `cross sectional`, `cross sectional, retrospective`

#### Linkage Study
- **Definition:** Genetic study mapping loci associated with traits by analyzing inheritance patterns in families
- **Key indicators:**
  - "linkage analysis"
  - "LOD score"
  - "pedigree"
  - Family-based inheritance tracking
- **Examples in data:** 13 occurrences
- **Typical combinations:** `linkage`, `linkage, trios`

#### Trios Study
- **Definition:** Genetic study involving parent-offspring trios to identify de novo mutations or transmission patterns
- **Key indicators:**
  - "parent-child trios"
  - "trio design"
  - "transmission disequilibrium test"
  - "HapMap cell lines" (often uses trio data)
- **Examples in data:** 9 occurrences
- **Typical combinations:** `trios`, `linkage, trios`

### Combined Primary Methods

Studies can employ multiple primary designs simultaneously. Common combinations:

#### Cohort + GWAS (212 occurrences)
- GWAS performed within a cohort study framework
- Example: "A prospective cohort underwent genome-wide genotyping"

#### Case/Control + GWAS (99 occurrences)
- GWAS using case-control design
- Example: "Cases with adverse drug reactions and matched controls were genotyped genome-wide"

#### Cohort + Case/Control (69 occurrences)
- Nested case-control within a cohort (cases arise from the cohort)
- Example: "From the cohort, patients who developed toxicity were matched to controls"

#### Clinical Trial + GWAS (51 occurrences)
- Genetic analysis embedded in clinical trial
- Example: "Trial participants were genotyped to identify pharmacogenomic markers"

#### Cohort + Clinical Trial (168 occurrences)
- Clinical trial analyzed as a cohort or trial data used for cohort-style analysis
- Example: "Clinical trial participants were followed as a cohort for long-term outcomes"

#### Case/Control + Clinical Trial (26 occurrences)
- Clinical trial data analyzed using case-control methodology
- Example: "From trial participants, those with adverse events (cases) were compared to controls"

## Dimension 2: Temporal Component

The temporal dimension describes when and how data was collected relative to outcomes.

### Prospective
- **Definition:** Study designed to follow subjects forward in time from exposure to outcome
- **Key indicators:**
  - "prospectively followed"
  - "enrolled and monitored"
  - "followed for X years"
  - "future outcomes tracked"
  - Data collected as events happen
- **Examples in data:** 270 standalone, 276 with cohort, 64 with clinical trial
- **When to assign:** Data collection begins before outcomes occur

### Retrospective
- **Definition:** Uses existing records to look backward at exposures and outcomes that already occurred
- **Key indicators:**
  - "medical records reviewed"
  - "historical cohort"
  - "existing data"
  - "retrospectively identified"
  - "chart review"
- **Examples in data:** 203 standalone, 348 with cohort, 76 with clinical trial
- **When to assign:** Data already exists at study initiation

### Both Prospective and Retrospective
- **Examples in data:** 6 occurrences
- **When to assign:** Study has distinct prospective and retrospective components
- **Example:** "Historical records reviewed (retrospective) and patients followed forward (prospective)"

### Decision Rules for Temporal Component

1. **Always add temporal component if clearly stated** in methods
2. **Default assumptions:**
   - Clinical trials → usually prospective (unless stated otherwise)
   - Case/control → usually retrospective (unless stated otherwise)
   - Cohort → can be either, must look for explicit indicators
3. **Omit if unclear** or not specified
4. **GWAS alone** → typically no temporal component unless part of cohort/trial

## Dimension 3: Analysis Type

The analysis type describes higher-level analytical approaches that can apply to any primary method.

### Meta-Analysis
- **Definition:** Combines results from multiple independent studies using statistical techniques
- **Key indicators:**
  - "meta-analysis"
  - "pooled analysis"
  - "systematic review with meta-analysis"
  - "combined data from X studies"
  - "forest plot"
  - "heterogeneity analysis (I²)"
- **Examples in data:** 552 occurrences
- **Typical combinations:**
  - `meta-analysis` (standalone)
  - `meta-analysis, GWAS` (90 occurrences)
  - `case/control, meta-analysis` (58 occurrences)
  - `cohort, meta-analysis` (21 occurrences)

### Replication
- **Definition:** Study designed to confirm or validate findings from prior research
- **Key indicators:**
  - "replication study"
  - "validation cohort"
  - "independent replication"
  - "confirmed previous findings"
  - "replication analysis"
  - Multiple separate cohorts tested
- **Examples in data:** 117 occurrences
- **Typical combinations:**
  - `replication` (standalone)
  - `cohort, replication` (36 occurrences)
  - `clinical trial, replication` (34 occurrences)
  - `case/control, replication` (32 occurrences)

### Meta-Analysis + Replication
- **Examples in data:** 17 occurrences
- **When to assign:** Meta-analysis that includes replication of specific findings
- **Example:** "Meta-analysis of existing studies with independent replication cohort"

## Label Construction Rules

### Rule 1: Ordering Convention
Based on frequency analysis, use this order:
1. Primary design(s) in descending order of specificity
2. Temporal component (if applicable)
3. Analysis type (if applicable)

**Examples:**
- `cohort, GWAS, retrospective`
- `case/control, meta-analysis`
- `clinical trial, replication, prospective`
- `cohort, case/control, GWAS, replication`

### Rule 2: Formatting Standards
- Use lowercase throughout
- Separate terms with `, ` (comma + space)
- Use `/` for compound terms: `case/control` (not "case-control")
- Order primary methods by importance/dominance in the paper

### Rule 3: Primary Method Priority
When multiple primary methods exist, order by:
1. The method that drove study enrollment
2. The method that defines the comparison
3. Additional analytical approaches

**Example:**
- If patients were enrolled as a cohort, then GWAS was performed → `cohort, GWAS`
- If GWAS was the main design with secondary cohort analysis → `GWAS, cohort`

### Rule 4: Omit Redundancy
- Don't add temporal component if it's implicit and universal
  - `clinical trial` (prospective is assumed, don't add unless explicitly stated)
  - `case/control` (retrospective is typical, only add if explicitly mentioned)
- Don't add "Unknown" unless truly unclassifiable

### Rule 5: Validate Combinations
Check if combination makes logical sense:
- **Common valid:** `cohort, GWAS, prospective` ✓
- **Rare but valid:** `case series, linkage, trios` ✓ (only 1 occurrence)
- **Questionable:** `clinical trial, case/control, meta-analysis, replication` (too many dimensions, verify)

## Classification Workflow

### Step 1: Read Methods Section
Focus on:
- Study design subsection
- Population/participants section
- Statistical analysis section
- First paragraph of methods

### Step 2: Identify Primary Method(s)
Ask:
1. How were participants selected? (cohort vs case/control vs trial enrollment)
2. Was there an intervention? (clinical trial)
3. What genetic methods were used? (GWAS, linkage, trios)
4. Is there a control group? (case series if no)
5. When was measurement done? (cross-sectional if single timepoint)

### Step 3: Identify Temporal Component
Ask:
1. Does it say "prospective" or "retrospective" explicitly?
2. Were participants followed forward? → prospective
3. Were records/data reviewed backward? → retrospective
4. If unclear, check if it's a typical pattern (e.g., case/control usually retrospective)

### Step 4: Identify Analysis Type
Ask:
1. Does it combine multiple studies? → meta-analysis
2. Does it validate prior findings? → replication
3. Both? → include both

### Step 5: Construct Label
Combine in order: [primary method(s)], [temporal], [analysis type]

### Step 6: Validate
Check against common patterns in the dataset:
- Is this combination in the frequency list?
- If novel, is it logically sound?
- Does it capture the study's essential design?

## Common Patterns Reference

Based on 11,078 total studies, here are the most common patterns:

| Pattern | Count | Interpretation |
|---------|-------|----------------|
| `cohort` | 6,434 | Simple cohort, temporal not specified |
| `case/control` | 1,486 | Simple case/control, temporal not specified |
| `meta-analysis` | 552 | Meta-analysis, primary method not specified |
| `clinical trial` | 524 | Simple clinical trial |
| `GWAS` | 407 | Pure GWAS without other design specified |
| `cohort, retrospective` | 348 | Historical cohort |
| `case series` | 306 | Descriptive series, no controls |
| `cohort, prospective` | 276 | Forward-looking cohort |
| `cohort, GWAS` | 212 | GWAS within cohort framework |
| `cohort, clinical trial` | 168 | Trial data as cohort or trial-based cohort |
| `replication` | 117 | Pure replication study |
| `case/control, GWAS` | 99 | GWAS with case/control design |
| `meta-analysis, GWAS` | 90 | Meta-analysis of GWAS studies |

## Special Cases

### None/Unknown Values
- **`None`:** 1,488 occurrences - likely data entry issues or unclassifiable
- **When to use:** Only when absolutely no design information is available
- **Better approach:** Use `Unknown` if some information exists but classification is ambiguous

### Single vs Multiple Study Phases
Some papers describe multiple studies or phases:
- **Discovery + Replication:** Use `replication` in the label
- **Multiple cohorts:** Choose the dominant/primary cohort design
- **Pooled analysis:** Consider `meta-analysis`

### Ambiguous Language
- "observational study" → Look for more specifics (cohort? case/control? cross-sectional?)
- "genetic study" → Is it GWAS? linkage? candidate gene? (candidate gene typically doesn't get special label)
- "pharmacogenomic study" → Not a study design, look for actual method

## Examples with Rationale

### Example 1: Simple Cohort
**Paper text:** "We prospectively enrolled 500 patients receiving warfarin and followed them for adverse events over 2 years."
- **Primary method:** cohort (enrolled and followed a defined group)
- **Temporal:** prospective (followed forward)
- **Analysis type:** none
- **Label:** `cohort, prospective`

### Example 2: Nested Case/Control GWAS
**Paper text:** "From a cohort of 10,000 patients, we identified 200 with severe adverse reactions (cases) and matched them 1:1 with controls. Genome-wide genotyping was performed."
- **Primary methods:** cohort (original enrollment), case/control (nested design), GWAS (genome-wide)
- **Temporal:** not explicitly stated, likely retrospective for case/control component
- **Analysis type:** none
- **Label:** `cohort, case/control, GWAS` (temporal omitted as mixed/unclear)

### Example 3: Meta-Analysis of Cohort Studies
**Paper text:** "We systematically reviewed and meta-analyzed 15 cohort studies examining the association between CYP2C9 variants and warfarin dose."
- **Primary method:** cohort (studies being meta-analyzed were cohorts)
- **Temporal:** not needed for meta-analysis
- **Analysis type:** meta-analysis
- **Label:** `cohort, meta-analysis`

### Example 4: Clinical Trial with Replication
**Paper text:** "A randomized trial tested the effect of genotype-guided dosing (N=1,000). Findings were replicated in an independent validation cohort (N=500)."
- **Primary method:** clinical trial (main study)
- **Temporal:** prospective (trials are prospective)
- **Analysis type:** replication
- **Label:** `clinical trial, replication, prospective`

### Example 5: Retrospective Case/Control GWAS
**Paper text:** "We retrospectively identified patients with drug-induced liver injury (cases) from electronic health records and matched controls. GWAS was performed on DNA samples."
- **Primary methods:** case/control (cases vs controls), GWAS (genome-wide)
- **Temporal:** retrospective (medical records)
- **Analysis type:** none
- **Label:** `case/control, GWAS, retrospective`

### Example 6: Pure GWAS
**Paper text:** "We performed genome-wide association analysis in 5,000 individuals to identify variants associated with drug response."
- **Primary method:** GWAS
- **Temporal:** typically not specified for pure GWAS
- **Analysis type:** none
- **Label:** `GWAS`

### Example 7: Family-Based Linkage with Trios
**Paper text:** "We analyzed 50 parent-offspring trios using linkage analysis to map pharmacogenomic loci."
- **Primary methods:** linkage, trios
- **Temporal:** not applicable
- **Analysis type:** none
- **Label:** `linkage, trios`

### Example 8: Complex Multi-Component Study
**Paper text:** "A retrospective cohort of 2,000 patients from a clinical trial database underwent GWAS. Findings were validated in two independent replication cohorts."
- **Primary methods:** cohort (retrospective analysis of trial), clinical trial (data source), GWAS
- **Temporal:** retrospective
- **Analysis type:** replication
- **Label:** `cohort, clinical trial, GWAS, retrospective, replication`
- **Note:** This is quite complex (5 components). Verify this level of complexity is accurate.

## Quality Checks

Before finalizing a study type label, verify:

1. **All terms are from the approved vocabulary** (see study_types.txt)
2. **Ordering follows convention** (primary → temporal → analysis)
3. **Combination is logical** (e.g., don't combine impossible designs)
4. **Label matches the paper's self-description** (if paper says "case-control study", label should include `case/control`)
5. **Most important design element is captured** (don't over-specify minor details)
6. **Temporal component is warranted** (only include if explicitly stated or clearly evident)

## Common Mistakes to Avoid

1. **Over-classification:** Not every detail needs to be captured
   - ❌ `cohort, case/control, GWAS, prospective, retrospective, meta-analysis, replication`
   - ✓ `cohort, GWAS, replication`

2. **Under-classification:** Missing important design elements
   - ❌ `cohort` (when paper explicitly describes GWAS component)
   - ✓ `cohort, GWAS`

3. **Wrong order:** Not following convention
   - ❌ `prospective, replication, cohort, GWAS`
   - ✓ `cohort, GWAS, prospective, replication`

4. **Using non-standard terms:**
   - ❌ `observational, genetic association`
   - ✓ `cohort, GWAS`

5. **Redundancy:**
   - ❌ `clinical trial, prospective` (prospective is implied)
   - ✓ `clinical trial` (unless paper specifically emphasizes prospective nature)

6. **Mixing method with analysis:**
   - ❌ `meta-analysis, systematic review` (redundant)
   - ✓ `meta-analysis`

## Summary Decision Tree

```
START
├─ Is this combining multiple studies?
│  ├─ YES → Include "meta-analysis"
│  └─ NO → Continue
├─ What is the PRIMARY METHOD?
│  ├─ Intervention assigned? → "clinical trial"
│  ├─ Cases vs controls compared? → "case/control"
│  ├─ Group followed over time? → "cohort"
│  ├─ Genome-wide testing? → "GWAS"
│  ├─ Descriptive series, no controls? → "case series"
│  ├─ Single timepoint measurement? → "cross sectional"
│  ├─ Family inheritance patterns? → "linkage"
│  ├─ Parent-offspring groups? → "trios"
│  └─ Multiple methods? → Include all relevant
├─ Is TEMPORAL component explicit?
│  ├─ Followed forward → Add "prospective"
│  ├─ Historical/existing data → Add "retrospective"
│  ├─ Both components → Add both
│  └─ Unclear/implicit → Omit
├─ Is this REPLICATING prior findings?
│  ├─ YES → Add "replication"
│  └─ NO → Done
└─ CONSTRUCT: [primary], [temporal], [analysis]
```

## Reference

For complete list of study type definitions, see: `docs/prompts/study_types.txt`

For frequency distribution, see: `persistent_data/study_type_counts.txt`

For implementation code, see: `src/study_parameters.py:94-117`
