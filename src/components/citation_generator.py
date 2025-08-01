import re
from typing import List, Dict
from pydantic import BaseModel, Field
from loguru import logger
from litellm import completion
import os
from abc import ABC, abstractmethod
from src.components.annotation_table import AnnotationTable, AnnotationRelationship
from src.utils import get_article_text
from difflib import SequenceMatcher
from tqdm import tqdm

# Prompts
annotation_citation_prompt = """
Pharmacogenomic Relationship:
- Gene: {annotation.gene}
- Polymorphism: {annotation.polymorphism}  
- Proposed Effect: {annotation.relationship_effect}
- P-value: {annotation.p_value}

Rate how strongly the following sentence supports the proposed effect of the pharmacogenomic relationship on a scale of 1-10.
Sentence to evaluate:
"{sentence}"

Rate from 0-10 where:
- 10: Sentence directly mentions this exact gene-polymorphism relationship and effect. Especially if it contains the mentioned p-value.
- 7-9: Sentence mentions the gene and polymorphism with related effects
- 4-6: Sentence mentions either the gene or polymorphism with some context
- 1-3: Sentence has minimal relevance to this relationship
- 0: Sentence has no relevance to this relationship

Provide your score on a scale of 0-10 (one decimal place allowed). No other text.
"""

study_parameters_citation_prompt = """

Parameter Type: {parameter_type}
Proposed Parameter Value: {parameter_content}

Rate how strongly the following sentence supports the proposed parameter value on a scale of 0-10.

Sentence to evaluate:
"{sentence}"

Rate from 0-10 where:
- 10: Sentence directly supports or describes this parameter
- 7-9: Sentence is closely related to this parameter
- 4-6: Sentence has some relevance to this parameter
- 1-3: Sentence has minimal relevance to this parameter
- 0: Sentence has no relevance to this parameter

Provide your score on a scale of 0-10 (one decimal place allowed). No other text.
"""

class SentenceRelevance(BaseModel):
    """Model for sentence relevance scoring"""
    sentence: str = Field(description="The sentence text")
    relevance_score: int = Field(description="Relevance score from 1-10", ge=1, le=10)


class AnnotationCitations(BaseModel):
    """Model for citations associated with an annotation"""
    gene: str = Field(description="Gene name from the annotation")
    polymorphism: str = Field(description="Polymorphism from the annotation")
    citations: List[str] = Field(description="Top 3 most relevant sentences")


