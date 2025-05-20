import time
import random
import pandas as pd
from Bio import Entrez
from tqdm import tqdm
from dotenv import load_dotenv
import os
from src.load_variants import get_pmid_list
import json
from src.utils.file_paths import get_project_root

load_dotenv()
# Email for NCBI
Entrez.email = os.getenv("NCBI_EMAIL")

# Step 1: Function to get PMCID from PMID
import requests
from loguru import logger

import requests
import time
from loguru import logger
from typing import List, Set, Dict, Optional


def load_saved_pmcid_mapping() -> Dict[str, Optional[str]]:
    """
    Load the saved PMCID mapping from the json file.
    """
    project_root = get_project_root()
    results_path = project_root / "data" / "pmcid_mapping.json"

    # Create data directory if it doesn't exist
    os.makedirs(project_root / "data", exist_ok=True)

    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            existing_results = json.load(f)
        logger.info(
            f"Loaded {len(existing_results)} existing PMCID mappings from {results_path}"
        )
    else:
        logger.info(
            f"No PMCID mapping found at {results_path}. Creating empty mapping."
        )
        existing_results = {}
    return existing_results


def batch_pmid_to_pmcid(
    pmids: List[str],
    email: str = os.getenv("NCBI_EMAIL"),
    batch_size: int = 100,
    delay: float = 0.4,
) -> Dict[str, Optional[str]]:
    """
    Convert a list of PMIDs to PMCIDs using NCBI's ID Converter API.

    Args:
        pmids: List of PMIDs (as strings).
        email: Your email address for NCBI tool identification.
        batch_size: Number of PMIDs to send per request (max: 200).
        delay: Seconds to wait between requests (default 0.4 to respect NCBI).

    Returns:
        Dict mapping each PMID to a PMCID (or None if not available).
    """
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    results = {}
    existing_results = load_saved_pmcid_mapping()

    # Check for existing results
    existing_pmids = set(existing_results.keys())

    # Remove existing results from pmids
    filtered_pmids = [x for x in pmids if str(x) not in existing_pmids]

    logger.info(f"Remaining PMIDs to process: {len(filtered_pmids)}")
    if len(filtered_pmids) == 0:
        logger.warning("No PMIDs to process. Exiting.")
        return existing_results

    # Process remaining PMIDs
    for i in range(0, len(filtered_pmids), batch_size):
        batch = filtered_pmids[i : i + batch_size]
        batch_str = [str(pmid) for pmid in batch]
        ids_str = ",".join(batch_str)
        logger.info(f"Processing PMIDs {i + 1} to {i + len(batch)}...")

        params = {
            "tool": "pmid2pmcid_tool",
            "email": email,
            "ids": ids_str,
            "format": "json",
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get("records", [])
            for record in records:
                pmid = record.get("pmid")
                pmcid = record.get("pmcid")
                results[pmid] = pmcid if pmcid else None
                if pmcid:
                    logger.info(f"PMID {pmid} → PMCID {pmcid}")
                else:
                    logger.warning(f"PMID {pmid} has no PMCID available.")
        except Exception as e:
            logger.error(f"Failed batch starting at index {i}: {e}")
            for pmid in batch:
                results[pmid] = None

        time.sleep(delay)

    # Merge existing results with new results
    existing_results.update(results)

    # Save updated results
    project_root = get_project_root()
    results_path = project_root / "data" / "pmcid_mapping.json"

    # Create data directory if it doesn't exist
    os.makedirs(project_root / "data", exist_ok=True)

    with open(results_path, "w") as f:
        json.dump(existing_results, f)
    logger.info(f"Updated PMCID mappings saved to {results_path}")

    return existing_results


def get_unique_pmcids() -> List[str]:
    """
    Get a list of unique PMCIDs from the PMCID mapping (pmcid_mapping.json)
    NOTE: Could add functionality to check for new PMCIDs in mapping and update the unique_pmcids.json file
    Currently function returns the pre-existing unique PMCIDs if they exist or regenerates the list from the mapping.
    """
    project_root = get_project_root()

    # Load the unique PMCIDs if they've already been saved
    unique_pmcids_path = project_root / "data" / "unique_pmcids.json"

    # Create data directory if it doesn't exist
    os.makedirs(project_root / "data", exist_ok=True)

    if os.path.exists(unique_pmcids_path):
        with open(unique_pmcids_path, "r") as f:
            try:
                pmcids = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error loading unique PMCIDs from {unique_pmcids_path}: {e}"
                )
                raise e
        logger.warning(
            f"Loaded {len(pmcids)} pre-existing unique PMCIDs from {unique_pmcids_path}"
        )
        return pmcids

    # Load from pmcid_mapping.json if unique pmcids haven't been saved
    results_path = project_root / "data" / "pmcid_mapping.json"

    if not os.path.exists(results_path):
        logger.error(
            f"No PMCID mapping found at {results_path}. Cannot generate unique PMCIDs."
        )
        return []

    with open(results_path, "r") as f:
        existing_results = json.load(f)

    # Get the unique pmcids (remove None values)
    pmcids = [value for value in existing_results.values() if value is not None]
    pmcids = list(set(pmcids))

    # Save the unique pmcids to a json file
    with open(unique_pmcids_path, "w") as f:
        json.dump(pmcids, f)
    logger.info(f"Unique PMCIDs saved to {unique_pmcids_path}")
    return pmcids


if __name__ == "__main__":
    pmid_list = get_pmid_list()
    results = batch_pmid_to_pmcid(pmid_list, os.getenv("NCBI_EMAIL"))
    logger.info(f"PMCID mapping complete. {len(results)} PMIDs mapped to PMCIDs.")
    pmcids = get_unique_pmcids()
    logger.info(f"Number of unique PMCIDs: {len(pmcids)}")
