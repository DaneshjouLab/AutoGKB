from loguru import logger
from src.components.deprecated.all_variants import extract_all_variants
import json
from typing import List
from src.utils import compare_lists
from typing import List

def load_ground_truth(pmcid: str):
    try:
        with open(f"tests/data/true_variant_list.json", "r") as f:
            try:
                return json.load(f)[pmcid]
            except KeyError:
                logger.error(f"PMCID {pmcid} not found in ground truth file (tests/data/true_variant_list.json)")
                return []
    except FileNotFoundError:
        logger.error(f"Ground truth file for PMCID {pmcid} not found (tests/data/true_variant_list.json)")
        return []

def parse_variant_list(variant_list):
    return [i['variant_id'] for i in variant_list]

def calc_contingencies(ground_truth: List[str], extracted: List[str]):
    true_positives = len(set(ground_truth) & set(extracted))
    true_negatives = len(set(extracted) - set(ground_truth))
    false_positives = len(set(extracted) - set(ground_truth))
    false_negatives = len(set(ground_truth) - set(extracted))
    return {
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }

def calc_metrics(contingencies):
    precision = contingencies["true_positives"] / (contingencies["true_positives"] + contingencies["false_positives"])
    recall = contingencies["true_positives"] / (contingencies["true_positives"] + contingencies["false_negatives"])
    f1_score = 2 * (precision * recall) / (precision + recall)
    return precision, recall, f1_score

def test_extract_function(pmcids: List[str] | str, verbose: bool = False):
    running_contingencies = {
        "true_positives": 0,
        "true_negatives": 0,
        "false_positives": 0,
        "false_negatives": 0,
    }
    # Test the extract function
    if isinstance(pmcids, str):
        pmcids = [pmcids]

    for pmcid in pmcids:
        logger.info(f"Testing PMCID: {pmcid}")
        ground_truth = parse_variant_list(load_ground_truth(pmcid))
        extracted = parse_variant_list(extract_all_variants(pmcid))
        contingencies = calc_contingencies(ground_truth, extracted)
        # update running contingencies
        running_contingencies["true_positives"] += contingencies["true_positives"]
        running_contingencies["true_negatives"] += contingencies["true_negatives"]
        running_contingencies["false_positives"] += contingencies["false_positives"]
        running_contingencies["false_negatives"] += contingencies["false_negatives"]
        if verbose:
            compare_lists(extracted, ground_truth, pmcid)

    # calculate final metrics
    precision, recall, f1_score = calc_metrics(running_contingencies)
    print(f"Final Metrics: Precision: {precision}, Recall: {recall}, F1 Score: {f1_score}")

if __name__ == "__main__":
    test_extract_function("PMC11730665", verbose=True)