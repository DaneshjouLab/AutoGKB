# SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: Apache-2.0
from typing import Dict, List, Any, Optional, Tuple
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


def evaluate_drug_annotations(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parallel benchmark for drug entries.
    Input is a list with exactly two dicts:
      - samples[0] = ground truth annotation dict
      - samples[1] = prediction annotation dict
    """

    if not isinstance(samples, list) or len(samples) != 2:
        raise ValueError("Expected a list with exactly two dicts: [ground_truth, prediction].")
    gt, pred = samples[0], samples[1]
    if not isinstance(gt, dict) or not isinstance(pred, dict):
        raise ValueError("Both items must be dicts: [ground_truth_dict, prediction_dict].")

    # Variant expansion and alignment (mirroring FA)
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

    def align_by_variant(
        ground_truth_list: List[Dict[str, Any]],
        predictions_list: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        rs_re = re.compile(r"rs\d+", re.IGNORECASE)
        gt_expanded = expand_annotations_by_variant(ground_truth_list or [])
        pred_expanded = expand_annotations_by_variant(predictions_list or [])

        pred_index: List[Tuple[set, str, Dict[str, Any]]] = []
        for rec in pred_expanded:
            raw = (rec.get('Variant/Haplotypes') or '').strip()
            raw_norm = normalize_variant(raw).lower()
            rsids = set(m.group(0).lower() for m in rs_re.finditer(raw))
            pred_index.append((rsids, raw_norm, rec))

        aligned_gt: List[Dict[str, Any]] = []
        aligned_pred: List[Dict[str, Any]] = []
        display_keys: List[str] = []

        for gt_rec in gt_expanded:
            gt_raw = (gt_rec.get('Variant/Haplotypes') or '').strip()
            gt_norm = normalize_variant(gt_raw).lower()
            gt_rs = set(m.group(0).lower() for m in rs_re.finditer(gt_raw))

            match = None
            if gt_rs:
                for rsids, raw_norm, pred_rec in pred_index:
                    if rsids & gt_rs:
                        match = pred_rec
                        break
            if match is None and gt_norm:
                for rsids, raw_norm, pred_rec in pred_index:
                    if gt_norm in raw_norm:
                        match = pred_rec
                        break

            if match is not None:
                aligned_gt.append(gt_rec)
                aligned_pred.append(match)
                disp = next(iter(gt_rs)) if gt_rs else gt_norm
                display_keys.append(disp)

        return aligned_gt, aligned_pred, display_keys

    # Prepare lists and align
    gt_list_raw: List[Dict[str, Any]] = [gt]
    pred_list_raw: List[Dict[str, Any]] = [pred]
    gt_list, pred_list, _ = align_by_variant(gt_list_raw, pred_list_raw)
    if not gt_list:
        # nothing aligned; return empty result structure
        return {'total_samples': 0, 'field_scores': {}, 'overall_score': 0.0, 'detailed_results': []}

    model = _get_model()

    def normalize_drug_name(name: str) -> str:
        # lowercase, strip, collapse whitespace, standardize separators
        n = name.lower().strip()
        # normalize hyphens to space and standardize slashes
        n = n.replace('-', ' ')
        # replace slashes with space-slash-space to normalize
        n = n.replace('/', ' / ')
        n = re.sub(r"\s+", " ", n)
        return n

    def parse_drug_list(value: Optional[str]) -> List[str]:
        if not value:
            return []
        # split on commas or the word 'or' (for individual tokens), keep slashes inside tokens
        parts = re.split(r",|\bor\b", value, flags=re.IGNORECASE)
        tokens = []
        for part in parts:
            token = normalize_drug_name(part)
            if token:
                tokens.append(token)
        # remove empties and duplicates while preserving order
        seen = set()
        unique = []
        for t in tokens:
            if t and t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

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
            similarity = float(
                np.dot(gt_embedding, pred_embedding)
                / (np.linalg.norm(gt_embedding) * np.linalg.norm(pred_embedding))
            )
            return similarity
        except Exception:
            return SequenceMatcher(None, gt_str.lower(), pred_str.lower()).ratio()

    def variant_substring_match(gt_val: Any, pred_val: Any) -> float:
        """Return 1.0 if GT substring appears in prediction (case-insensitive).
        Also accept canonical gene-phenotype group labels via category equality.
        """
        if gt_val is None and pred_val is None:
            return 1.0
        if gt_val is None or pred_val is None:
            return 0.0
        gt_str = re.sub(r"\s+", " ", str(gt_val).strip().lower())
        pred_str = re.sub(r"\s+", " ", str(pred_val).strip().lower())
        # canonical phenotype-group labels that may appear in this field
        phenotype_group_labels = {
            'poor metabolizers',
            'intermediate metabolizers',
            'extensive metabolizers',
            'ultra-rapid metabolizers',
            'intermediate activity',
            'reduced function',
            'normal function',
        }
        if gt_str in phenotype_group_labels or pred_str in phenotype_group_labels:
            return 1.0 if gt_str == pred_str else 0.0
        if not gt_str:
            return 1.0 if not pred_str else 0.0
        return 1.0 if gt_str in pred_str else 0.0

    def parse_allele_tokens(text: Optional[str]) -> List[str]:
        if not text:
            return []
        # split on '+' and whitespace and commas/semicolons
        parts = re.split(r"[+/,;\s]+", str(text))
        tokens = [p.strip().lower() for p in parts if p and p.strip()]
        return tokens

    def alleles_set_coverage(gt_val: Any, pred_val: Any) -> float:
        """Order-insensitive coverage for allele/group fields.
        Scores fraction of GT tokens present in Pred tokens (1.0 if both empty).
        """
        gt_tokens = parse_allele_tokens(gt_val)
        pred_tokens = parse_allele_tokens(pred_val)
        if not gt_tokens and not pred_tokens:
            return 1.0
        if not gt_tokens or not pred_tokens:
            return 0.0
        pred_set = set(pred_tokens)
        covered = sum(1 for t in gt_tokens if t in pred_set)
        return covered / len(gt_tokens)

    def drugs_coverage(gt: Dict[str, Any], pred: Dict[str, Any]) -> float:
        """Operator-aware coverage for Drug(s).
        Uses `Multiple drugs And/or` to decide coverage rule. Defaults to 'or' if missing.
        """
        gt_drugs_raw = gt.get('Drug(s)')
        pred_drugs_raw = pred.get('Drug(s)')
        gt_tokens = parse_drug_list(gt_drugs_raw)
        pred_tokens = parse_drug_list(pred_drugs_raw)
        if not gt_tokens and not pred_tokens:
            return 1.0
        if not gt_tokens or not pred_tokens:
            return 0.0

        operator = (gt.get('Multiple drugs And/or') or pred.get('Multiple drugs And/or') or 'or').strip().lower()

        def token_match(g: str, p: str) -> bool:
            if g == p:
                return True
            # allow strong fuzzy match for short drug tokens
            return SequenceMatcher(None, g, p).ratio() >= 0.85

        # build coverage matrix
        covered = [False] * len(gt_tokens)
        for i, gtok in enumerate(gt_tokens):
            for ptok in pred_tokens:
                if token_match(gtok, ptok):
                    covered[i] = True
                    break

        if operator == 'and':
            return 1.0 if all(covered) else sum(1 for c in covered if c) / len(covered)
        # default 'or': partial credit by fraction covered, with minimum of whether any matched
        frac = sum(1 for c in covered if c) / len(covered)
        return max(frac, 1.0 if any(covered) else 0.0)

    # Map evaluators to drug schema fields; Drug(s) handled separately below.
    def category_equal(a: Any, b: Any) -> float:
        a_norm = (re.sub(r"\s+", " ", str(a).strip().lower()) if a is not None else None)
        b_norm = (re.sub(r"\s+", " ", str(b).strip().lower()) if b is not None else None)
        if a_norm is None and b_norm is None:
            return 1.0
        if a_norm is None or b_norm is None:
            return 0.0
        return 1.0 if a_norm == b_norm else 0.0

    field_evaluators = {
        'Variant/Haplotypes': variant_substring_match,
        'Gene': semantic_similarity,
        'PMID': exact_match,
        'Phenotype Category': category_equal,
        'Significance': category_equal,
        'Alleles': alleles_set_coverage,
        'Specialty Population': semantic_similarity,
        'Metabolizer types': semantic_similarity,
        'isPlural': category_equal,
        'Is/Is Not associated': category_equal,
        'Direction of effect': category_equal,
        'PD/PK terms': semantic_similarity,
        'Multiple drugs And/or': category_equal,
        'Population types': semantic_similarity,
        'Population Phenotypes or diseases': semantic_similarity,
        'Multiple phenotypes or diseases And/or': category_equal,
        'Comparison Allele(s) or Genotype(s)': alleles_set_coverage,
        'Comparison Metabolizer types': semantic_similarity,
    }

    results: Dict[str, Any] = {'total_samples': len(gt_list), 'field_scores': {}, 'overall_score': 0.0}

    for field, evaluator in field_evaluators.items():
        scores: List[float] = []
        for g, p in zip(gt_list, pred_list):
            scores.append(evaluator(g.get(field), p.get(field)))
        results['field_scores'][field] = {'mean_score': sum(scores) / len(scores), 'scores': scores}

    # Compute Drug(s) scores with operator-aware logic
    drug_scores: List[float] = []
    for g, p in zip(gt_list, pred_list):
        drug_scores.append(drugs_coverage(g, p))
    results['field_scores']['Drug(s)'] = {'mean_score': sum(drug_scores) / len(drug_scores), 'scores': drug_scores}

    results['detailed_results'] = []
    for i, (g, p) in enumerate(zip(gt_list, pred_list)):
        sample_result: Dict[str, Any] = {'sample_id': i, 'field_scores': {}}
        for field, evaluator in field_evaluators.items():
            sample_result['field_scores'][field] = evaluator(g.get(field), p.get(field))
        sample_result['field_scores']['Drug(s)'] = drugs_coverage(g, p)
        # No dependency penalties wired yet for drug entries; can be added later if needed
        sample_result['dependency_issues'] = []
        results['detailed_results'].append(sample_result)

    for field in list(field_evaluators.keys()) + ['Drug(s)']:
        field_scores = [s['field_scores'][field] for s in results['detailed_results']]
        results['field_scores'][field] = {'mean_score': sum(field_scores) / len(field_scores), 'scores': field_scores}

    field_means = [v['mean_score'] for v in results['field_scores'].values()]
    results['overall_score'] = sum(field_means) / len(field_means) if field_means else 0.0
    return results


