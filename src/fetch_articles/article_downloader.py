from loguru import logger
from src.fetch_articles.pmcid_converter import get_unique_pmcids
from Bio import Entrez
import os
import json
from tqdm import tqdm

def fetch_pmc_content(pmcid):
    try:
        handle = Entrez.efetch(db="pmc", id=pmcid, rettype="full", retmode="xml")
        record = handle.read()
        handle.close()
        return record
    except Exception as e:
        print(f"An error occurred while fetching content for PMCID {pmcid}: {e}")
        return None
    
def update_downloaded_pmcids() -> None:
    """
    Update the downloaded_pmcids.json file with PMCIDs found in the saved_data/articles directory.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    downloaded_pmcids_path = os.path.join(base_dir, "saved_data", "downloaded_pmcids.json")
    # Check for all the filenames in the saved_data/articles directory
    articles_dir = os.path.join(base_dir, "saved_data", "articles")
    article_pmcids = [f.split(".")[0] for f in os.listdir(articles_dir)]
    article_pmcids_mapping = {pmcid: f"{pmcid}.xml" for pmcid in article_pmcids}

    logger.info(f"Found {len(article_pmcids)} existing XML files in {articles_dir}")
    # Add the new PMCIDs to the json file
    if os.path.exists(downloaded_pmcids_path):
        with open(downloaded_pmcids_path, "r") as f:
            try:
                downloaded_pmcids = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error loading {downloaded_pmcids_path}. Creating new json file.")
                downloaded_pmcids = {}
    else:
        downloaded_pmcids = {}
    downloaded_pmcids.update(article_pmcids_mapping)
    with open(downloaded_pmcids_path, "w") as f:
        json.dump(downloaded_pmcids, f)
    logger.info(f"Updated {downloaded_pmcids_path} with {len(article_pmcids)} new PMCIDs")

def download_articles(pmcids: list[str]):
    """
    Download articles from PubMed Central using PMCIDs.
    Keeps track of the PMCIDs that have been downloaded and skips them.
    Saves the downloaded articles to the saved_data/articles directory.

    Args:
        pmcids (list[str]): List of PMCIDs to download.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    saved_dir = os.path.join(base_dir, "saved_data", "articles")
    os.makedirs(saved_dir, exist_ok=True)

    # Load the downloaded PMCIDs from the json file
    downloaded_pmcids_path = os.path.join(base_dir, "saved_data", "downloaded_pmcids.json")
    if os.path.exists(downloaded_pmcids_path):
        with open(downloaded_pmcids_path, "r") as f:
            downloaded_pmcids = json.load(f)
    else:
        downloaded_pmcids = {}

    new_pmcids = [pmcid for pmcid in pmcids if pmcid not in downloaded_pmcids]
    logger.warning(f"{len(downloaded_pmcids)} existing articles found")
    logger.info(f"{len(new_pmcids)} new articles to download")
    
    # Download the articles
    for pmcid in tqdm(new_pmcids):
        record = fetch_pmc_content(pmcid)
        if record:
            with open(os.path.join(saved_dir, f"{pmcid}.xml"), "w") as f:
                f.write(record.decode('utf-8'))
            downloaded_pmcids[pmcid] = f"{pmcid}.xml"
        else:
            downloaded_pmcids[pmcid] = None
            logger.warning(f"No record found for PMCID {pmcid}")
    logger.info(f"Downloaded {len(downloaded_pmcids)} articles")

    # Save the downloaded PMCIDs to a json file
    with open(os.path.join(base_dir, "saved_data", "downloaded_pmcids.json"), "w") as f:
        json.dump(downloaded_pmcids, f)

if __name__ == "__main__":
    update_downloaded_pmcids()
    pmcids = get_unique_pmcids()
    download_articles(pmcids)

