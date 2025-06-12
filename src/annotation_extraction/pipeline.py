"""
Main pipeline orchestrator for annotation extraction.
"""

from typing import List, Dict, Optional, Tuple
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from .models import (
    ArticleInput, RelevanceResult, ExtractedEntities, ClassificationResult,
    AnnotationRow, ValidationResult, AnnotationType
)
from .inference import (
    LLMInterface, RelevanceScreener, EntityExtractor, AnnotationClassifier,
    RowGenerator, QualityValidator
)
from .prompts import PromptTemplates


class AnnotationPipeline:
    """Main pipeline for extracting pharmacogenomic annotations from articles."""
    
    def __init__(self, llm: LLMInterface, enable_validation: bool = True, 
                 parallel_processing: bool = False, max_workers: int = 4):
        """
        Initialize the annotation pipeline.
        
        Args:
            llm: LLM interface for generating responses
            enable_validation: Whether to enable quality validation
            parallel_processing: Whether to process multiple articles in parallel
            max_workers: Maximum number of worker threads for parallel processing
        """
        self.llm = llm
        self.enable_validation = enable_validation
        self.parallel_processing = parallel_processing
        self.max_workers = max_workers
        
        # Initialize pipeline stages
        self.relevance_screener = RelevanceScreener(llm)
        self.entity_extractor = EntityExtractor(llm)
        self.annotation_classifier = AnnotationClassifier(llm)
        self.row_generator = RowGenerator(llm)
        self.quality_validator = QualityValidator(llm) if enable_validation else None
    
    def process_article(self, article: ArticleInput) -> Dict:
        """
        Process a single article through the complete pipeline.
        
        Args:
            article: Input article data
            
        Returns:
            Dictionary containing processing results and generated annotations
        """
        logger.info(f"Processing article PMID: {article.pmid}")
        
        results = {
            'pmid': article.pmid,
            'relevance': None,
            'entities': None,
            'classifications': [],
            'annotations': [],
            'validation_results': [],
            'errors': [],
            'success': False
        }
        
        try:
            # Stage 1: Relevance screening
            logger.debug("Stage 1: Relevance screening")
            relevance = self.relevance_screener.screen_article(article)
            results['relevance'] = asdict(relevance)
            
            if not relevance.is_relevant:
                logger.info(f"Article {article.pmid} not relevant for annotation")
                results['success'] = True
                return results
            
            # Stage 2: Entity extraction
            logger.debug("Stage 2: Entity extraction")
            entities = self.entity_extractor.extract_entities(article)
            results['entities'] = asdict(entities)
            
            # Stage 3: Relationship classification
            logger.debug("Stage 3: Relationship classification")
            classifications = self.annotation_classifier.classify_relationships(entities, article)
            results['classifications'] = [asdict(c) for c in classifications]
            
            if not classifications:
                logger.warning(f"No classifiable relationships found in article {article.pmid}")
                results['success'] = True
                return results
            
            # Stage 4: Row generation
            logger.debug("Stage 4: Row generation")
            annotations = self.row_generator.generate_annotation_rows(classifications, article)
            results['annotations'] = [asdict(a) for a in annotations]
            
            # Stage 5: Quality validation (optional)
            if self.enable_validation and self.quality_validator:
                logger.debug("Stage 5: Quality validation")
                validation_results = []
                for annotation in annotations:
                    validation = self.quality_validator.validate_row(annotation, article)
                    validation_results.append(validation)
                
                results['validation_results'] = [asdict(v) for v in validation_results]
                
                # Filter out invalid annotations if validation is enabled
                valid_annotations = []
                for annotation, validation in zip(annotations, validation_results):
                    if validation.is_valid:
                        valid_annotations.append(annotation)
                    else:
                        logger.warning(f"Invalid annotation for {article.pmid}: {validation.errors}")
                
                results['annotations'] = [asdict(a) for a in valid_annotations]
            
            results['success'] = True
            logger.info(f"Successfully processed article {article.pmid}: {len(results['annotations'])} annotations")
            
        except Exception as e:
            logger.error(f"Error processing article {article.pmid}: {str(e)}")
            results['errors'].append(str(e))
            results['success'] = False
        
        return results
    
    def process_articles(self, articles: List[ArticleInput]) -> List[Dict]:
        """
        Process multiple articles through the pipeline.
        
        Args:
            articles: List of input articles
            
        Returns:
            List of processing results for each article
        """
        logger.info(f"Processing {len(articles)} articles")
        
        if self.parallel_processing and len(articles) > 1:
            return self._process_articles_parallel(articles)
        else:
            return self._process_articles_sequential(articles)
    
    def _process_articles_sequential(self, articles: List[ArticleInput]) -> List[Dict]:
        """Process articles sequentially."""
        results = []
        for article in articles:
            result = self.process_article(article)
            results.append(result)
        return results
    
    def _process_articles_parallel(self, articles: List[ArticleInput]) -> List[Dict]:
        """Process articles in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all articles for processing
            future_to_article = {
                executor.submit(self.process_article, article): article 
                for article in articles
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing article {article.pmid}: {str(e)}")
                    results.append({
                        'pmid': article.pmid,
                        'success': False,
                        'errors': [str(e)]
                    })
        
        # Sort results by PMID to maintain consistent ordering
        results.sort(key=lambda x: x.get('pmid', ''))
        
        return results
    
    def process_batch_article(self, article: ArticleInput) -> Dict:
        """
        Process an article using batch processing for multiple relationships.
        
        This method uses the batch processing prompt to handle articles
        with many variant-outcome relationships more efficiently.
        
        Args:
            article: Input article data
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Batch processing article PMID: {article.pmid}")
        
        results = {
            'pmid': article.pmid,
            'relevance': None,
            'batch_annotations': [],
            'validation_results': [],
            'errors': [],
            'success': False
        }
        
        try:
            # Stage 1: Relevance screening
            relevance = self.relevance_screener.screen_article(article)
            results['relevance'] = asdict(relevance)
            
            if not relevance.is_relevant:
                logger.info(f"Article {article.pmid} not relevant for batch annotation")
                results['success'] = True
                return results
            
            # Batch processing prompt
            prompt = PromptTemplates.format_prompt(
                PromptTemplates.BATCH_PROCESSING,
                pmid=article.pmid,
                full_article=article.article_text
            )
            
            response = self.llm.generate(prompt, temperature=0.2)
            
            # Parse batch response
            annotations = self._parse_batch_response(response)
            results['batch_annotations'] = [asdict(a) for a in annotations]
            
            # Optional validation
            if self.enable_validation and self.quality_validator:
                validation_results = []
                for annotation in annotations:
                    validation = self.quality_validator.validate_row(annotation, article)
                    validation_results.append(validation)
                
                results['validation_results'] = [asdict(v) for v in validation_results]
                
                # Filter valid annotations
                valid_annotations = []
                for annotation, validation in zip(annotations, validation_results):
                    if validation.is_valid:
                        valid_annotations.append(annotation)
                
                results['batch_annotations'] = [asdict(a) for a in valid_annotations]
            
            results['success'] = True
            logger.info(f"Batch processed article {article.pmid}: {len(results['batch_annotations'])} annotations")
            
        except Exception as e:
            logger.error(f"Error batch processing article {article.pmid}: {str(e)}")
            results['errors'].append(str(e))
            results['success'] = False
        
        return results
    
    def _parse_batch_response(self, response: str) -> List[AnnotationRow]:
        """Parse batch processing response into annotation rows."""
        annotations = []
        lines = response.strip().split('\n')
        
        current_type = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('ANNOTATION_TYPE:'):
                type_text = line.split(':', 1)[1].strip().lower()
                if 'functional' in type_text:
                    current_type = AnnotationType.FUNCTIONAL
                elif 'drug' in type_text:
                    current_type = AnnotationType.DRUG
                elif 'phenotype' in type_text:
                    current_type = AnnotationType.PHENOTYPE
            
            elif line.startswith('ROW:') and current_type:
                row_data = line.split(':', 1)[1].strip()
                if '\t' in row_data:
                    fields = self._get_field_names_for_type(current_type)
                    annotation = AnnotationRow(
                        annotation_type=current_type,
                        row_data=row_data.split('\t'),
                        fields=fields
                    )
                    annotations.append(annotation)
        
        return annotations
    
    def _get_field_names_for_type(self, annotation_type: AnnotationType) -> List[str]:
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
    
    def export_annotations_to_tsv(self, results: List[Dict], output_dir: str) -> Dict[str, str]:
        """
        Export annotations to TSV files by type.
        
        Args:
            results: List of processing results
            output_dir: Directory to save TSV files
            
        Returns:
            Dictionary mapping annotation types to file paths
        """
        import os
        from collections import defaultdict
        
        # Group annotations by type
        annotations_by_type = defaultdict(list)
        
        for result in results:
            if result.get('success') and result.get('annotations'):
                for annotation_dict in result['annotations']:
                    annotation_type = annotation_dict['annotation_type']
                    annotations_by_type[annotation_type].append(annotation_dict)
        
        # Write TSV files
        file_paths = {}
        
        for annotation_type, annotations in annotations_by_type.items():
            if not annotations:
                continue
                
            filename = f"var_{annotation_type}_ann.tsv"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                if annotations:
                    header = '\t'.join(annotations[0]['fields'])
                    f.write(header + '\n')
                
                # Write data rows
                for annotation in annotations:
                    row = '\t'.join(annotation['row_data'])
                    f.write(row + '\n')
            
            file_paths[annotation_type] = file_path
            logger.info(f"Exported {len(annotations)} {annotation_type} annotations to {file_path}")
        
        return file_paths
    
    def get_pipeline_stats(self, results: List[Dict]) -> Dict:
        """Get statistics about pipeline processing."""
        stats = {
            'total_articles': len(results),
            'successful_articles': 0,
            'relevant_articles': 0,
            'total_annotations': 0,
            'annotations_by_type': {},
            'validation_pass_rate': 0.0,
            'error_count': 0,
            'errors': []
        }
        
        for result in results:
            if result.get('success'):
                stats['successful_articles'] += 1
                
                if result.get('relevance', {}).get('is_relevant'):
                    stats['relevant_articles'] += 1
                
                # Count annotations
                if result.get('annotations'):
                    stats['total_annotations'] += len(result['annotations'])
                    
                    for annotation in result['annotations']:
                        ann_type = annotation.get('annotation_type', 'unknown')
                        stats['annotations_by_type'][ann_type] = stats['annotations_by_type'].get(ann_type, 0) + 1
                
                # Validation statistics
                if result.get('validation_results'):
                    valid_count = sum(1 for v in result['validation_results'] if v.get('is_valid'))
                    total_count = len(result['validation_results'])
                    if total_count > 0:
                        stats['validation_pass_rate'] += valid_count / total_count
            
            if result.get('errors'):
                stats['error_count'] += len(result['errors'])
                stats['errors'].extend(result['errors'])
        
        # Average validation pass rate
        if stats['successful_articles'] > 0:
            stats['validation_pass_rate'] /= stats['successful_articles']
        
        return stats