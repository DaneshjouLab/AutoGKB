# LLM-Based Article Annotation Method for Pharmacogenomic Variant Annotations

## Overview

This document outlines a comprehensive approach for using Large Language Models (LLMs) to extract structured pharmacogenomic variant annotations from biomedical articles. The method is designed to populate the AutoGKB variant annotation database with information about drug-gene interactions, variant effects, and clinical outcomes.

## Input and Output Structure

### Input
- **Article**: Markdown-formatted biomedical articles from PubMed Central (PMC)
- **Format**: Each article contains metadata (title, authors, PMID, PMCID, DOI) and full text content

### Output
Three types of structured annotations corresponding to TSV files:

1. **Functional Annotations (var_fa_ann.tsv)** - In vitro/molecular level effects
2. **Drug Annotations (var_drug_ann.tsv)** - Clinical drug response associations  
3. **Phenotype Annotations (var_pheno_ann.tsv)** - Disease/adverse event associations

Each annotation contains 20+ standardized fields including variant information, genes, drugs, phenotypes, population details, and comparison groups.

## Multi-Stage LLM Pipeline
### Stage 1: Annotation Determination
**Objective**: Determine what annotations make the most sense to include from the article
**Prompt Template**:
```
You are determining what type of annotations are appropritate for the article from the options of  to extract from a biomedical article. For the article determine the following:

Article: \n\n{article_text}\n\n

Articles get Variant Drug Annotations when they report associations between genetic variants and
pharmacological parameters or clinical drug response measures that specifically relate to:
Drug Annotations (var_drug_ann.tsv) include:

- Pharmacokinetic/Pharmacodynamic Parameters
- Clinical phenotypes/adverse events (Drug toxicity, organ dysfunction, treatment response phenotypes, disease outcomes when treated with drugs)

Articles get Variant Phenotype Annotations when they report associations between genetic variants and adverse drug reactions, toxicities, or clinical outcomes that represent:
- Toxicity/Safety outcomes
- Clinical phenotypes/adverse events

Articles get Variant Functional Annotations when they contain in vitro or mechanistic functional studies that directly measure how genetic variants affect:

- Enzyme/transporter activity (e.g., clearance, metabolism, transport)
- Binding affinity (e.g., protein-drug interactions)
- Functional properties (e.g., uptake rates, kinetic parameters like Km/Vmax)

The key distinction is mechanistic functional studies (gets var_fa_ann) vs clinical association studies (gets var_drug_ann or var_pheno_ann but not var_fa_ann).

Examples:

- "Cardiotoxicity when treated with anthracyclines" → var_pheno_ann
- "Decreased clearance of methotrexate" → var_drug_ann
- "Decreased enzyme activity in cell culture" → var_fa_ann
- "Variant affects drug clearance/response" —> var_drug_ann
- "Variant affects adverse events/toxicity outcomes" —> var_pheno_ann
- "Variant affects protein function in laboratory studies" —> var_fa_ann

Using this information, decide which out of the 3 annotations the article should receive with a one sentence summary reason along with a sentence/quote from the article that indicates why this is true.

Output Format:
Variant Drug Annotation: (Y/N)
Reason: (Reason)
Quote:(Quote)

Variant Phenotype Annotation: (Y/N)
Reason: (Reason)
Quote:(Quote)

Variant Functional Annotation: (Y/N)
Reason: (Reason)
Quote:(Quote)
```

TODO: Scrape this and get a structured output or create a structured ouput from this directly


### Stage 2A: Var Drug Tailored Article Summary

**Objective**: Summarize all the key information from an article necessary for a var_drug_ann entry

