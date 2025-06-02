import os
import requests
import zipfile
from io import BytesIO
import shutil
from loguru import logger
import pandas as pd
import json

from src.utils.file_paths import get_project_root

"""
This file contains functions to load the clinical variants data from the PharmGKB API.
The key function is get_pmid_list(), which loads the PMIDs from the variant annotations tsv file and saves them to a json file.
"""


def download_and_extract_variant_annotations(override: bool = False) -> str:
    """
    Downloads and extracts the variant annotations zip file.
    If the folder already exists, it will be skipped unless override parameter is set to True.
    Params:
        override (bool): If True, the folder will be deleted and the zip file will be downloaded and extracted again.
    Returns:
        str: The path to the extracted folder.
    """
    url = "https://api.pharmgkb.org/v1/download/file/data/variantAnnotations.zip"

    save_dir = os.path.join(get_project_root(), "data")
    extract_dir = os.path.join(save_dir, "variantAnnotations")

    if os.path.exists(extract_dir):
        if not override:
            logger.info(f"Folder already exists at {extract_dir}. Skipping download.")
            return extract_dir
        else:
            shutil.rmtree(extract_dir)

    os.makedirs(extract_dir, exist_ok=True)

    logger.info(f"Downloading ZIP from {url}...")
    response = requests.get(url)
    response.raise_for_status()

    logger.info("Extracting ZIP...")
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        z.extractall(extract_dir)

    logger.info(f"Files extracted to: {extract_dir}")
    return extract_dir


def load_raw_variant_annotations(override: bool = False) -> pd.DataFrame:
    """
    Loads the variant annotations tsv file.
    If the file does not exist, it will be downloaded and extracted.
    Params:
        override (bool): If True, the file will be downloaded and extracted again.
    Returns:
        pd.DataFrame: The loaded variant annotations tsv file.
    """
    tsv_path = os.path.join(
        get_project_root(), "data", "variantAnnotations", "var_drug_ann.tsv"
    )

    if not os.path.exists(tsv_path):
        logger.info(f"{tsv_path} not found. Downloading data...")
        download_and_extract_variant_annotations(override)

    if not os.path.exists(tsv_path):
        logger.error(f"File still not found after download attempt: {tsv_path}")
        raise FileNotFoundError(
            f"File still not found after download attempt: {tsv_path}"
        )

    logger.info(f"Loading TSV from: {tsv_path}")
    df = pd.read_csv(tsv_path, sep="\t")
    return df


def unique_variants(df: pd.DataFrame) -> dict:
    """
    Generates a dictionary with unique values for each column of a Pandas DataFrame.

    Args:
        df: The input Pandas DataFrame.

    Returns:
        A dictionary where keys are column names and values are lists of unique values
        for that column. Returns an empty dictionary if the input is invalid.
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("Input is not a Pandas DataFrame")
        return {}

    return {col: df[col].unique().tolist() for col in df.columns}


def get_pmid_list(override: bool = False) -> list:
    """
    Loads the pmid list from the variant annotations tsv file.
    """
    pmid_list_path = os.path.join(get_project_root(), "data", "pmid_list.json")
    if os.path.exists(pmid_list_path):
        logger.info(f"Loading PMIDs from {pmid_list_path}")
        with open(pmid_list_path, "r") as f:
            pmid_list = json.load(f)
    else:
        df = load_raw_variant_annotations(override)
        pmid_list = df["PMID"].unique().tolist()
        logger.info(f"Saving PMIDs to {pmid_list_path}")
        with open(pmid_list_path, "w") as f:
            json.dump(pmid_list, f)
    return pmid_list


def variant_annotations_pipeline():
    """
    Loads the variant annotations tsv file and saves the unique PMIDs to a json file.
    """
    # Download and extract the variant annotations
    logger.info("Downloading and extracting variant annotations...")
    download_and_extract_variant_annotations()

    # Load the variant annotations
    logger.info("Loading variant annotations...")
    df = load_raw_variant_annotations()

    # Get the PMIDs
    logger.info("Getting PMIDs...")
    pmid_list = get_pmid_list()
    logger.info(f"Number of unique PMIDs: {len(pmid_list)}")


if __name__ == "__main__":
    variant_annotations_pipeline()
