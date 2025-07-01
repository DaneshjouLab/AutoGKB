import re
from loguru import logger
import json
from typing import List, Optional
from termcolor import colored
from src.article_parser import MarkdownParser

_true_variant_cache: Optional[dict] = None


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


def get_true_variants(pmcid: str) -> List[str]:
    """
    Get the actual annotated variants for a given PMCID.
    Uses module-level caching to load the JSON file only once.
    """
    global _true_variant_cache

    if _true_variant_cache is None:
        try:
            with open("data/benchmark/true_variant_list.json", "r") as f:
                _true_variant_cache = json.load(f)
        except FileNotFoundError:
            logger.error(
                "True variant list file not found: data/benchmark/true_variant_list.json"
            )
            _true_variant_cache = {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing true variant list JSON: {e}")
            _true_variant_cache = {}

    return _true_variant_cache.get(pmcid, []) if _true_variant_cache else []


def get_article_text(
    pmcid: Optional[str] = None, article_text: Optional[str] = None
) -> str:
    """
    Get the article text for a given PMCID or return the article text if it is already provided.
    """
    if article_text is None and pmcid is None:
        logger.error("Either article_text or pmcid must be provided.")
        raise ValueError("Either article_text or pmcid must be provided.")

    if article_text is None:
        article_text = MarkdownParser(pmcid=pmcid).get_article_text()

    return article_text


def is_pmcid(text: str):
    if text.startswith("PMC") and len(text) < 20:
        return True
    return False


def get_title(markdown_text: str):
    # get the title from the markdown text
    title = markdown_text.split("\n")[0]
    # remove the # from the title
    title = title.replace("# ", "")
    return title
