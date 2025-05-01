import os
import requests
import zipfile
from io import BytesIO
import shutil
from loguru import logger
import pandas as pd

def download_and_extract_clinical_variants(override=False):
    url = "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, "saved_data")
    extract_dir = os.path.join(save_dir, "clinicalVariants")

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


def load_clinical_variants_tsv():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tsv_path = os.path.join(base_dir, "saved_data", "clinicalVariants", "clinicalVariants.tsv")

    if not os.path.exists(tsv_path):
        logger.info(f"{tsv_path} not found. Downloading data...")
        download_and_extract_clinical_variants()

    if not os.path.exists(tsv_path):
        logger.error(f"File still not found after download attempt: {tsv_path}")
        raise FileNotFoundError(f"File still not found after download attempt: {tsv_path}")

    logger.info(f"Loading TSV from: {tsv_path}")
    df = pd.read_csv(tsv_path, sep='\t')
    return df


if __name__ == "__main__":
    df = load_clinical_variants_tsv()
    print(df.head())
