import re
from typing import List, Dict, Tuple, Literal
from pydantic import BaseModel, Field
from loguru import logger
from litellm import completion
import os
from src.components.annotation_table import AnnotationTable, AnnotationRelationship
from src.utils import get_article_text
from difflib import SequenceMatcher


class SentenceRelevance(BaseModel):
    """Model for sentence relevance scoring"""
    sentence: str = Field(description="The sentence text")
    relevance_score: int = Field(description="Relevance score from 1-10", ge=1, le=10)
    reasoning: str = Field(description="Brief explanation of the relevance score")


class AnnotationCitations(BaseModel):
    """Model for citations associated with an annotation"""
    gene: str = Field(description="Gene name from the annotation")
    polymorphism: str = Field(description="Polymorphism from the annotation")
    citations: List[str] = Field(description="Top 3 most relevant sentences")


class CitationGenerator:
    """
    Generator for adding citations to annotations by finding the most relevant
    sentences in the source text. Supports both LM-based scoring (using GPT-4o-mini)
    and local similarity/regex-based scoring for offline usage.
    """
    
    def __init__(self, pmcid: str, model: str = "gpt-4o-mini", approach: Literal["lm", "local"] = "lm"):
        """
        Initialize the citation generator.
        
        Args:
            pmcid: PubMed Central ID
            model: Model to use for relevance scoring (default: gpt-4o-mini)
            approach: Approach to use for scoring - "lm" for language model or "local" for similarity/regex
        """
        self.pmcid = pmcid
        self.model = model
        self.approach = approach
        self.article_text = get_article_text(pmcid)
        
        # Split article into sentences
        self.sentences = self._split_into_sentences(self.article_text)
        logger.info(f"Split article into {len(self.sentences)} sentences using {approach} approach")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex pattern.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentences
        """
        # Basic sentence splitting - can be improved with more sophisticated NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out very short sentences and clean up
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        return sentences
    
    def _score_sentence_relevance(self, sentence: str, annotation: AnnotationRelationship) -> Tuple[int, str]:
        """
        Score how relevant a sentence is to a specific annotation using GPT-4o-mini via litellm.
        
        Args:
            sentence: The sentence to score
            annotation: The annotation to compare against
            
        Returns:
            Tuple of (relevance_score, reasoning)
        """
        prompt = f"""
Rate the relevance of this sentence to the pharmacogenomic relationship on a scale of 1-10.

Pharmacogenomic Relationship:
- Gene: {annotation.gene}
- Polymorphism: {annotation.polymorphism}  
- Effect: {annotation.relationship_effect}
- P-value: {annotation.p_value}

Sentence to evaluate:
"{sentence}"

Rate from 1-10 where:
- 10: Sentence directly mentions this exact gene-polymorphism relationship and effect
- 7-9: Sentence mentions the gene and polymorphism with related effects
- 4-6: Sentence mentions either the gene or polymorphism with some context
- 1-3: Sentence has minimal or no relevance to this relationship