class CitationGeneratorBase(ABC):
    """
    Abstract base class for citation generators.
    """
    
    def __init__(self, pmcid: str, model: str = "local"):
        """
        Initialize the citation generator base.
        
        Args:
            pmcid: PubMed Central ID
            model: Model to use for relevance scoring
        """
        self.pmcid = pmcid
        self.model = model
        self.article_text = get_article_text(pmcid)
        
        # Split article into sentences
        self.sentences = self._split_into_sentences(self.article_text)
        logger.info(f"Split article into {len(self.sentences)} sentences")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex pattern.
        Excludes markdown headers from the sentence list.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentences with markdown headers excluded
        """
        # Basic sentence splitting - can be improved with more sophisticated NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out very short sentences, markdown headers, and clean up
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip if too short
            if len(sentence) <= 20:
                continue
            # Skip if it's a markdown header (starts with # after stripping)
            if re.match(r'^\s*#+\s', sentence):
                continue
            if "Keywords:" in sentence or "keywords:" in sentence:
                continue
            filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    @abstractmethod
    def _score_sentence_relevance(self, sentence: str, annotation: AnnotationRelationship) -> int:
        """
        Score how relevant a sentence is to a specific annotation.
        
        Args:
            sentence: The sentence to score
            annotation: The annotation to compare against
            
        Returns:
            Relevance score from 1-10
        """
        pass
    
    @abstractmethod
    def _score_sentence_for_parameter(self, sentence: str, parameter_content: str, parameter_type: str) -> int:
        """
        Score how relevant a sentence is to a specific study parameter.
        
        Args:
            sentence: The sentence to score
            parameter_content: The content of the parameter to find citations for
            parameter_type: The type of parameter (summary, study_type, etc.)
            
        Returns:
            Relevance score from 1-10
        """
        pass
    
    def _is_citation_similar(self, citation1: str, citation2: str, threshold: float = 0.8) -> bool:
        """
        Check if two citations are similar using sequence matching.
        
        Args:
            citation1: First citation to compare
            citation2: Second citation to compare  
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if citations are similar above threshold
        """
        # Normalize citations for comparison
        norm1 = citation1.lower().strip()
        norm2 = citation2.lower().strip()
        
        # Calculate similarity ratio
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= threshold
    
    def _is_generic_background(self, sentence: str) -> bool:
        """
        Check if a sentence is generic background information not specific to the study.
        
        Args:
            sentence: Sentence to evaluate
            
        Returns:
            True if sentence appears to be generic background
        """
        sentence_lower = sentence.lower()
        
        # Generic phrases that indicate background information
        generic_patterns = [
            'for example,',
            'in addition,',
            'furthermore,',
            'moreover,',
            'various studies',
            'research has',
            'investigations have',
            'studies have',
            'it has been',
            'previous research',
            'prior studies',
            'literature suggests',
            'evidence suggests',
            'reports have',
            'findings suggest'
        ]
        
        # Check for generic patterns
        generic_count = sum(1 for pattern in generic_patterns if pattern in sentence_lower)
        
        # Consider it generic if it has multiple generic patterns
        return generic_count >= 2
    
    def _remove_duplicates_and_filter(self, citations: List[str]) -> List[str]:
        """
        Remove duplicate and generic citations from a list.
        
        Args:
            citations: List of citation strings
            
        Returns:
            Filtered list with duplicates and generic citations removed
        """
        if not citations:
            return citations
        
        filtered_citations = []
        
        for citation in citations:
            # Skip if it's generic background information
            if self._is_generic_background(citation):
                logger.debug(f"Skipping generic citation: {citation[:100]}...")
                continue
            
            # Skip if similar to an already added citation
            is_duplicate = False
            for existing in filtered_citations:
                if self._is_citation_similar(citation, existing):
                    logger.debug(f"Skipping duplicate citation: {citation[:100]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered_citations.append(citation)
        
        return filtered_citations
    
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
        
        for i, sentence in tqdm(enumerate(candidate_sentences), total=len(candidate_sentences), desc=f"Scoring sentences using {self.model}"):
            score = self._score_sentence_relevance(sentence, annotation)
            sentence_scores.append((sentence, score))
        
        # Sort by score descending and take more than needed for filtering
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Take more candidates than needed to account for filtering
        candidate_sentences = [item[0] for item in sentence_scores[:top_k * 3]]
        
        # Remove duplicates and filter generic citations
        filtered_sentences = self._remove_duplicates_and_filter(candidate_sentences)
        
        # Take final top K after filtering
        top_sentences = filtered_sentences[:top_k]
        
        # If we don't have enough after filtering, add more non-generic ones
        if len(top_sentences) < top_k:
            remaining_needed = top_k - len(top_sentences)
            for sentence, score in sentence_scores[top_k * 3:]:
                if not self._is_generic_background(sentence):
                    # Check if it's not already similar to existing ones
                    is_duplicate = any(self._is_citation_similar(sentence, existing) 
                                     for existing in top_sentences)
                    if not is_duplicate:
                        top_sentences.append(sentence)
                        remaining_needed -= 1
                        if remaining_needed == 0:
                            break
        
        # Log the scores for the final top sentences
        logger.info(f"Top scores for {annotation.gene}-{annotation.polymorphism} (after filtering):")
        final_scores = [(s, score) for s, score in sentence_scores 
                       if s in top_sentences]
        for i, (sentence, score) in enumerate(final_scores[:top_k]):
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
        Ensures uniqueness across all relationships to avoid citation reuse.
        
        Args:
            annotations: Original AnnotationTable
            
        Returns:
            AnnotationTable with citations added
        """
        updated_relationships = []
        used_citations = set()  # Track citations used across all relationships
        
        for i, annotation in enumerate(annotations.relationships):
            logger.info(f"Adding citations to annotation {i+1}/{len(annotations.relationships)}: {annotation.gene}-{annotation.polymorphism}")
            
            # Get more candidates to account for global filtering
            top_citations_candidates = self._get_top_citations_for_annotation(annotation, top_k=5)
            
            # Filter out citations already used in other relationships
            unique_citations = []
            for citation in top_citations_candidates:
                # Check if this citation is too similar to any already used citation
                is_globally_duplicate = any(
                    self._is_citation_similar(citation, used_citation, threshold=0.7)
                    for used_citation in used_citations
                )
                
                if not is_globally_duplicate:
                    unique_citations.append(citation)
                    used_citations.add(citation)
                    if len(unique_citations) >= 3:  # We want 3 unique citations per relationship
                        break
            
            # If we still don't have enough unique citations, get more candidates
            if len(unique_citations) < 3:
                additional_candidates = self._get_top_citations_for_annotation(annotation, top_k=10)
                for citation in additional_candidates:
                    if citation not in unique_citations:
                        is_globally_duplicate = any(
                            self._is_citation_similar(citation, used_citation, threshold=0.7)
                            for used_citation in used_citations
                        )
                        
                        if not is_globally_duplicate:
                            unique_citations.append(citation)
                            used_citations.add(citation)
                            if len(unique_citations) >= 3:
                                break
            
            # Final fallback: if still no unique citations, use lower similarity threshold or fallback citations
            if len(unique_citations) == 0:
                # Try with a lower similarity threshold
                fallback_candidates = self._get_top_citations_for_annotation(annotation, top_k=15)
                for citation in fallback_candidates:
                    is_globally_duplicate = any(
                        self._is_citation_similar(citation, used_citation, threshold=0.5)
                        for used_citation in used_citations
                    )
                    
                    if not is_globally_duplicate:
                        unique_citations.append(citation)
                        used_citations.add(citation)
                        if len(unique_citations) >= 3:
                            break
                
                # Ultimate fallback: if STILL no citations, find any sentence mentioning the gene
                if len(unique_citations) == 0:
                    logger.warning(f"No citations found for {annotation.gene}-{annotation.polymorphism}, using fallback")
                    gene_mentions = [s for s in self.sentences if annotation.gene.lower() in s.lower()]
                    if gene_mentions:
                        if len(gene_mentions) < 3:
                            unique_citations = gene_mentions
                        else:
                            unique_citations = gene_mentions[:3]  # At least provide one citation
                        used_citations.update(unique_citations)
            
            # Create new annotation with unique citations
            updated_annotation = AnnotationRelationship(
                gene=annotation.gene,
                polymorphism=annotation.polymorphism,
                relationship_effect=annotation.relationship_effect,
                p_value=annotation.p_value,
                citations=unique_citations[:3]  # Take top 3 unique citations
            )
            
            updated_relationships.append(updated_annotation)
            
            logger.info(f"Added {len(unique_citations)} unique citations for {annotation.gene}-{annotation.polymorphism}")
        
        return AnnotationTable(relationships=updated_relationships)
    
    def _get_top_citations_for_parameter(self, parameter_content: str, parameter_type: str, top_k: int = 3) -> List[str]:
        """
        Find the top K most relevant sentences for a specific study parameter.
        
        Args:
            parameter_content: The content of the parameter to find citations for
            parameter_type: The type of parameter (summary, study_type, etc.)
            top_k: Number of top sentences to return
            
        Returns:
            List of top relevant sentences
        """
        # Pre-filter sentences based on parameter type keywords
        parameter_keywords = {
            'summary': ['study', 'research', 'investigation'],
            'study_type': ['study', 'design', 'analysis', 'gwas', 'cohort', 'case'],
            'participant_info': ['participants', 'subjects', 'patients', 'population'],
            'study_design': ['design', 'methodology', 'sample', 'recruitment'],
            'study_results': ['results', 'findings', 'significant', 'association'],
            'allele_frequency': ['allele', 'frequency', 'genotype', 'variant']
        }
        
        keywords = parameter_keywords.get(parameter_type, [])
        candidate_sentences = []
        
        for sentence in self.sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                candidate_sentences.append(sentence)
        
        # If we have too few candidates, use more sentences
        if len(candidate_sentences) < 20:
            candidate_sentences = self.sentences[:min(100, len(self.sentences))]
        
        logger.info(f"Pre-filtered to {len(candidate_sentences)} candidate sentences for {parameter_type}")
        
        sentence_scores = []
        
        for sentence in candidate_sentences:
            score = self._score_sentence_for_parameter(sentence, parameter_content, parameter_type)
            sentence_scores.append((sentence, score))
        
        # Sort by score descending and take more than needed for filtering
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Take more candidates than needed to account for filtering
        candidate_sentences = [item[0] for item in sentence_scores[:top_k * 3]]
        
        # Remove duplicates and filter generic citations
        filtered_sentences = self._remove_duplicates_and_filter(candidate_sentences)
        
        # Take final top K after filtering
        top_sentences = filtered_sentences[:top_k]
        
        # If we don't have enough after filtering, add more non-generic ones
        if len(top_sentences) < top_k:
            remaining_needed = top_k - len(top_sentences)
            for sentence, score in sentence_scores[top_k * 3:]:
                if not self._is_generic_background(sentence):
                    # Check if it's not already similar to existing ones
                    is_duplicate = any(self._is_citation_similar(sentence, existing) 
                                     for existing in top_sentences)
                    if not is_duplicate:
                        top_sentences.append(sentence)
                        remaining_needed -= 1
                        if remaining_needed == 0:
                            break
        
        # Log the scores for the final top sentences
        logger.info(f"Top scores for {parameter_type} (after filtering):")
        final_scores = [(s, score) for s, score in sentence_scores 
                       if s in top_sentences]
        for i, (sentence, score) in enumerate(final_scores[:top_k]):
            logger.info(f"  {i+1}. Score {score}: {sentence[:100]}...")
        
        return top_sentences
    
    def add_citations_to_study_parameters(self, study_parameters):
        """
        Add citations to study parameters by finding relevant sentences for each parameter.
        Modifies the parameters to include citations nested within each parameter key.
        
        Args:
            study_parameters: StudyParameters object
            
        Returns:
            StudyParameters object with citations nested in each parameter
        """
        logger.info("Adding citations to study parameters")
        
        # Create a new study parameters object with citations
        updated_params = study_parameters.model_copy(deep=True)
        
        # Add citations nested within each parameter
        updated_params.summary.citations = self._get_top_citations_for_parameter(
            study_parameters.summary.content, 'summary'
        )
        
        updated_params.study_type.citations = self._get_top_citations_for_parameter(
            study_parameters.study_type.content, 'study_type'
        )
        
        updated_params.participant_info.citations = self._get_top_citations_for_parameter(
            study_parameters.participant_info.content, 'participant_info'
        )
        
        updated_params.study_design.citations = self._get_top_citations_for_parameter(
            study_parameters.study_design.content, 'study_design'
        )
        
        updated_params.study_results.citations = self._get_top_citations_for_parameter(
            study_parameters.study_results.content, 'study_results'
        )
        
        updated_params.allele_frequency.citations = self._get_top_citations_for_parameter(
            study_parameters.allele_frequency.content, 'allele_frequency'
        )
        
        logger.info("Completed adding citations to study parameters")
        return updated_params


