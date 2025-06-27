import re
from loguru import logger
import json
from typing import List
from termcolor import colored
from src.inference import Variant
from src.article_parser import MarkdownParser


def extractVariantsRegex(text):
    # Note, seems to extract a ton of variants, not just the ones that are being studied
    # Think it might only be applicable to rsIDs
    variantRegex = r"\b([A-Z]+\d+[A-Z]*\*\d+|\brs\d+)\b"
    return re.findall(variantRegex, text) or []


def save_output(prompt, output, filename):
    # save prompt and output to file
    with open(f"test_outputs/{filename}.txt", "w") as f:
        f.write("Prompt:\n")
        f.write(prompt)
        f.write("\nOutput:\n")
        f.write(output)
    logger.info(f"Saved output to {filename}.txt")


def compare_lists(
    experimental_list: List[str], ground_truth_list: List[str], pmcid: str
):
    """
    Compare experimental list with ground truth list and calculate performance metrics.

    Args:
    experimental_list (list): List of predicted/experimental values
    ground_truth_list (list): List of actual/ground truth values
    pmcid (str): PMCID of the article

    Returns:
    tuple: (true_positives, true_negatives, false_positives, false_negatives)
    """
    # Convert lists to sets for efficient comparison
    experimental_set = set(experimental_list)
    ground_truth_set = set(ground_truth_list)

    # Calculate performance metrics
    true_positives = len(experimental_set.intersection(ground_truth_set))
    false_positives = len(experimental_set - ground_truth_set)
    false_negatives = len(ground_truth_set - experimental_set)
    true_negatives = 0  # Not applicable in this context

    # Color-code the lists
    colored_experimental = []
    colored_ground_truth = []

    # Color experimental list
    for item in experimental_list:
        if item in ground_truth_set:
            colored_experimental.append(colored(item, "green"))
        else:
            colored_experimental.append(colored(item, "red"))

    # Color ground truth list
    for item in ground_truth_list:
        if item in experimental_set:
            colored_ground_truth.append(colored(item, "green"))
        else:
            colored_ground_truth.append(colored(item, "red"))

    # Print colored lists
    print(f"================= {pmcid} =================")
    print("Experimental List:")
    print(" ".join(map(str, colored_experimental)))
    print("\nGround Truth List:")
    print(" ".join(map(str, colored_ground_truth)))

    # Return performance metrics
    return true_positives, true_negatives, false_positives, false_negatives


def get_true_variants(pmcid):
    """
    Get the actual annotated variants for a given PMCID.
    """
    true_variant_list = json.load(open("data/benchmark/true_variant_list.json"))
    return true_variant_list[pmcid]


def get_article_text(pmcid: str = None, article_text: str = None):
    """
    Get the article text for a given PMCID or return the article text if it is already provided.
    """
    if article_text is None and pmcid is None:
        logger.error("Either article_text or pmcid must be provided.")
        raise ValueError("Either article_text or pmcid must be provided.")

    if article_text is not None and pmcid is not None:
        logger.warning("Both article_text and PMCID are provided. Using article_text.")

    if article_text is None:
        article_text = MarkdownParser(pmcid=pmcid).get_article_text()

    return article_text
