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

### Stage 1: Article Relevance Screening

**Objective**: Determine if the article contains pharmacogenomic variant information worthy of annotation.

**Prompt Template**:
```
You are a pharmacogenomics expert reviewing biomedical literature. Analyze this article and determine if it contains information about genetic variants and their associations with drug response, metabolism, toxicity, or disease phenotypes.

Article Title: {title}
Article Text: {article_text}

Does this article contain:
1. Specific genetic variants (SNPs, haplotypes, alleles)?
2. Drug names or therapeutic interventions?
3. Clinical outcomes, drug responses, or phenotypic associations?
4. Population or patient cohort data?

Respond with: RELEVANT or NOT_RELEVANT
If RELEVANT, provide a brief 2-3 sentence summary of the key pharmacogenomic findings.
```

### Stage 2: Entity Extraction and Relationship Identification

**Objective**: Extract all relevant pharmacogenomic entities and their relationships from the article.

**Prompt Template**:
```
You are extracting pharmacogenomic information from a biomedial article. Identify and extract the following entities and their relationships:

Article: {article_text}

Extract:

GENETIC VARIANTS:
- SNP IDs (rs numbers)
- Gene names and symbols
- Variant/haplotype names (e.g., CYP2D6*4, *1/*2)
- Allele designations
- Genotype combinations

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

### Stage 3: Annotation Type Classification

**Objective**: Determine which type(s) of annotations should be created for each variant-outcome relationship.

**Prompt Template**:
```
Based on the extracted entities and relationships, classify each variant-outcome association into annotation categories:

Extracted Relationships: {relationships}

Classification Rules:
- FUNCTIONAL ANNOTATION: In vitro studies, enzyme activity, protein expression, cellular assays, metabolism studies
- DRUG ANNOTATION: Clinical drug response, efficacy, dosing, therapeutic outcomes in patients
- PHENOTYPE ANNOTATION: Adverse events, toxicity, disease susceptibility, clinical phenotypes

For each relationship, specify:
1. Annotation type(s) applicable
2. Confidence level (high/medium/low)
3. Key evidence supporting the classification

Output format: 
Relationship ID | Annotation Type(s) | Confidence | Evidence Summary
```

### Stage 4: Schema-Specific Row Generation

**Objective**: Generate complete TSV row entries matching the exact database schema.

#### 4.1 Functional Annotation Row Generation (var_fa_ann.tsv)

**Prompt Template**:
```
Generate a complete functional annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

Article PMID: {pmid}
Relationship: {relationship_description}
Relevant Text: {supporting_sentence}

REQUIRED OUTPUT FORMAT - Tab-separated values in this exact order:

Variant Annotation ID: [Generate unique ID: concatenate timestamp + random numbers]
Variant/Haplotypes: [Exact variant notation, e.g., "CYP2C19*1, CYP2C19*2" or "rs1234567"]
Gene: [Gene symbol only, e.g., "CYP2C19"]
Drug(s): [Generic drug name(s), e.g., "warfarin" or "clopidogrel, aspirin"]
PMID: [{pmid}]
Phenotype Category: [EXACTLY ONE: "Metabolism/PK", "Efficacy", "Toxicity", "Dosage", "Other"]
Significance: [EXACTLY ONE: "yes", "no", "not stated"]
Notes: [Brief context or methodology, e.g., "in vitro expression study"]
Sentence: [Complete supporting sentence from article that describes the association]
Alleles: [Specific allele if different from Variant/Haplotypes, or empty]
Specialty Population: [EXACTLY ONE: "Pediatric", "Geriatric", or leave empty]
Assay type: [Laboratory method, e.g., "yeast microsomes", "human liver microsomes"]
Metabolizer types: [If applicable: "poor metabolizer", "intermediate metabolizer", etc.]
isPlural: [Leave empty - automatically determined]
Is/Is Not associated: [EXACTLY ONE: "Is", "Is Not", "Are", "Are Not"]
Direction of effect: [EXACTLY ONE: "increased", "decreased", or empty if no direction]
Functional terms: [Specific functional outcome, e.g., "activity of", "metabolism of", "clearance of"]
Gene/gene product: [Gene symbol if functional term relates to gene product]
When treated with/exposed to/when assayed with: [Drug context if applicable]
Multiple drugs And/or: [EXACTLY ONE: "and", "or", or empty]
Cell type: [If in vitro study, specify cell type]
Comparison Allele(s) or Genotype(s): [Reference genotype for comparison]
Comparison Metabolizer types: [Reference metabolizer status if applicable]

