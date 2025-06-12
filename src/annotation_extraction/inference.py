"""
Individual stages of the annotation extraction pipeline.
"""

import re
import time
import random
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from litellm import completion
from loguru import logger

from .models import (
    ArticleInput, RelevanceResult, ExtractedEntities, ExtractedEntity,
    ClassificationResult, AnnotationRow, ValidationResult, Relationship,
    AnnotationType, PhenotypeCategory, Significance, Association, Direction
)
from .prompts import PromptTemplates


class LLMInterface(ABC):
    """Abstract interface for LLM interactions."""
    
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Generate response from LLM."""
        pass

class ModelConfig:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

class RelevanceScreener:
    """Stage 1: Determines if article contains relevant pharmacogenomic content."""
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm
    
    def screen_article(self, article: ArticleInput) -> RelevanceResult:
        """Screen article for pharmacogenomic relevance."""
        prompt = PromptTemplates.format_prompt(
            PromptTemplates.RELEVANCE_SCREENING,
            title=article.title,
            article_text=article.article_text
        )
        
        response = self.llm.generate(prompt, temperature=0.1)
        
        # Parse response
        lines = response.strip().split('\n')
        first_line = lines[0].strip().upper()
        
        is_relevant = first_line == "RELEVANT"
        summary = None
        
        if is_relevant and len(lines) > 1:
            summary = '\n'.join(lines[1:]).strip()
        
        return RelevanceResult(is_relevant=is_relevant, summary=summary)


class EntityExtractor:
    """Stage 2: Extracts pharmacogenomic entities and relationships."""
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm
    
    def extract_entities(self, article: ArticleInput) -> ExtractedEntities:
        """Extract all relevant entities from article."""
        prompt = PromptTemplates.format_prompt(
            PromptTemplates.ENTITY_EXTRACTION,
            article_text=article.article_text
        )
        
        response = self.llm.generate(prompt, temperature=0.2)
        
        # Parse the structured response
        entities = self._parse_entity_response(response)
        
        return entities
    
    def _parse_entity_response(self, response: str) -> ExtractedEntities:
        """Parse LLM response into structured entities."""
        sections = {
            'GENETIC VARIANTS:': [],
            'DRUGS AND INTERVENTIONS:': [],
            'PHENOTYPES AND OUTCOMES:': [],
            'POPULATION INFORMATION:': [],
            'ASSOCIATIONS AND RELATIONSHIPS:': []
        }
        
        current_section = None
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line in sections:
                current_section = line
            elif current_section and line.startswith('- '):
                entity_text = line[2:].strip()
                entity = ExtractedEntity(
                    entity_type=current_section.replace(':', '').strip(),
                    value=entity_text,
                    context="",
                    supporting_text=entity_text
                )
                sections[current_section].append(entity)
        
        return ExtractedEntities(
            genetic_variants=sections['GENETIC VARIANTS:'],
            drugs=sections['DRUGS AND INTERVENTIONS:'],
            phenotypes=sections['PHENOTYPES AND OUTCOMES:'],
            population_info=sections['POPULATION INFORMATION:'],
            associations=sections['ASSOCIATIONS AND RELATIONSHIPS:']
        )


class AnnotationClassifier:
    """Stage 3: Classifies relationships into annotation types."""
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm
    
    def classify_relationships(self, entities: ExtractedEntities, article: ArticleInput) -> List[ClassificationResult]:
        """Classify each relationship into annotation types."""
        # Create relationships from associations
        relationships = self._create_relationships(entities, article)
        
        if not relationships:
            return []
        
        # Format relationships for classification
        relationships_text = self._format_relationships_for_prompt(relationships)
        
        prompt = PromptTemplates.format_prompt(
            PromptTemplates.ANNOTATION_CLASSIFICATION,
            relationships=relationships_text
        )
        
        response = self.llm.generate(prompt, temperature=0.1)
        
        # Parse classification results
        return self._parse_classification_response(response, relationships)
    
    def _create_relationships(self, entities: ExtractedEntities, article: ArticleInput) -> List[Relationship]:
        """Create relationships from extracted entities."""
        relationships = []
        
        # Simple heuristic: pair variants with drugs and phenotypes
        for variant in entities.genetic_variants:
            # Extract gene from variant
            gene = self._extract_gene_from_variant(variant.value)
            
            for drug in entities.drugs:
                for phenotype in entities.phenotypes:
                    relationship = Relationship(
                        variant=variant.value,
                        gene=gene,
                        drug=drug.value,
                        phenotype=phenotype.value,
                        association_type="association",
                        evidence_text=f"{variant.supporting_text} {drug.supporting_text} {phenotype.supporting_text}",
                        statistical_measures=None
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _extract_gene_from_variant(self, variant_text: str) -> str:
        """Extract gene symbol from variant notation."""
        # Look for gene symbols (e.g., CYP2D6 from CYP2D6*4)
        gene_pattern = r'([A-Z][A-Z0-9]+)(?:\*|\s|$)'
        match = re.search(gene_pattern, variant_text)
        return match.group(1) if match else ""
    
    def _format_relationships_for_prompt(self, relationships: List[Relationship]) -> str:
        """Format relationships for classification prompt."""
        formatted = []
        for i, rel in enumerate(relationships):
            formatted.append(f"{i+1}. {rel.variant} ({rel.gene}) - {rel.drug} - {rel.phenotype}")
        return '\n'.join(formatted)
    
    def _parse_classification_response(self, response: str, relationships: List[Relationship]) -> List[ClassificationResult]:
        """Parse classification response into results."""
        results = []
        lines = response.strip().split('\n')
        
        for line in lines:
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    try:
                        rel_id = int(parts[0]) - 1
                        if 0 <= rel_id < len(relationships):
                            annotation_types = self._parse_annotation_types(parts[1])
                            confidence = self._parse_confidence(parts[2])
                            evidence = parts[3]
                            
                            result = ClassificationResult(
                                relationship=relationships[rel_id],
                                annotation_types=annotation_types,
                                confidence=confidence,
                                evidence_summary=evidence
                            )
                            results.append(result)
                    except (ValueError, IndexError):
                        continue
        
        return results
    
    def _parse_annotation_types(self, type_text: str) -> List[AnnotationType]:
        """Parse annotation types from text."""
        types = []
        type_text = type_text.lower()
        
        if 'functional' in type_text:
            types.append(AnnotationType.FUNCTIONAL)
        if 'drug' in type_text:
            types.append(AnnotationType.DRUG)
        if 'phenotype' in type_text:
            types.append(AnnotationType.PHENOTYPE)
        
        return types or [AnnotationType.FUNCTIONAL]  # Default to functional
    
    def _parse_confidence(self, confidence_text: str) -> float:
        """Parse confidence level from text."""
        confidence_text = confidence_text.lower()
        if 'high' in confidence_text:
            return 0.9
        elif 'medium' in confidence_text:
            return 0.7
        elif 'low' in confidence_text:
            return 0.5
        else:
            return 0.7  # Default


class RowGenerator:
    """Stage 4: Generates schema-specific TSV rows."""
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm
    
    def generate_annotation_rows(self, classifications: List[ClassificationResult], article: ArticleInput) -> List[AnnotationRow]:
        """Generate annotation rows for all classifications."""
        all_rows = []
        
        for classification in classifications:
            for annotation_type in classification.annotation_types:
                row = self._generate_single_row(classification, annotation_type, article)
                if row:
                    all_rows.append(row)
        
        return all_rows
    
    def _generate_single_row(self, classification: ClassificationResult, 
                           annotation_type: AnnotationType, article: ArticleInput) -> Optional[AnnotationRow]:
        """Generate a single annotation row."""
        relationship = classification.relationship
        
        # Select appropriate prompt template
        if annotation_type == AnnotationType.FUNCTIONAL:
            template = PromptTemplates.FUNCTIONAL_ANNOTATION_GENERATION
        elif annotation_type == AnnotationType.DRUG:
            template = PromptTemplates.DRUG_ANNOTATION_GENERATION
        elif annotation_type == AnnotationType.PHENOTYPE:
            template = PromptTemplates.PHENOTYPE_ANNOTATION_GENERATION
        else:
            return None
        
        prompt = PromptTemplates.format_prompt(
            template,
            pmid=article.pmid,
            relationship_description=f"{relationship.variant} - {relationship.drug} - {relationship.phenotype}",
            supporting_sentence=relationship.evidence_text
        )
        
        response = self.llm.generate(prompt, temperature=0.1)
        
        # Parse the TSV row
        return self._parse_tsv_response(response, annotation_type)
    
    def _parse_tsv_response(self, response: str, annotation_type: AnnotationType) -> Optional[AnnotationRow]:
        """Parse LLM response into annotation row."""
        lines = response.strip().split('\n')
        
        # Find the TSV row (should be tab-separated)
        for line in lines:
            if '\t' in line and len(line.split('\t')) > 10:  # Minimum field count
                row_data = line.split('\t')
                
                # Generate unique ID if needed
                if not row_data[0] or row_data[0] == '[Generate unique ID]':
                    row_data[0] = self._generate_unique_id()
                
                # Get field names based on annotation type
                fields = self._get_field_names(annotation_type)
                
                return AnnotationRow(
                    annotation_type=annotation_type,
                    row_data=row_data,
                    fields=fields
                )
        
        return None
    
    def _generate_unique_id(self) -> str:
        """Generate unique annotation ID."""
        timestamp = str(int(time.time()))
        random_num = str(random.randint(1000, 9999))
        return timestamp + random_num
    
    def _get_field_names(self, annotation_type: AnnotationType) -> List[str]:
        """Get field names for annotation type."""
        if annotation_type == AnnotationType.FUNCTIONAL:
            return [
                "Variant Annotation ID", "Variant/Haplotypes", "Gene", "Drug(s)", "PMID",
                "Phenotype Category", "Significance", "Notes", "Sentence", "Alleles",
                "Specialty Population", "Assay type", "Metabolizer types", "isPlural",
                "Is/Is Not associated", "Direction of effect", "Functional terms",
                "Gene/gene product", "When treated with/exposed to/when assayed with",
                "Multiple drugs And/or", "Cell type", "Comparison Allele(s) or Genotype(s)",
                "Comparison Metabolizer types"
            ]
        elif annotation_type == AnnotationType.DRUG:
            return [
                "Variant Annotation ID", "Variant/Haplotypes", "Gene", "Drug(s)", "PMID",
                "Phenotype Category", "Significance", "Notes", "Sentence", "Alleles",
                "Specialty Population", "Metabolizer types", "isPlural",
                "Is/Is Not associated", "Direction of effect", "PD/PK terms",
                "Multiple drugs And/or", "Population types",
                "Population Phenotypes or diseases", "Multiple phenotypes or diseases And/or",
                "Comparison Allele(s) or Genotype(s)", "Comparison Metabolizer types"
            ]
        elif annotation_type == AnnotationType.PHENOTYPE:
            return [
                "Variant Annotation ID", "Variant/Haplotypes", "Gene", "Drug(s)", "PMID",
                "Phenotype Category", "Significance", "Notes", "Sentence", "Alleles",
                "Specialty Population", "Metabolizer types", "isPlural",
                "Is/Is Not associated", "Direction of effect", "Side effect/efficacy/other",
                "Phenotype", "Multiple phenotypes And/or",
                "When treated with/exposed to/when assayed with", "Multiple drugs And/or",
                "Population types", "Population Phenotypes or diseases",
                "Multiple phenotypes or diseases And/or",
                "Comparison Allele(s) or Genotype(s)", "Comparison Metabolizer types"
            ]
        else:
            return []


class QualityValidator:
    """Stage 5: Validates generated annotation rows."""
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm
    
    def validate_row(self, row: AnnotationRow, article: ArticleInput) -> ValidationResult:
        """Validate a single annotation row."""
        # Basic validation first
        basic_errors = self._basic_validation(row)
        
        if basic_errors:
            return ValidationResult(is_valid=False, errors=basic_errors)
        
        # LLM-based validation
        prompt = PromptTemplates.format_prompt(
            PromptTemplates.QUALITY_VALIDATION,
            annotation_row=row.to_tsv(),
            relevant_text=article.article_text[:1000],  # First 1000 chars
            schema_fields=', '.join(row.fields)
        )
        
        response = self.llm.generate(prompt, temperature=0.1)
        
        return self._parse_validation_response(response, row)
    
    def _basic_validation(self, row: AnnotationRow) -> List[str]:
        """Perform basic validation checks."""
        errors = []
        
        # Check field count
        expected_count = len(row.fields)
        actual_count = len(row.row_data)
        
        if actual_count != expected_count:
            errors.append(f"Field count mismatch: expected {expected_count}, got {actual_count}")
        
        # Check required fields are not empty
        required_indices = [0, 1, 2, 4]  # ID, Variant, Gene, PMID
        for idx in required_indices:
            if idx < len(row.row_data) and not row.row_data[idx].strip():
                errors.append(f"Required field '{row.fields[idx]}' is empty")
        
        # Validate controlled vocabulary fields
        if len(row.row_data) > 5:  # Phenotype Category
            category = row.row_data[5]
            valid_categories = ["Metabolism/PK", "Efficacy", "Toxicity", "Dosage", "Other"]
            if category and category not in valid_categories:
                errors.append(f"Invalid Phenotype Category: {category}")
        
        if len(row.row_data) > 6:  # Significance
            significance = row.row_data[6]
            valid_significance = ["yes", "no", "not stated"]
            if significance and significance not in valid_significance:
                errors.append(f"Invalid Significance: {significance}")
        
        return errors
    
    def _parse_validation_response(self, response: str, row: AnnotationRow) -> ValidationResult:
        """Parse validation response from LLM."""
        lines = response.strip().split('\n')
        
        is_valid = any('VALID' in line.upper() for line in lines[:3])
        errors = []
        
        # Extract error messages
        for line in lines:
            if line.startswith('- ') or line.startswith('* '):
                errors.append(line[2:].strip())
        
        return ValidationResult(is_valid=is_valid, errors=errors)