class LocalCitationGenerator(CitationGeneratorBase):
    """
    Citation generator using local similarity/regex-based scoring for offline usage.
    """
    
    def _score_sentence_relevance(self, sentence: str, annotation: AnnotationRelationship) -> int:
        """
        Score how relevant a sentence is to a specific annotation using local similarity/regex.
        
        Args:
            sentence: The sentence to score
            annotation: The annotation to compare against
            
        Returns:
            Relevance score from 1-10
        """
        sentence_lower = sentence.lower()
        score = 0
        
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
        
        # Check for effect-related terms if we have effect information
        if annotation.relationship_effect:
            effect_terms = annotation.relationship_effect.lower().split()
            effect_matches = [term for term in effect_terms if len(term) > 3 and term in sentence_lower]
            if effect_matches:
                score += 1
        
        # Check for statistical terms if we have p-value
        if annotation.p_value:
            stat_keywords = ['p-value', 'p<', 'p =', 'significant', 'correlation', 'association', 'odds ratio']
            stat_matches = [kw for kw in stat_keywords if kw in sentence_lower]
            if stat_matches:
                score += 1
        
        # Bonus for having both gene and polymorphism
        if gene_found and poly_found:
            score += 2
        
        # Calculate similarity using sequence matcher for additional context
        query = f"{annotation.gene} {annotation.polymorphism} {annotation.relationship_effect or ''}".lower()
        similarity = SequenceMatcher(None, sentence_lower, query).ratio()
        if similarity > 0.3:
            score += int(similarity * 2)
        
        # Clamp score between 1-10
        score = max(1, min(10, score))
        
        return score

    def _score_sentence_for_parameter(self, sentence: str, parameter_content: str, parameter_type: str) -> int:
        """
        Score how relevant a sentence is to a specific study parameter using local similarity/regex.
        
        Args:
            sentence: The sentence to score
            parameter_content: The content of the parameter to find citations for
            parameter_type: The type of parameter (summary, study_type, etc.)
            
        Returns:
            Relevance score from 1-10
        """
        sentence_lower = sentence.lower()
        parameter_lower = parameter_content.lower()
        score = 0
        
        # Define keywords for each parameter type
        parameter_keywords = {
            'summary': ['study', 'research', 'investigation', 'analysis', 'examined', 'evaluated', 'assessed'],
            'study_type': ['gwas', 'case-control', 'cohort', 'clinical trial', 'meta-analysis', 'cross-sectional', 'retrospective', 'prospective'],
            'participant_info': ['participants', 'subjects', 'patients', 'age', 'gender', 'ethnicity', 'population', 'demographics'],
            'study_design': ['design', 'methodology', 'sample size', 'recruitment', 'protocol', 'inclusion', 'exclusion'],
            'study_results': ['results', 'findings', 'significant', 'p-value', 'odds ratio', 'hazard ratio', 'correlation', 'association'],
            'allele_frequency': ['allele', 'frequency', 'genotype', 'variant', 'polymorphism', 'mutation', 'prevalence']
        }
        
        # Check for parameter-specific keywords
        if parameter_type in parameter_keywords:
            keywords = parameter_keywords[parameter_type]
            keyword_matches = [kw for kw in keywords if kw in sentence_lower]
            if keyword_matches:
                score += min(3, len(keyword_matches))
        
        # Check for direct overlap with parameter content
        parameter_words = [word for word in parameter_lower.split() if len(word) > 3]
        word_matches = [word for word in parameter_words if word in sentence_lower]
        if word_matches:
            score += min(4, len(word_matches))
        
        # Calculate text similarity
        similarity = SequenceMatcher(None, sentence_lower, parameter_lower).ratio()
        if similarity > 0.2:
            score += int(similarity * 3)
        
        # Check for statistical terms if this is results
        if parameter_type == 'study_results':
            stat_keywords = ['p<', 'p =', 'p-value', 'significant', 'ci', 'confidence interval', 'odds ratio', 'hazard ratio']
            stat_matches = [kw for kw in stat_keywords if kw in sentence_lower]
            if stat_matches:
                score += 2
        
        # Check for study type indicators
        if parameter_type == 'study_type':
            type_indicators = ['study was', 'conducted', 'design', 'approach', 'method']
            type_matches = [indicator for indicator in type_indicators if indicator in sentence_lower]
            if type_matches:
                score += 2
        
        # Clamp score between 1-10
        score = max(1, min(10, score))
        
        return score


