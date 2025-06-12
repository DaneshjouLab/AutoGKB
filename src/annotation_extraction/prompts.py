"""
Prompt templates for the LLM annotation pipeline.
"""

from typing import Dict, Any


class PromptTemplates:
    """Container for all prompt templates used in the pipeline."""

    VAR_DRUG_SUMMARY = """

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

"""
    
    RELEVANCE_SCREENING = """
You are a pharmacogenomics expert reviewing biomedical literature. Analyze this article and determine if it contains information about genetic variants and their associations with drug response, metabolism, toxicity, or disease phenotypes.

Article Title: {title}
Article Text: {article_text}

Does this article contain:
1. Specific genetic variants (SNPs, haplotypes, alleles)?
2. Drug names or therapeutic interventions?
3. Clinical outcomes, drug responses, or phenotypic associations?
4. Population or patient cohort data?

Respond with: RELEVANT or NOT_RELEVANT
If RELEVANT, provide a brief 2-3 sentence summary of the key pharmacogenomic findings."""

    ENTITY_EXTRACTION = """
You are extracting pharmacogenomic information from a biomedical article. Identify and extract the following entities and their relationships:

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

Format your response as structured lists with clear entity types and associated context."""

    ANNOTATION_CLASSIFICATION = """
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
Relationship ID | Annotation Type(s) | Confidence | Evidence Summary"""

    FUNCTIONAL_ANNOTATION_GENERATION = """Generate a complete functional annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

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

OUTPUT EXACTLY ONE TAB-SEPARATED ROW with all fields filled or empty as appropriate."""

    DRUG_ANNOTATION_GENERATION = """Generate a complete drug annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

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

OUTPUT EXACTLY ONE TAB-SEPARATED ROW."""

    PHENOTYPE_ANNOTATION_GENERATION = """Generate a complete phenotype annotation row for this pharmacogenomic relationship. You must fill ALL fields according to the exact schema below.

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

OUTPUT EXACTLY ONE TAB-SEPARATED ROW."""

    QUALITY_VALIDATION = """Review this generated annotation row and validate it meets the schema requirements:

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
- Corrected row if invalid"""

    BATCH_PROCESSING = """
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

Ensure no duplicate relationships and complete coverage of annotatable findings."""

    @classmethod
    def format_prompt(cls, template: str, **kwargs) -> str:
        """Format a prompt template with provided parameters."""
        return template.format(**kwargs)