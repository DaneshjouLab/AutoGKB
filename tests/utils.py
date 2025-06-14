from termcolor import colored
from typing import List

def compare_lists(experimental_list: List[str], ground_truth_list: List[str], pmcid: str):
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
            colored_experimental.append(colored(item, 'green'))
        else:
            colored_experimental.append(colored(item, 'red'))
    
    # Color ground truth list
    for item in ground_truth_list:
        if item in experimental_set:
            colored_ground_truth.append(colored(item, 'green'))
        else:
            colored_ground_truth.append(colored(item, 'red'))
    
    # Print colored lists
    print(f"================= {pmcid} =================")
    print("Experimental List:")
    print(' '.join(map(str, colored_experimental)))
    print("\nGround Truth List:")
    print(' '.join(map(str, colored_ground_truth)))
    
    # Return performance metrics
    return true_positives, true_negatives, false_positives, false_negatives