**Prompt Template**:
```
You are extracting pharmacogenomic information from a biomedical article. Identify and extract the following entities and their relationships:

Article: {article_text}

Extract:
METHODS SECTION:
- Briefly summarize the methods and results of the study

GENETIC VARIANTS (if present):
- SNP IDs (rs numbers)
  - For each SNP, capture:
    - Specific gene location
    - Variant type (missense, synonymous, etc.)
    - Potential functional impact on protein
    - Observed genotype frequencies
  - Explicitly link each genetic variant to:
    - Specific drug response
    - Changes in clinical outcomes
    - Mechanism of pharmacological interaction
- Gene names and symbols
- Variant/haplotype names (e.g., CYP2D6*4, *1/*2)
- Allele designations
- Genotype combinations
- If/how the variants affected the outcome of the study

DRUGS AND INTERVENTIONS:
- Drug names (generic and brand)
- Drug classes and categories
- Dosing information
- Treatment regimens

PHENOTYPES AND OUTCOMES:
- Clinical phenotypes
- Adverse events and toxicities
- Efficacy measures
- Pharmacokinetic parameters (clearance, metabolism, etc.)
- Disease conditions
- If/how the phenotypes affected the outcome of the study

POPULATION INFORMATION:
- Study population characteristics
- Demographics (age, ethnicity, gender)
- Sample sizes
- Inclusion/exclusion criteria

ASSOCIATIONS AND RELATIONSHIPS:
- Statistical associations between variants and outcomes
- Odds ratios, p-values, confidence intervals
- Comparative statements (increased/decreased effects)
- Causal relationships

Format your response as structured lists with clear entity types and associated context.

```
Notes: 
- The methods section right now is pretty good, it captures most of the information.
- Next is converting this to an extractable format