Provide your score and a brief 1-sentence reasoning.
Format: Score: X, Reasoning: [your reasoning]
"""
        
        try:
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response
            if "Score:" in response_text and "Reasoning:" in response_text:
                parts = response_text.split("Reasoning:")
                score_part = parts[0].replace("Score:", "").strip()
                reasoning = parts[1].strip()
                
                # Extract numeric score
                score = int(re.search(r'\d+', score_part).group())
                score = max(1, min(10, score))  # Clamp between 1-10
                
                return score, reasoning
            else:
                logger.warning(f"Unexpected response format: {response_text}")
                return 1, "Failed to parse response"
                
        except Exception as e:
            logger.error(f"Error scoring sentence relevance: {e}")
            return 1, f"Error: {str(e)}"
    
    def _score_sentence_similarity(self, sentence: str, annotation: AnnotationRelationship) -> Tuple[int, str]:
        """
        Score how relevant a sentence is to a specific annotation using local similarity/regex.
        
        Args:
            sentence: The sentence to score
            annotation: The annotation to compare against
            
        Returns:
            Tuple of (relevance_score, reasoning)
        """
        sentence_lower = sentence.lower()
        score = 0
        reasoning_parts = []
        
        # Check for exact gene match (higher weight)
        gene_variants = [
            annotation.gene.lower(),
            annotation.gene.lower().replace('(', '').replace(')', ''),
            annotation.gene.lower().replace('-', ''),
            annotation.gene.lower().replace('_', '')
        ]
        
        gene_found = False
        for gene_variant in gene_variants:
            if gene_variant in sentence_lower:
                score += 4
                gene_found = True
                reasoning_parts.append(f"contains gene '{annotation.gene}'")
                break
        
        # Check for polymorphism match
        poly_found = False
        if annotation.polymorphism:
            poly_variants = [
                annotation.polymorphism.lower(),
                annotation.polymorphism.lower().replace('*', ''),
                annotation.polymorphism.lower().split()[0] if ' ' in annotation.polymorphism else annotation.polymorphism.lower()
            ]
            
            for poly_variant in poly_variants:
                if poly_variant and poly_variant in sentence_lower:
                    score += 3
                    poly_found = True
                    reasoning_parts.append(f"contains polymorphism '{annotation.polymorphism}'")
                    break
        
        # Check for pharmacogenomic keywords
        pharma_keywords = [
            'metabolism', 'metabolize', 'drug', 'pharmacokinetic', 'pharmacodynamic',
            'efficacy', 'response', 'dosing', 'therapeutic', 'adverse', 'reaction',
            'toxicity', 'enzyme', 'inhibitor', 'inducer', 'substrate', 'variant',
            'genotype', 'phenotype', 'allele', 'mutation', 'polymorphism'
        ]
        
        keyword_matches = [kw for kw in pharma_keywords if kw in sentence_lower]
        if keyword_matches:
            score += min(2, len(keyword_matches))
            reasoning_parts.append(f"contains pharmacogenomic terms: {', '.join(keyword_matches[:3])}")
        
        # Check for effect-related terms if we have effect information
        if annotation.relationship_effect:
            effect_terms = annotation.relationship_effect.lower().split()
            effect_matches = [term for term in effect_terms if len(term) > 3 and term in sentence_lower]
            if effect_matches:
                score += 1
                reasoning_parts.append(f"mentions effect terms: {', '.join(effect_matches[:2])}")
        
        # Check for statistical terms if we have p-value
        if annotation.p_value:
            stat_keywords = ['p-value', 'p<', 'p =', 'significant', 'correlation', 'association', 'odds ratio']
            stat_matches = [kw for kw in stat_keywords if kw in sentence_lower]
            if stat_matches:
                score += 1
                reasoning_parts.append("contains statistical terms")
        
        # Bonus for having both gene and polymorphism
        if gene_found and poly_found:
            score += 2
            reasoning_parts.append("contains both gene and polymorphism")
        
        # Calculate similarity using sequence matcher for additional context
        query = f"{annotation.gene} {annotation.polymorphism} {annotation.relationship_effect or ''}".lower()
        similarity = SequenceMatcher(None, sentence_lower, query).ratio()
        if similarity > 0.3:
            score += int(similarity * 2)
            reasoning_parts.append(f"high text similarity ({similarity:.2f})")
        
        # Clamp score between 1-10
        score = max(1, min(10, score))
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "minimal relevance detected"
        
        return score, reasoning
    
    def _get_top_citations_for_annotation(self, annotation: AnnotationRelationship, top_k: int = 3) -> List[str]:
        """
        Find the top K most relevant sentences for a specific annotation.
        Uses keyword filtering to pre-select candidate sentences before scoring.
        
        Args:
            annotation: The annotation to find citations for
            top_k: Number of top sentences to return
            
        Returns:
            List of top relevant sentences
        """
        # First, filter sentences that contain the gene name or polymorphism
        gene_terms = [annotation.gene.lower(), annotation.gene.replace('(', '').replace(')', '').lower()]
        poly_terms = [annotation.polymorphism.lower().split()[0] if annotation.polymorphism else '']
        
        # Pre-filter sentences that contain relevant keywords
        candidate_sentences = []
        for sentence in self.sentences:
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in gene_terms + poly_terms if term):
                candidate_sentences.append(sentence)
        
        # If we have too few candidates, expand to more sentences
        if len(candidate_sentences) < 20:
            candidate_sentences = self.sentences[:min(100, len(self.sentences))]
        
        logger.info(f"Pre-filtered to {len(candidate_sentences)} candidate sentences for {annotation.gene}-{annotation.polymorphism}")
        
        sentence_scores = []
        
        for i, sentence in enumerate(candidate_sentences):
            if i % 10 == 0:  # Log progress every 10 sentences
                logger.info(f"Processed {i}/{len(candidate_sentences)} candidate sentences")
            
            # Use appropriate scoring method based on approach
            if self.approach == "lm":
                score, reasoning = self._score_sentence_relevance(sentence, annotation)
            else:  # local approach
                score, reasoning = self._score_sentence_similarity(sentence, annotation)
            
            sentence_scores.append((sentence, score, reasoning))
        
        # Sort by score descending and take top K
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [item[0] for item in sentence_scores[:top_k]]
        
        # Log the scores for the top sentences
        logger.info(f"Top scores for {annotation.gene}-{annotation.polymorphism}:")
        for i, (sentence, score, reasoning) in enumerate(sentence_scores[:top_k]):
            logger.info(f"  {i+1}. Score {score}: {sentence[:100]}...")
        
        return top_sentences
    
    def generate_citations(self, annotations: AnnotationTable) -> Dict[str, AnnotationCitations]:
        """
        Generate citations for all annotations in the table.
        
        Args:
            annotations: AnnotationTable containing relationships to cite
            
        Returns:
            Dictionary mapping annotation keys to their citations
        """
        citations_dict = {}
        
        for i, annotation in enumerate(annotations.relationships):
            logger.info(f"Processing annotation {i+1}/{len(annotations.relationships)}: {annotation.gene}-{annotation.polymorphism}")
            
            # Generate a unique key for this annotation
            annotation_key = f"{annotation.gene}_{annotation.polymorphism}".replace(" ", "_")
            
            # Get top citations for this annotation
            top_citations = self._get_top_citations_for_annotation(annotation)
            
            # Create citation object
            citation_obj = AnnotationCitations(
                gene=annotation.gene,
                polymorphism=annotation.polymorphism,
                citations=top_citations
            )
            
            citations_dict[annotation_key] = citation_obj
            
        logger.info(f"Generated citations for {len(citations_dict)} annotations")
        return citations_dict
    
    def add_citations_to_annotations(self, annotations: AnnotationTable) -> AnnotationTable:
        """
        Add citations directly to the annotation relationships.
        
        Args:
            annotations: Original AnnotationTable
            
        Returns:
            AnnotationTable with citations added
        """
        updated_relationships = []
        
        for i, annotation in enumerate(annotations.relationships):
            logger.info(f"Adding citations to annotation {i+1}/{len(annotations.relationships)}: {annotation.gene}-{annotation.polymorphism}")
            
            # Get top citations for this annotation
            top_citations = self._get_top_citations_for_annotation(annotation)
            
            # Create new annotation with citations
            updated_annotation = AnnotationRelationship(
                gene=annotation.gene,
                polymorphism=annotation.polymorphism,
                relationship_effect=annotation.relationship_effect,
                p_value=annotation.p_value,
                citations=top_citations
            )
            
            updated_relationships.append(updated_annotation)
        
        return AnnotationTable(relationships=updated_relationships)