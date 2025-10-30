from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
import numpy as np
import re
from sentence_transformers import SentenceTransformer


_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    return _model


def parse_variant_list(variants_text: Optional[str]) -> List[str]:
    if not variants_text:
        return []
    tokens = re.split(r'[,;|\s]+(?:\+\s*)?', variants_text)
    return [t.strip() for t in tokens if t and t.strip()]


def normalize_variant(variant: str) -> str:
    v = variant.strip()
    if v.lower().startswith('rs'):
        return v.lower()
    return re.sub(r'\s+', '', v)


def expand_annotations_by_variant(annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []
    for ann in annotations:
        variants_field = ann.get('Variant/Haplotypes')
        tokens = parse_variant_list(variants_field)
        if len(tokens) <= 1:
            expanded.append(ann)
            continue
        for tok in tokens:
            new_ann = dict(ann)
            new_ann['Variant/Haplotypes'] = normalize_variant(tok)
            new_ann['_expanded_from_multi_variant'] = True
            expanded.append(new_ann)
    return expanded


def validate_external_data(annotation: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    rsid_pattern = re.compile(r'^rs\d+$', re.IGNORECASE)
    star_allele_pattern = re.compile(r'^[A-Z0-9]+\*\d+$')
    gene_pattern = re.compile(r'^[A-Z0-9]+$')

    variants = annotation.get('Variant/Haplotypes', '')
    if variants:
        variant_list = re.split(r'[,;|\s]+(?:\+\s*)?', variants)
        for variant in (v.strip() for v in variant_list if v.strip()):
            if variant.lower().startswith('rs'):
                if not rsid_pattern.match(variant):
                    issues.append(f"Invalid rsID format: {variant}")
            elif '*' in variant:
                if not star_allele_pattern.match(variant):
                    issues.append(f"Invalid star allele format: {variant}")

    gene = annotation.get('Gene', '')
    if gene and not gene_pattern.match(gene):
        issues.append(f"Invalid gene name format: {gene}")
    return issues


def validate_field_dependencies(annotation: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    gene_product = annotation.get('Gene/gene product')
    gene = annotation.get('Gene')
    if gene_product and not gene:
        issues.append("Gene field required when Gene/gene product is specified")

    comparison_alleles = annotation.get('Comparison Allele(s) or Genotype(s)')
    variants = annotation.get('Variant/Haplotypes')
    if comparison_alleles and not variants:
        issues.append("Variant/Haplotypes required when Comparison Allele(s) is specified")

    direction = annotation.get('Direction of effect')
    association = annotation.get('Is/Is Not associated')
    if direction and association != 'Associated with':
        issues.append("Direction of effect requires 'Associated with' status")

    functional_terms = annotation.get('Functional terms')
    gene_product = annotation.get('Gene/gene product')
    if functional_terms and not gene_product:
        issues.append("Gene/gene product recommended when Functional terms is specified")
    return issues


def validate_annotation_consistency(annotation: Dict[str, Any], study_params: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    variant_id = annotation.get('Variant Annotation ID')
    if variant_id:
        found_in_study = any(sp.get('Variant Annotation ID') == variant_id for sp in study_params)
        if not found_in_study:
            issues.append(f"Variant Annotation ID {variant_id} not found in study_parameters")

    annotation_pmid = annotation.get('PMID')
    if annotation_pmid and study_params:
        study_pmids = {sp.get('PMID') for sp in study_params if sp.get('PMID')}
        if study_pmids and annotation_pmid not in study_pmids:
            issues.append(f"PMID {annotation_pmid} inconsistent with study parameters")
    return issues


def validate_all_dependencies(annotation: Dict[str, Any], study_params: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    issues: List[str] = []
    issues.extend(validate_external_data(annotation))
    issues.extend(validate_field_dependencies(annotation))
    if study_params:
        issues.extend(validate_annotation_consistency(annotation, study_params))
    return issues


def evaluate_functional_analysis(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate FA when provided a list with exactly two dicts:
      - samples[0] = ground truth annotation dict
      - samples[1] = prediction annotation dict

    Args:
        samples: [ground_truth_dict, prediction_dict]

    Returns:
        Dict with overall and per-field scores.
    """

    if not isinstance(samples, list) or len(samples) != 2:
        raise ValueError("Expected a list with exactly two dicts: [ground_truth, prediction].")
    gt, pred = samples[0], samples[1]
    if not isinstance(gt, dict) or not isinstance(pred, dict):
        raise ValueError("Both items must be dicts: [ground_truth_dict, prediction_dict].")

    gt_list: List[Dict[str, Any]] = [gt]
    pred_list: List[Dict[str, Any]] = [pred]

    model = _get_model()

    def exact_match(gt_val: Any, pred_val: Any) -> float:
        if gt_val is None and pred_val is None:
            return 1.0
        if gt_val is None or pred_val is None:
            return 0.0
        return 1.0 if str(gt_val).strip().lower() == str(pred_val).strip().lower() else 0.0

    def semantic_similarity(gt_val: Any, pred_val: Any) -> float:
        if gt_val is None and pred_val is None:
            return 1.0
        if gt_val is None or pred_val is None:
            return 0.0
        gt_str = str(gt_val).strip()
        pred_str = str(pred_val).strip()
        if gt_str == pred_str:
            return 1.0
        try:
            embeddings = model.encode([gt_str, pred_str])
            gt_embedding = embeddings[0]
            pred_embedding = embeddings[1]
            similarity = float(np.dot(gt_embedding, pred_embedding) / (np.linalg.norm(gt_embedding) * np.linalg.norm(pred_embedding)))
            return similarity
        except Exception:
            return SequenceMatcher(None, gt_str.lower(), pred_str.lower()).ratio()

    def variant_coverage(gt_variants: str, pred_variants: str) -> float:
        if not gt_variants or not pred_variants:
            return 1.0 if not gt_variants and not pred_variants else 0.0

        def is_wildtype(variant: str) -> bool:
            variant_lower = variant.lower().strip()
            wildtype_indicators = ['wild type', 'wildtype', 'wt', '*1']
            return any(wt in variant_lower for wt in wildtype_indicators)

        def is_rsid(variant: str) -> bool:
            return variant.strip().lower().startswith('rs')

        def is_star_allele(variant: str) -> bool:
            return '*' in variant.strip()

        gt_list = [v.strip() for v in re.split(r'[,;|\s]+(?:\+\s*)?', gt_variants) if v.strip()]
        pred_list = [v.strip() for v in re.split(r'[,;|\s]+(?:\+\s*)?', pred_variants) if v.strip()]
        gt_list_filtered = [v for v in gt_list if not is_wildtype(v)]
        if not gt_list_filtered:
            return 1.0 if pred_list else 0.0

        covered_count = 0
        for gt_var in gt_list_filtered:
            gt_var_lower = gt_var.lower()
            if is_rsid(gt_var) or is_star_allele(gt_var):
                if any(gt_var_lower == pred_var.lower() for pred_var in pred_list):
                    covered_count += 1
            else:
                best_match_score = 0.0
                for pred_var in pred_list:
                    if gt_var_lower in pred_var.lower() or pred_var.lower() in gt_var_lower:
                        best_match_score = 1.0
                        break
                    similarity = SequenceMatcher(None, gt_var_lower, pred_var.lower()).ratio()
                    best_match_score = max(best_match_score, similarity)
                if best_match_score > 0.8:
                    covered_count += 1
        return covered_count / len(gt_list_filtered)

    field_evaluators = {
        'Variant/Haplotypes': variant_coverage,
        'Gene': semantic_similarity,
        'Drug(s)': semantic_similarity,
        'PMID': exact_match,
        'Phenotype Category': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Significance': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Alleles': semantic_similarity,
        'Specialty Population': semantic_similarity,
        'Assay type': semantic_similarity,
        'Metabolizer types': semantic_similarity,
        'isPlural': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Is/Is Not associated': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Direction of effect': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Functional terms': semantic_similarity,
        'Gene/gene product': semantic_similarity,
        'When treated with/exposed to/when assayed with': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Multiple drugs And/or': lambda gt, pred: 1.0 if (gt and pred and gt.lower().strip() == pred.lower().strip()) else (1.0 if not gt and not pred else 0.0),
        'Cell type': semantic_similarity,
        'Comparison Allele(s) or Genotype(s)': semantic_similarity,
        'Comparison Metabolizer types': semantic_similarity
    }

    results: Dict[str, Any] = {'total_samples': len(gt_list), 'field_scores': {}, 'overall_score': 0.0}

    for field, evaluator in field_evaluators.items():
        scores: List[float] = []
        for gt, pred in zip(gt_list, pred_list):
            scores.append(evaluator(gt.get(field), pred.get(field)))
        results['field_scores'][field] = {'mean_score': sum(scores) / len(scores), 'scores': scores}

    results['detailed_results'] = []
    for i, (gt, pred) in enumerate(zip(gt_list, pred_list)):
        sample_result: Dict[str, Any] = {'sample_id': i, 'field_scores': {}}
        for field, evaluator in field_evaluators.items():
            sample_result['field_scores'][field] = evaluator(gt.get(field), pred.get(field))
        dependency_issues = validate_all_dependencies(pred, None)
        sample_result['dependency_issues'] = dependency_issues
        if dependency_issues:
            penalty_per_issue = 0.05
            total_penalty = min(len(dependency_issues) * penalty_per_issue, 0.3)
            fields_to_penalize = set()
            for issue in dependency_issues:
                if "Gene" in issue or "gene" in issue:
                    fields_to_penalize.update(['Gene', 'Gene/gene product'])
                elif "Variant" in issue or "variant" in issue:
                    fields_to_penalize.update(['Variant/Haplotypes', 'Comparison Allele(s) or Genotype(s)'])
                elif "Direction" in issue or "Associated" in issue:
                    fields_to_penalize.update(['Direction of effect', 'Is/Is Not associated'])
                elif "Functional" in issue:
                    fields_to_penalize.update(['Functional terms', 'Gene/gene product'])
                elif "rsID" in issue or "star allele" in issue:
                    fields_to_penalize.add('Variant/Haplotypes')
                else:
                    fields_to_penalize.update(sample_result['field_scores'].keys())
            for field in fields_to_penalize:
                original_score = sample_result['field_scores'][field]
                sample_result['field_scores'][field] = original_score * (1 - total_penalty)
        results['detailed_results'].append(sample_result)

    for field in list(field_evaluators.keys()):
        field_scores = [s['field_scores'][field] for s in results['detailed_results']]
        results['field_scores'][field] = {'mean_score': sum(field_scores) / len(field_scores), 'scores': field_scores}

    field_means = [v['mean_score'] for v in results['field_scores'].values()]
    results['overall_score'] = sum(field_means) / len(field_means) if field_means else 0.0
    return results