### Stage 3A: Extracting Drug Terms
This takes the raw articles --> drug terms
I think raw articles makes sense because we need quotes
```
You are an expert pharmacogenomics researcher reading and extracting annotations from the following article

\n\n{article_text}\n\n

These are the following terms for which we need to extract values:

Term: Variant/Haplotypes
- Content: The specific genetic variant mentioned in the study
- Manual Process: Look for SNP IDs (rs numbers), star alleles (CYP2D6*4), or genotype combinations
- Example: rs2909451, CYP2C19*1, CYP2C19*2, *1/*18

Term: Gene
- Content: Gene symbol associated with the variant
- Manual Process: Find the gene name near the variant mention, use standard HUGO symbols
- Example: DPP4, CYP2C19, KCNJ11

Term: Drug(s)
- Content: Generic drug name(s) studied
- Manual Process: Extract drug names from methods/results, use generic names, separate multiple drugs with commas
- Example: sitagliptin, clopidogrel, aspirin

Term: Phenotype Category
- Content: Type of clinical outcome studied
- Manual Process: Categorize based on what was measured:
    - Efficacy: Treatment response, clinical improvement
    - Metabolism/PK: Drug levels, clearance, half-life
    - Toxicity: Adverse events, side effects
    - Dosage: Dose requirements, dose adjustments
    - Other: Everything else
- Example: Efficacy (for HbA1c improvement study)

Term: Significance
- Content: Whether the association was statistically significant
- Manual Process: Look for p-values, confidence intervals:
    - yes: p < 0.05 or explicitly stated as significant
    - no: p ≥ 0.05 or stated as non-significant
    - not stated: No statistical testing mentioned
- Example: yes (P < .001 in sitagliptin study)

Term: Notes
- Content: Key study details, methodology, or important context
- Manual Process: Extract relevant quotes showing statistical results, study design, or important caveats
- Example: "Patients with the rs2909451 TT genotype in the study group exhibited a median HbA1c improvement of 0.57..."

Term: Standardized Sentence

- Content: Standardized description of the genetic association
- Manual Process: Write in format: "[Genotype/Allele] is [associated with/not associated with] [increased/decreased]
[outcome] [drug context] [population context]"
- Example: "Genotype TT is associated with decreased response to sitagliptin in people with Diabetes Mellitus, Type 2."

Term: Alleles

- Content: Specific allele or genotype if different from Variant/Haplotypes field
- Manual Process: Extract the exact genotype mentioned (AA, TT, CC, del/del, etc.)
- Example: TT, *1/*18, del/del

Term: Metabolizer types

- Content: CYP enzyme phenotype categories
- Manual Process: Look for metabolizer classifications in CYP studies:
    - poor metabolizer, intermediate metabolizer, extensive metabolizer, ultrarapid metabolizer
- Example: intermediate metabolizer

Term: Comparison Allele(s) or Genotype(s)

- Content: Reference genotype used for comparison
- Manual Process: Find what the study variant was compared against
- Example: *1/*1, C (for wild-type comparisons)

Term: Comparison Metabolizer types

- Content: Reference metabolizer status for comparison
- Manual Process: Extract the comparison metabolizer phenotype
- Example: normal metabolizer

Term: Specialty Population

- Content: Age-specific populations
- Manual Process: Check if study specifically focused on:
    - Pediatric: Children/adolescents
    - Geriatric: Elderly patients
    - Leave empty for general adult populations

Term: Population types
- Content: Descriptor of study population
- Manual Process: Look for population descriptors, usually "in people with" or ethnicity information
- Example: in people with

Term: Population Phenotypes or diseases
- Content: Disease/condition context with standardized prefix
- Manual Process: Find the medical condition studied, add appropriate prefix:
    - Disease: for established diseases
    - Other: for conditions/traits
    - Side Effect: for adverse events
- Example: Other:Diabetes Mellitus, Type 2

Term: isPlural
- Content: Grammar helper for sentence construction
- Manual Process: Use Is for singular subjects, Are for plural
- Example: Is

Term: Is/Is Not associated
- Content: Direction of association
- Manual Process: Determine if association was:
    - Associated with: Positive association found
    - Not associated with: No association found
- Example: Associated with

Term: Direction of effect

- Content: Whether the effect increases or decreases the outcome
- Manual Process: Look for directional language:
    - increased: Higher levels, better response, more effect
    - decreased: Lower levels, worse response, less effect
    - Leave empty if no clear direction
- Example: decreased

Term: PD/PK terms

- Content: Pharmacological outcome descriptor
- Manual Process: Extract the specific outcome measured:
    - response to, concentrations of, metabolism of, clearance of, dose of
- Example: response to

Term: Multiple drugs And/or

- Content: Logical connector for multiple drugs
- Manual Process: If multiple drugs mentioned:
    - and: All drugs together
    - or: Any of the drugs
    - Leave empty for single drug

Term: Multiple phenotypes or diseases And/or

- Content: Logical connector for multiple conditions
- Manual Process: Similar to drugs, use and/or for multiple conditions
- Leave empty for single condition

General recommended strategies

1. Scan for genetic variants: Look for "rs" numbers, gene names with asterisks, or phrases like "genotype," "allele,"
"polymorphism"
2. Identify drug context: Find drug names in methods, results, or discussion sections
3. Locate outcome measures: Look for clinical endpoints, lab values, response rates, adverse events
4. Find statistical associations: Search for p-values, odds ratios, significant differences between genotype groups
5. Extract population details: Note the study population, disease context, and inclusion criteria
6. Standardize the relationship: Convert the finding into the standardized sentence format following the association pattern

For each term, the output should be of the format:

Extracted Output: (output)
Reason: (one sentence justification)
Quote: (quote from the article that demonstrates why)
```