class LMCitationGenerator(CitationGeneratorBase):
    """
    Citation generator using LM-based scoring with language models.
    """
    
    def _score_sentence_relevance(self, sentence: str, annotation: AnnotationRelationship) -> int:
        """
        Score how relevant a sentence is to a specific annotation using language model.
        
        Args:
            sentence: The sentence to score
            annotation: The annotation to compare against
            
        Returns:
            Relevance score from 1-10
        """
        prompt = annotation_citation_prompt
        prompt = annotation_citation_prompt.format(annotation=annotation, sentence=sentence)
        try:
            completion_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 100
            }
            
            response = completion(**completion_kwargs)
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response - expect only numeric score (no reasoning)
            try:
                # Extract numeric score directly from response
                score_match = re.search(r'\b(\d+(?:\.\d+)?)\b', response_text)
                if score_match:
                    score = float(score_match.group(1))
                    score = max(0, min(10, score))  # Clamp between 0-10
                    return int(score)
                else:
                    logger.warning(f"No numeric score found in response: {response_text}")
                    return 1
            except Exception as parse_error:
                logger.warning(f"Error parsing score from response '{response_text}': {parse_error}")
                return 1
                
        except Exception as e:
            logger.error(f"Error scoring sentence relevance: {e}")
            return 1

    def _score_sentence_for_parameter(self, sentence: str, parameter_content: str, parameter_type: str) -> int:
        """
        Score how relevant a sentence is to a specific study parameter using language model.
        
        Args:
            sentence: The sentence to score
            parameter_content: The content of the parameter to find citations for
            parameter_type: The type of parameter (summary, study_type, etc.)
            
        Returns:
            Relevance score from 1-10
        """
        prompt = study_parameters_citation_prompt
        prompt = study_parameters_citation_prompt.format(parameter_type=parameter_type, parameter_content=parameter_content, sentence=sentence)
        
        try:
            completion_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 50
            }
            
            response = completion(**completion_kwargs)
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response - expect only numeric score (no reasoning)
            try:
                # Extract numeric score directly from response
                score_match = re.search(r'\b(\d+(?:\.\d+)?)\b', response_text)
                if score_match:
                    score = float(score_match.group(1))
                    score = max(0, min(10, score))  # Clamp between 0-10
                    return int(score)
                else:
                    logger.warning(f"No numeric score found in response: {response_text}")
                    return 1
            except Exception as parse_error:
                logger.warning(f"Error parsing score from response '{response_text}': {parse_error}")
                return 1
                
        except Exception as e:
            logger.error(f"Error scoring sentence for parameter: {e}")
            return 1