OUTPUT EXACTLY ONE TAB-SEPARATED ROW with all fields filled or empty as appropriate.
Example output format:
1451148445	CYP2C19*1, CYP2C19*17	CYP2C19	normeperidine	30902024	Metabolism/PK	not stated	In other in vitro experiments...	CYP2C19 *17/*17 is associated with increased formation of normeperidine as compared to CYP2C19 *1/*1 + *1/*17.	*17/*17		in human liver microsomes		Is	Associated with	increased	formation of					*1/*1 + *1/*17	
```

#### 4.2 Drug Annotation Row Generation (var_drug_ann.tsv)

**Prompt Template**:
```
Generate a complete drug annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

Article PMID: {pmid}
Relationship: {relationship_description}
Relevant Text: {supporting_sentence}

REQUIRED OUTPUT FORMAT - Tab-separated values in this exact order:

Variant Annotation ID: [Generate unique ID]
Variant/Haplotypes: [Exact variant notation]
Gene: [Gene symbol only]
Drug(s): [Generic drug name(s)]
PMID: [{pmid}]
Phenotype Category: [EXACTLY ONE: "Metabolism/PK", "Efficacy", "Toxicity", "Dosage", "Other"]
Significance: [EXACTLY ONE: "yes", "no", "not stated"]
Notes: [Clinical context or study details]
Sentence: [Complete supporting sentence from article]
Alleles: [Specific allele if different from Variant/Haplotypes, or empty]
Specialty Population: [EXACTLY ONE: "Pediatric", "Geriatric", or empty]
Metabolizer types: [If applicable: metabolizer status]
isPlural: [Leave empty]
Is/Is Not associated: [EXACTLY ONE: "Is", "Is Not", "Are", "Are Not"]
Direction of effect: [EXACTLY ONE: "increased", "decreased", or empty]
PD/PK terms: [Pharmacokinetic/pharmacodynamic outcome, e.g., "concentrations of", "response to"]
Multiple drugs And/or: [EXACTLY ONE: "and", "or", or empty]
Population types: [Ethnicity/ancestry if specified]
Population Phenotypes or diseases: [Disease with prefix: "Disease:", "Other:", "Side Effect:"]
Multiple phenotypes or diseases And/or: [EXACTLY ONE: "and", "or", or empty]
Comparison Allele(s) or Genotype(s): [Reference genotype]
Comparison Metabolizer types: [Reference metabolizer status]

OUTPUT EXACTLY ONE TAB-SEPARATED ROW.
Example output format:
1451834452	CYP3A4*1, CYP3A4*17	CYP3A4	nifedipine	15634941	Other, Metabolism/PK	not stated	in vitro expression...	CYP3A4 *17 is associated with decreased metabolism of nifedipine as compared to CYP3A4 *1.	*17			Is	Associated with	decreased	metabolism of					*1	
```

#### 4.3 Phenotype Annotation Row Generation (var_pheno_ann.tsv)

**Prompt Template**:
```
Generate a complete phenotype annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

Article PMID: {pmid}
Relationship: {relationship_description}
Relevant Text: {supporting_sentence}

REQUIRED OUTPUT FORMAT - Tab-separated values in this exact order:

Variant Annotation ID: [Generate unique ID]
Variant/Haplotypes: [Exact variant notation]
Gene: [Gene symbol only]
Drug(s): [Generic drug name(s)]
PMID: [{pmid}]
Phenotype Category: [EXACTLY ONE: "Metabolism/PK", "Efficacy", "Toxicity", "Dosage", "Other"]
Significance: [EXACTLY ONE: "yes", "no", "not stated"]
Notes: [Clinical context]
Sentence: [Complete supporting sentence from article]
Alleles: [Specific allele if different, or empty]
Specialty Population: [EXACTLY ONE: "Pediatric", "Geriatric", or empty]
Metabolizer types: [If applicable]
isPlural: [Leave empty]
Is/Is Not associated: [EXACTLY ONE: "Is", "Is Not", "Are", "Are Not"]
Direction of effect: [EXACTLY ONE: "increased", "decreased", or empty]
Side effect/efficacy/other: [Specific phenotype outcome with prefix: "Side Effect:", "Efficacy:", "Other:"]
Phenotype: [Primary phenotype, e.g., "Neutropenia", "Stevens-Johnson Syndrome"]
Multiple phenotypes And/or: [EXACTLY ONE: "and", "or", or empty]
When treated with/exposed to/when assayed with: [Drug context]
Multiple drugs And/or: [EXACTLY ONE: "and", "or", or empty]
Population types: [Ethnicity if specified]
Population Phenotypes or diseases: [Disease context with prefix]
Multiple phenotypes or diseases And/or: [EXACTLY ONE: "and", "or", or empty]
Comparison Allele(s) or Genotype(s): [Reference genotype]
Comparison Metabolizer types: [Reference metabolizer status]

OUTPUT EXACTLY ONE TAB-SEPARATED ROW.
Example output format:
1449169911	HLA-B*35:08	HLA-B	lamotrigine	29238301	Toxicity	no	The allele was not significant...	HLA-B *35:08 is not associated with likelihood of Maculopapular Exanthema, severe cutaneous adverse reactions or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy.	*35:08			Is	Not associated with		likelihood of	Side Effect:Maculopapular Exanthema, Side Effect:Severe Cutaneous Adverse Reactions, Side Effect:Stevens-Johnson Syndrome	or	when treated with		in people with	Disease:Epilepsy			
```

#### 4.4 Quality Control and Validation

**Prompt Template**:
```
Review this generated annotation row and validate it meets the schema requirements:

Generated Row: {annotation_row}
Source Article Excerpt: {relevant_text}
Expected Schema: {schema_fields}

Validation Checklist:
1. Are ALL required fields present in correct order?
2. Do controlled vocabulary fields use exact allowed values?
3. Is the variant notation standardized?
4. Are drug names generic/standard?
5. Does the sentence directly support the association?
6. Are comparison groups appropriate?
7. Is the statistical significance correctly interpreted?

Output:
- VALID or INVALID
- List specific corrections needed
- Corrected row if invalid
```

### Stage 5: Multi-Row Batch Processing

**Objective**: Process articles that contain multiple variant-outcome relationships efficiently.

**Prompt Template**:
```
This article contains multiple pharmacogenomic relationships. Generate separate annotation rows for each relationship.

Article PMID: {pmid}
Article Text: {full_article}

For each distinct variant-drug-outcome relationship found:
1. Determine annotation type (functional/drug/phenotype)
2. Generate complete TSV row following the appropriate schema
3. Ensure unique Variant Annotation IDs
4. Maintain consistency in variant nomenclature across rows

Output format:
ANNOTATION_TYPE: [functional/drug/phenotype]
ROW: [complete tab-separated row]

ANNOTATION_TYPE: [functional/drug/phenotype]  
ROW: [complete tab-separated row]

[Continue for all relationships found]

Ensure no duplicate relationships and complete coverage of annotatable findings.
```

## Implementation Strategy

### Phase 1: Schema Integration and Prompt Testing
1. Create detailed field-level documentation with examples from existing data
2. Test prompts with sample articles that have manual annotations
3. Validate output format compatibility with TSV import processes
4. Refine controlled vocabulary lists and standardization rules

### Phase 2: Row-Level Validation Pipeline  
1. Implement automated schema validation for generated rows
2. Create field-specific validation rules (e.g., PMID format, controlled vocabularies)
3. Build consistency checks across related annotations
4. Develop confidence scoring for generated rows

### Phase 3: Batch Processing and Error Handling
1. Implement parallel processing for multiple articles
2. Create error recovery for malformed outputs
3. Build retry logic for low-confidence annotations
4. Develop human review queues for validation

### Phase 4: Database Integration
1. Create direct TSV import pipelines
2. Implement deduplication logic at database level
3. Build update mechanisms for revised annotations
4. Create audit trails for annotation provenance

## Quality Control Measures

### Automated Row Validation
- Field count and order verification
- Controlled vocabulary compliance checking
- Cross-reference validation (PMIDs, variant IDs, drug names)
- Statistical measures plausibility checks

### Schema Compliance Monitoring
- Real-time validation during generation
- Rejection of malformed rows with specific error messages
- Automatic retry with corrected prompts
- Escalation to human review for persistent failures

### Consistency Enforcement
- Variant nomenclature standardization across all rows
- Drug name normalization to generic forms
- Population and phenotype term standardization
- Cross-annotation relationship validation

## Expected Challenges and Mitigation Strategies

### Challenge 1: Complex Multi-Field Dependencies
**Mitigation**: Use step-by-step field completion with intermediate validation checkpoints in prompts.

### Challenge 2: Controlled Vocabulary Adherence
**Mitigation**: Provide comprehensive allowed value lists in prompts and implement strict post-processing validation.

### Challenge 3: Tab-Separated Format Issues
**Mitigation**: Use explicit field delimiters and implement robust parsing with error detection.

### Challenge 4: Unique ID Generation
**Mitigation**: Implement deterministic ID generation based on content hash to avoid duplicates.

### Challenge 5: Multi-Row Consistency
**Mitigation**: Process all relationships from an article in single LLM call to maintain consistency.

## Success Metrics

### Schema Compliance
- Percentage of generated rows meeting exact schema requirements
- Field completion rates across different annotation types
- Controlled vocabulary adherence rates

### Data Quality
- Accuracy of extracted variant-outcome relationships
- Consistency of annotations across multiple extractions
- Completeness of captured relationships per article

### Processing Efficiency
- Successful row generation rate per article
- Time to generate complete annotation sets
- Human review intervention rates

This schema-focused approach ensures that LLM outputs can be directly imported into the database structure while maintaining high data quality and consistency standards.