### Stage 3B: Extracting Pheno Terms
```
Phenotype Association Annotation Guidelines

Article: \n\n{article_text}\n\n


## Terms for Extraction

### Variant/Haplotypes
- **Content**: The specific genetic variant studied
- **Manual Process**: Extract SNP IDs (rs numbers), HLA alleles, star alleles, or genotype combinations
- **Example**: HLA-B*35:08, rs1801272, UGT1A1*1, UGT1A1*28

### Gene
- **Content**: Gene symbol associated with the variant
- **Manual Process**: Find the gene name near the variant mention
- **Example**: HLA-B, CYP2A6, UGT1A1

### Drug(s)
- **Content**: Drug(s) that caused or were involved in the phenotype
- **Manual Process**: 
  - Extract drug names that triggered the adverse event or phenotype
  - Leave empty for disease susceptibility studies without drug involvement
- **Example**: lamotrigine, sacituzumab govitecan, empty for disease predisposition

### Phenotype Category
- **Content**: Type of phenotype or outcome studied
- **Manual Process**: Categorize based on primary outcome:
  - Toxicity: Adverse drug reactions, side effects, drug-induced toxicity
  - Efficacy: Treatment response, therapeutic outcomes
  - Metabolism/PK: Pharmacokinetic parameters, drug levels
  - Dosage: Dose requirements, dose-response relationships
  - Other: Disease susceptibility, traits not directly drug-related
- **Example**: 
  - Toxicity (for Stevens-Johnson Syndrome)
  - Other (for alcoholism risk)

### Significance
- **Content**: Statistical significance of the association
- **Manual Process**: Look for p-values and statistical tests:
  - yes: p < 0.05 or stated as significant
  - no: p ≥ 0.05 or explicitly non-significant
  - not stated: No statistical testing reported
- **Example**: no (for non-significant HLA associations)

### Notes
- **Content**: Key study details, statistics, methodology
- **Manual Process**: Extract relevant quotes showing statistical results, case descriptions, or important context
- **Example**: "The allele was not significant when comparing allele frequency in cases..."

### Standardized Sentence
- **Content**: Standardized description of the genetic-phenotype association
- **Manual Process**: Write in format: "[Variant] is [associated with/not associated with] [increased/decreased] [phenotype outcome] [drug context] [population context]"
- **Example**: "HLA-B *35:08 is not associated with likelihood of Maculopapular Exanthema, severe cutaneous adverse reactions or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy."

### Alleles
- **Content**: Specific allele or genotype if different from main variant field
- **Manual Process**: Extract the exact genotype mentioned
- **Example**: *35:08, AA + AT, *1/*28 + *28/*28

### Specialty Population
- **Content**: Age-specific populations
- **Manual Process**: Identify if study focused on specific age groups:
  - Pediatric: Children/adolescents
  - Geriatric: Elderly patients
  - Leave empty for general adult populations
- **Example**: Pediatric (for children with Fanconi Anemia)

### Metabolizer Types
- **Content**: CYP enzyme phenotype when applicable
- **Manual Process**: Look for metabolizer classifications in CYP studies:
  - poor metabolizer
  - intermediate metabolizer
  - extensive metabolizer
  - ultrarapid metabolizer
  - deficiency
- **Example**: ultrarapid metabolizer, intermediate activity

### isPlural
- **Content**: Grammar helper for sentence construction
- **Manual Process**: Use Is for singular subjects, Are for plural
- **Example**: Is (for single allele), Are (for combined genotypes)

### Is/Is Not Associated
- **Content**: Direction of statistical association
- **Manual Process**: Determine association type:
  - Associated with: Positive association found
  - Not associated with: No association found
- **Example**: Not associated with, Associated with

### Direction of Effect
- **Content**: Whether the variant increases or decreases the phenotype
- **Manual Process**: Look for directional language:
  - increased: Higher risk, more severe, greater likelihood
  - decreased: Lower risk, less severe, reduced likelihood
  - Leave empty if no clear direction
- **Example**: 
  - increased (for higher toxicity risk)
  - decreased (for lower disease risk)

### Side Effect/Efficacy/Other
- **Content**: Specific phenotype outcome with standardized prefix
- **Manual Process**: Categorize the phenotype and add appropriate prefix:
  - Side Effect: for adverse drug reactions
  - Efficacy: for therapeutic outcomes
  - Disease: for disease conditions
  - Other: for other traits/conditions
  - PK: for pharmacokinetic measures
- **Example**: 
  - Side Effect:Stevens-Johnson Syndrome
  - Disease:Alcohol abuse
  - Other:Medication adherence

### When Treated With/Exposed To/When Assayed With
- **Content**: Drug administration context
- **Manual Process**: Use standard phrases:
  - when treated with: For therapeutic drug administration
  - when exposed to: For environmental or non-therapeutic exposure
  - due to: For substance-related disorders
  - Leave empty for non-drug phenotypes
- **Example**: when treated with, due to (for substance abuse)

### Multiple Drugs And/Or
- **Content**: Logical connector for multiple drugs
- **Manual Process**: If multiple drugs involved:
  - and: Combination therapy
  - or: Any of the drugs
  - Leave empty for single drug
- **Example**: or (for any of several drugs)

### Population Types
- **Content**: Description of study population
- **Manual Process**: Look for population descriptors:
  - in people with: General population with condition
  - in children with: Pediatric population
  - in women with: Gender-specific population
- **Example**: in people with, in children with

### Population Phenotypes or Diseases
- **Content**: Disease/condition context with prefix
- **Manual Process**: Find the medical condition and add prefix:
  - Disease: for established diseases
  - Other: for conditions/traits
- **Example**: 
  - Disease:Epilepsy
  - Other:Diabetes Mellitus, Type 2

### Multiple Phenotypes or Diseases And/Or
- **Content**: Logical connector for multiple conditions
- **Manual Process**: Use and/or for multiple disease contexts
- **Example**: and (for multiple comorbidities)

### Comparison Allele(s) or Genotype(s)
- **Content**: Reference genotype for comparison
- **Manual Process**: Find what the variant was compared against
- **Example**: TT (wild-type), *1/*1 (normal function allele)

### Comparison Metabolizer Types
- **Content**: Reference metabolizer phenotype
- **Manual Process**: Extract comparison metabolizer status
- **Example**: normal metabolizer

## General Strategy Recommendations

1. **Identify Phenotype Outcomes**: Look for adverse events, toxicities, disease conditions, clinical traits
2. **Find Genetic Associations**: Search for variants linked to the phenotype (may or may not involve drugs)
3. **Determine Drug Involvement**: Check if phenotype is drug-induced or related to disease susceptibility
4. **Extract Statistical Evidence**: Look for odds ratios, p-values, case reports, frequency differences
5. **Categorize Phenotype Type**: Classify as toxicity, efficacy, disease susceptibility, or other trait
6. **Note Population Context**: Identify specific patient populations, age groups, disease conditions
7. **Standardize the Relationship**: Convert findings into standardized sentence format describing the genetic-phenotype association

For each term, the output should be of the format:

Extracted Output: (output)
Reason: (one sentence justification)
Quote: (quote from the article that demonstrates why)
```

