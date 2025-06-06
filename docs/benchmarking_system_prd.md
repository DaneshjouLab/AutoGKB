# Language Model Benchmarking System for Pharmacogenomic Knowledge Extraction

## Product Requirements Document (PRD)

### 1. Overview

This document outlines the requirements for developing a benchmarking system to evaluate language model (LM) performance on extracting structured pharmacogenomic annotations from scientific articles.

### 2. Problem Statement

Currently, there is no standardized way to measure how effectively language models can extract complex pharmacogenomic relationships from scientific literature. The AutoGKB project has curated data that maps scientific articles to structured annotations, providing an opportunity to create a robust evaluation framework.

### 3. Objectives

- **Primary:** Create a comprehensive benchmarking system to evaluate LM extraction capabilities
- **Secondary:** Establish baseline performance metrics for current state-of-the-art models
- **Tertiary:** Enable iterative improvement of extraction models through standardized evaluation

### 4. Dataset Analysis

#### 4.1 Training Data Structure (train.jsonl)
- **Format:** JSONL with structured pharmacogenomic annotations
- **Key Fields:** 
  - Article metadata (pmcid, title, pmid)
  - Variant information (gene, variant_haplotypes, alleles)
  - Drug associations (drugs, multiple_drugs_and_or)
  - Clinical outcomes (phenotype_category, significance, direction_of_effect)
  - Population context (specialty_population, population_types, population_phenotypes_or_diseases)
  - Structured sentence representation with comparison groups

#### 4.2 Article Repository (data/articles/)
- **Format:** Markdown files with standardized structure
- **Content:** Full-text scientific articles from PMC
- **Metadata:** Embedded author, journal, DOI, PMID, PMCID information
- **Structure:** Title, abstract, and full article content

#### 4.3 Column Mapping (column_mapping.json)
- Maps database field names to human-readable descriptions
- Provides schema understanding for evaluation metrics

### 5. Functional Requirements

#### 5.1 Core Evaluation Framework

**FR-1: Text-to-Structured Extraction Evaluation**
- Input: Scientific article text (markdown format)
- Expected Output: Structured JSON matching training data schema
- Evaluation: Field-level accuracy, relationship extraction precision/recall

**FR-2: Multi-level Evaluation Metrics**
- **Entity Level:** Gene names, drug names, variant identifiers
- **Relationship Level:** Drug-gene associations, clinical outcomes
- **Semantic Level:** Direction of effect, significance assessment
- **Population Level:** Specialty populations, disease contexts

**FR-3: Partial Credit Scoring**
- Exact match scoring for categorical fields
- Semantic similarity scoring for free-text fields
- Hierarchical scoring for complex nested relationships

#### 5.2 Benchmark Tasks

**Task 1: Basic Entity Extraction**
- Extract genes, drugs, variants from article text
- Metrics: Precision, Recall, F1-score per entity type

**Task 2: Relationship Classification**
- Identify pharmacogenomic associations (significant/not significant)
- Classify direction of effect (increased/decreased/null)
- Metrics: Classification accuracy, confusion matrices

**Task 3: Structured Sentence Generation**
- Generate standardized sentences describing relationships
- Compare against gold standard sentences
- Metrics: BLEU, ROUGE, semantic similarity scores

**Task 4: Population Context Extraction**
- Identify specialty populations (Pediatric, etc.)
- Extract disease/phenotype contexts
- Metrics: Multi-label classification metrics

#### 5.3 Evaluation Infrastructure

**FR-4: Automated Evaluation Pipeline**
- Load articles and corresponding annotations
- Run LM inference on article content
- Compare outputs against gold standard
- Generate comprehensive evaluation reports

**FR-5: Model Comparison Framework**
- Support multiple LM architectures (GPT, Claude, Llama, etc.)
- Standardized prompting strategies
- Fair comparison methodologies

**FR-6: Error Analysis Tools**
- Categorize error types (missing entities, incorrect relationships)
- Provide detailed failure case analysis
- Generate improvement recommendations

### 6. Technical Requirements

#### 6.1 Input Processing
- Parse markdown articles to extract relevant text sections
- Handle article metadata extraction
- Support batch processing of multiple articles

#### 6.2 Output Validation
- Validate LM outputs against expected schema
- Handle malformed JSON responses
- Implement fallback parsing strategies

#### 6.3 Evaluation Metrics Implementation
- Exact string matching for categorical fields
- Fuzzy matching for drug/gene names (accounting for synonyms)
- Semantic embedding-based similarity for free-text fields
- Statistical significance testing for performance comparisons

#### 6.4 Reporting and Visualization
- Generate detailed evaluation reports (HTML/PDF)
- Create performance comparison dashboards
- Provide per-article and aggregate statistics

### 7. Data Requirements

#### 7.1 Evaluation Splits
- **Training Set:** For prompt development and model fine-tuning
- **Validation Set:** For hyperparameter tuning and model selection
- **Test Set:** For final evaluation and comparison

#### 7.2 Reference Standards
- Gold standard annotations from domain experts
- Inter-annotator agreement metrics
- Confidence scores for ambiguous cases

### 8. Performance Requirements

#### 8.1 Accuracy Targets
- **Entity Extraction:** >90% F1-score for genes and drugs
- **Relationship Classification:** >85% accuracy for significance determination
- **Overall Structured Output:** >80% field-level accuracy

#### 8.2 Processing Requirements
- Support evaluation of 100+ articles within reasonable time
- Parallel processing capabilities for multiple models
- Memory-efficient handling of large language models

### 9. Success Criteria

#### 9.1 Primary Success Metrics
- Comprehensive benchmark suite covering all annotation fields
- Baseline performance established for 3+ different LM families
- Reproducible evaluation methodology

#### 9.2 Secondary Success Metrics
- Error analysis reveals actionable improvement areas
- Performance differences between models are statistically significant
- Community adoption for standardized pharmacogenomic LM evaluation

### 10. Implementation Phases

#### Phase 1: Core Framework
- Basic entity extraction evaluation
- Simple relationship classification metrics
- Initial evaluation pipeline

#### Phase 2: Advanced Evaluation
- Complex relationship extraction
- Semantic similarity metrics
- Population context evaluation

#### Phase 3: Comprehensive Analysis
- Error categorization and analysis
- Model comparison tools
- Performance optimization recommendations

### 11. Dependencies

#### 11.1 Data Dependencies
- Access to complete article repository
- Validated annotation gold standards
- Column mapping configuration

#### 11.2 Technical Dependencies
- Language model APIs or local model hosting
- Evaluation metric libraries (scikit-learn, etc.)
- Text processing libraries
- Visualization frameworks

### 12. Risks and Mitigations

#### 12.1 Data Quality Risks
- **Risk:** Inconsistent annotation quality
- **Mitigation:** Implement annotation validation and quality checks

#### 12.2 Model Variability Risks
- **Risk:** Non-deterministic model outputs
- **Mitigation:** Multiple evaluation runs with statistical analysis

#### 12.3 Evaluation Bias Risks
- **Risk:** Overfitting evaluation to specific model strengths
- **Mitigation:** Diverse evaluation tasks and metrics

### 13. Future Considerations

- Integration with automated annotation pipelines
- Real-time evaluation capabilities
- Extension to other biomedical domains
- Community benchmark competitions

---

This PRD provides the foundation for developing a comprehensive language model benchmarking system that will enable systematic evaluation and improvement of pharmacogenomic knowledge extraction capabilities.