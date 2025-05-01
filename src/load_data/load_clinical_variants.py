import os
import requests
import zipfile
from io import BytesIO
import shutil
from loguru import logger
import pandas as pd
import json

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
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, "saved_data")
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


def load_variant_annotations_tsv(override: bool = False) -> pd.DataFrame:
    """
    Loads the variant annotations tsv file.
    If the file does not exist, it will be downloaded and extracted.
    Params:
        override (bool): If True, the file will be downloaded and extracted again.
    Returns:
        pd.DataFrame: The loaded variant annotations tsv file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tsv_path = os.path.join(base_dir, "saved_data", "variantAnnotations", "var_drug_ann.tsv")

    if not os.path.exists(tsv_path):
        logger.info(f"{tsv_path} not found. Downloading data...")
        download_and_extract_variant_annotations(override)

    if not os.path.exists(tsv_path):
        logger.error(f"File still not found after download attempt: {tsv_path}")
        raise FileNotFoundError(f"File still not found after download attempt: {tsv_path}")

    logger.info(f"Loading TSV from: {tsv_path}")
    df = pd.read_csv(tsv_path, sep='\t')
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

def load_unique_variants(save_results: bool = True) -> dict:
    """
    Loads the unique variants from the variant annotations tsv file and saves them to a json file.
    If the json file already exists, it will be loaded from the file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    unique_variants_path = os.path.join(base_dir, "saved_data", "unique_variants.json")
    if os.path.exists(unique_variants_path):
        logger.info(f"Loading unique variants from {unique_variants_path}")
        with open(unique_variants_path, "r") as f:
            unique_values_per_column = json.load(f)
    else:
        logger.info(f"Unique variants not found at {unique_variants_path}. Loading from tsv file...")
        df = load_variant_annotations_tsv()
        unique_values_per_column = unique_variants(df)
        if save_results:
            logger.info(f"Saving unique variants to {unique_variants_path}")
            with open(unique_variants_path, "w") as f:
                json.dump(unique_values_per_column, f)
    return unique_values_per_column

def get_pmid_list(override: bool = False) -> list:
    """
    Loads the pmid list from the variant annotations tsv file.
    """
    df = load_variant_annotations_tsv()
    return df["PMID"].unique().tolist()

if __name__ == "__main__":
    pmid_list = get_pmid_list()
    print(pmid_list[0:50])