### Stage 3C: Extracting FA Terms
```
# Functional Annotation Guidelines

## Terms for Extraction

### Variant/Haplotypes
- **Content**: The specific genetic variant studied
- **Manual Process**: Extract variant names, star alleles, SNP IDs, or protein constructs tested
- **Example**: CYP2C19*1, CYP2C19*17, rs72552763, CYP2B6*1, CYP2B6*6

### Gene
- **Content**: Gene symbol associated with the variant
- **Manual Process**: Identify the gene being studied functionally
- **Example**: CYP2C19, CYP2B6, SLC22A1

### Drug(s)
- **Content**: Substrate or compound used in the functional assay
- **Manual Process**: Extract the drug/substrate used to test enzyme activity or transport
- **Example**: normeperidine, bupropion, warfarin, voriconazole

### Phenotype Category
- **Content**: Type of functional outcome measured
- **Manual Process**: Categorize based on what was measured:
  - Metabolism/PK: Enzyme activity, clearance, transport, binding affinity
  - Efficacy: Functional response in cellular systems
  - Leave empty for basic biochemical studies
- **Example**: 
  - Metabolism/PK (for enzyme kinetics)
  - Efficacy (for cellular response)

### Significance
- **Content**: Statistical significance of functional differences
- **Manual Process**: Look for statistical comparisons:
  - yes: Significant differences in activity/function
  - no: No significant differences
  - not stated: No statistical testing reported
- **Example**: 
  - yes (for significant activity differences)
  - not stated (for descriptive studies)

### Notes
- **Content**: Key experimental details, methodology, quantitative results
- **Manual Process**: Extract relevant quotes showing experimental conditions, numerical results, or important technical details
- **Example**: "Clearance was 26.57% of wild-type. CYP2C19 variants expressed in Sf21 insect cells..."

### Standardized Sentence
- **Content**: Standardized description of the functional relationship
- **Manual Process**: Write in format: "[Variant] is associated with [increased/decreased] [functional outcome] [experimental context] as compared to [reference variant]"
- **Example**: "CYP2C19 *17/*17 is associated with increased formation of normeperidine as compared to CYP2C19 *1/*1 + *1/*17."

### Alleles
- **Content**: Specific allele or genotype tested
- **Manual Process**: Extract the exact variant designation
- **Example**: *17/*17, *1/*1, del, A

### Metabolizer Types
- **Content**: Phenotype classification if applicable
- **Manual Process**: Rarely used in functional studies; mainly for CYP phenotyping
- **Example**: Usually empty

### Comparison Allele(s) or Genotype(s)
- **Content**: Reference variant for comparison
- **Manual Process**: Find the control/wild-type variant used for comparison
- **Example**: *1/*1 + *1/*17, *1, GAT

### Comparison Metabolizer Types
- **Content**: Reference metabolizer status
- **Manual Process**: Usually empty for functional studies
- **Example**: Usually empty

### Assay Type
- **Content**: Laboratory method or experimental system used
- **Manual Process**: Extract the specific assay methodology:
  - in human liver microsomes: Microsomal enzyme assays
  - hydroxylation assay: Specific metabolic pathway assays
  - crystal structure prediction: Computational modeling
  - Leave empty if not specified
- **Example**: 
  - in human liver microsomes
  - hydroxylation assay
  - crystal structure prediction

### Cell Type
- **Content**: Cell line or tissue system used for the assay
- **Manual Process**: Extract the specific cellular context:
  - 293FT cells: Human embryonic kidney cells
  - COS-7 cells: Monkey kidney cells
  - Sf21 insect cells: Insect cells for baculovirus expression
  - in insect microsomes: Microsomal preparations
  - expressed in [cell type]: Heterologous expression systems
- **Example**: 
  - in 293FT cells
  - expressed in COS-7 cells

### Specialty Population
- **Content**: Age-specific populations (rarely applicable to functional studies)
- **Manual Process**: Usually leave empty for in vitro studies
- **Example**: Usually empty

### isPlural
- **Content**: Grammar helper for sentence construction
- **Manual Process**: Use Is for singular subjects, Are for plural
- **Example**: Is

### Is/Is Not Associated
- **Content**: Direction of functional association
- **Manual Process**: Determine association type:
  - Associated with: Functional difference observed
  - Not associated with: No functional difference
- **Example**: Associated with

### Direction of Effect
- **Content**: Whether the variant increases or decreases function
- **Manual Process**: Look for directional language:
  - increased: Higher activity, better function, enhanced capability
  - decreased: Lower activity, reduced function, impaired capability
- **Example**: 
  - increased (for enhanced activity)
  - decreased (for reduced activity)

### Functional Terms
- **Content**: Specific functional outcome measured
- **Manual Process**: Extract the precise functional parameter:
  - activity of: Enzyme activity measurements
  - clearance of: Drug clearance kinetics
  - formation of: Metabolite formation
  - transport of: Transporter function
  - affinity to: Binding affinity
  - catalytic activity of: Catalytic efficiency
- **Example**: 
  - formation of
  - activity of
  - clearance of

### Gene/Gene Product
- **Content**: Specific gene or protein being functionally assessed
- **Manual Process**: Extract the gene symbol when the functional term relates to gene product activity
- **Example**: CYP2C19, CYP2B6, CYP2C9

### When Treated With/Exposed To/When Assayed With
- **Content**: Experimental substrate context
- **Manual Process**: Use standard phrases for functional assays:
  - when assayed with: For enzyme activity assays
  - of: For direct metabolite measurements
  - Leave empty for non-substrate specific functions
- **Example**: 
  - when assayed with
  - of

### Multiple Drugs And/Or
- **Content**: Logical connector for multiple substrates
- **Manual Process**: If multiple substrates tested:
  - and: Combination substrate assays
  - or: Alternative substrate assays
  - Leave empty for single substrate
- **Example**: or (for alternative substrates)

## Manual Reading Strategy for Functional Annotations

1. **Identify Experimental System**: Look for cell lines, microsomes, expression systems, computational models
2. **Find Functional Readouts**: Search for enzyme activity, kinetic parameters, binding affinity, transport rates
3. **Extract Substrate Information**: Identify the drug/compound used to test function
4. **Locate Comparison Data**: Find reference variants (usually wild-type or *1 alleles) for comparison
5. **Quantify Functional Changes**: Look for fold-changes, percentages, kinetic parameters (Km, Vmax, clearance)
6. **Note Experimental Conditions**: Extract assay conditions, expression systems, substrate concentrations
7. **Standardize the Relationship**: Convert findings into standardized sentence format describing the functional difference

## Key Differences from Clinical Annotations

- **Laboratory-based**: In vitro studies rather than patient studies
- **Mechanistic Focus**: How variants affect protein function rather than clinical outcomes
- **Quantitative Measures**: Enzyme kinetics, binding constants, activity percentages
- **Controlled Conditions**: Defined experimental systems rather than clinical populations
- **Substrate-specific**: Effects measured with specific drugs/compounds as substrates

**Purpose**: Functional annotations provide the mechanistic basis for understanding why certain variants affect drug response in patients - they show how genetic changes alter protein function at the molecular level.

For each term, the output should be of the format:

Extracted Output: (output)
Reason: (one sentence justification)
Quote: (sentence from the article that demonstrates why)
```