def create_citation_generator(pmcid: str, model: str = "local") -> CitationGeneratorBase:
    """
    Factory method to create the appropriate citation generator.
    
    Args:
        pmcid: PubMed Central ID
        model: Model to use - "local" for similarity/regex scoring, or any LM model name for language model scoring
        
    Returns:
        Citation generator instance
    """
    if model == "local":
        logger.info(f"Creating local citation generator")
        return LocalCitationGenerator(pmcid, model)
    else:
        logger.info(f"Creating LM-based citation generator with model {model}")
        return LMCitationGenerator(pmcid, model)


# Maintain backward compatibility
def CitationGenerator(pmcid: str, model: str = "local", approach: str = None) -> CitationGeneratorBase:
    """
    Legacy constructor for backward compatibility.
    
    Args:
        pmcid: PubMed Central ID
        model: Model to use - "local" for similarity/regex scoring, or any LM model name for language model scoring
        approach: DEPRECATED - kept for backward compatibility, use model parameter instead
        
    Returns:
        Citation generator instance
    """
    # Handle legacy approach parameter
    if approach is not None:
        logger.warning("The 'approach' parameter is deprecated. Use model='local' for local scoring or specify an LM model name.")
        if approach == "local":
            return create_citation_generator(pmcid, "local")
        else:
            # If approach was "lm", use the provided model
            return create_citation_generator(pmcid, model)
    else:
        return create_citation_generator(pmcid, model)


def main():
    """
    Test function for citation generator using PMC11730665 and a single sentence.
    """
    # Test parameters
    pmcid = "PMC11730665"
    test_sentence = "Patients with the GG genotype had a trend toward lower efficacy of sitagliptin and higher efficacy of gliclazide, likely due to slower metabolism of gliclazide."
    
    # Create citation generator
    generator = create_citation_generator(pmcid, model="gemini/gemini-2.5-flash-lite")
    
    # Create a mock annotation for testing
    from src.components.annotation_table import AnnotationRelationship
    test_annotation = AnnotationRelationship(
        gene="CYP2C9",
        polymorphism="rs1057910 GG",
        relationship_effect="Patients with the GG genotype had a trend toward lower efficacy of sitagliptin and higher efficacy of gliclazide, likely due to slower metabolism of gliclazide.",
        p_value=".464",
        citations=[]
    )
    
    print(f"Testing citation generator with PMCID: {pmcid}")
    print(f"Test sentence: {test_sentence}")
    print(f"Test annotation: {test_annotation.gene} {test_annotation.polymorphism}")
    print("-" * 50)
    
    # Get citations for the annotation
    citations = generator._get_top_citations_for_annotation(test_annotation, top_k=3)
    
    print(f"Found {len(citations)} citations:")
    for i, citation in enumerate(citations, 1):
        print(f"{i}. {citation}")
        print()
    
    return citations


if __name__ == "__main__":
    main()