### Extract Association for Single Variant
```
Article: \n\n{article_text}\n\n

For the variant {variant_id}, determine what type of association(s) is being studied by the article. The options are Drug, Phenotype, and Functional.

A variant has a Drug association when the article reports associations between the genetic variant and
pharmacological parameters or clinical drug response measures that specifically relate to:
- Pharmacokinetic/Pharmacodynamic Parameters
- Clinical phenotypes/adverse events (Drug toxicity, organ dysfunction, treatment response phenotypes, disease outcomes when treated with drugs)

A variant has a Phenotype association when the article reports associations between genetic variants and adverse drug reactions, toxicities, or clinical outcomes that represent:
- Toxicity/Safety outcomes
- Clinical phenotypes/adverse events

A variant has a Functional association when the article contains in vitro or mechanistic functional studies that directly measure how the variant affects:
- Enzyme/transporter activity (e.g., clearance, metabolism, transport)
- Binding affinity (e.g., protein-drug interactions)
- Functional properties (e.g., uptake rates, kinetic parameters like Km/Vmax)

The key distinction is mechanistic functional studies typically get Functional associations vs clinical association studies get Phenotype and Drug associations but Functional.
Examples:
- "Cardiotoxicity when treated with anthracyclines" → Phenotype
- "Decreased clearance of methotrexate" → Drug
- "Decreased enzyme activity in cell culture" → Functional
- "Variant affects drug clearance/response" —> Drug
- "Variant affects adverse events/toxicity outcomes" —> Phenotype
- "Variant affects protein function in laboratory studies" —> Functional

Using this information, decide which out of the 3 annotations the variant should receive with a one sentence summary explanation for the decision along with a sentence/quote from the article that indicates why this is true. It is possible there is more than one Annotation/association per variant

Output Format:
Variant Drug Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Phenotype Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Functional Association: (Y/N)
Explanation: (Reason)
```