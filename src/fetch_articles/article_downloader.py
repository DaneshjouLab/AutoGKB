from loguru import logger
from src.fetch_articles.pmcid_converter import get_unique_pmcids
from src.utils.file_paths import get_project_root
from src.variant_extraction.config import ENTREZ_EMAIL
from Bio import Entrez
import os
import json
from tqdm import tqdm

Entrez.email = ENTREZ_EMAIL

def fetch_pmc_content(pmcid):
    """
    Fetch content for a single article from PubMed Central.

    Args:
        pmcid (str): The PubMed Central ID to fetch

    Returns:
        bytes or None: The article content in XML format or None if fetching failed
    """
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
    Update the downloaded_pmcids.json file with PMCIDs found in the data/articles directory.
    """
    project_root = get_project_root()
    downloaded_pmcids_path = project_root / "data" / "downloaded_pmcids.json"

    # Check for all the filenames in the data/articles directory
    articles_dir = project_root / "data" / "articles"
    os.makedirs(articles_dir, exist_ok=True)

    article_pmcids = [f.split(".")[0] for f in os.listdir(articles_dir)]
    article_pmcids_mapping = {pmcid: f"{pmcid}.xml" for pmcid in article_pmcids}

    logger.info(f"Found {len(article_pmcids)} existing XML files in {articles_dir}")

    # Add the new PMCIDs to the json file
    if os.path.exists(downloaded_pmcids_path):
        with open(downloaded_pmcids_path, "r") as f:
            try:
                downloaded_pmcids = json.load(f)
            except json.JSONDecodeError:
                logger.error(
                    f"Error loading {downloaded_pmcids_path}. Creating new json file."
                )
                downloaded_pmcids = {}
    else:
        downloaded_pmcids = {}

    downloaded_pmcids.update(article_pmcids_mapping)

    with open(downloaded_pmcids_path, "w") as f:
        json.dump(downloaded_pmcids, f)

    logger.info(
        f"Updated {downloaded_pmcids_path} with {len(article_pmcids)} new PMCIDs"
    )


def download_articles(pmcids: list[str]):
    """
    Download articles from PubMed Central using PMCIDs.
    Keeps track of the PMCIDs that have been downloaded and skips them.
    Saves the downloaded articles to the data/articles directory.

    Args:
        pmcids (list[str]): List of PMCIDs to download.
    """
    project_root = get_project_root()
    articles_dir = project_root / "data" / "articles"
    os.makedirs(articles_dir, exist_ok=True)

    # Load the downloaded PMCIDs from the json file
    downloaded_pmcids_path = project_root / "data" / "downloaded_pmcids.json"

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
            with open(articles_dir / f"{pmcid}.xml", "w") as f:
                f.write(record.decode("utf-8"))
            downloaded_pmcids[pmcid] = f"{pmcid}.xml"
        else:
            downloaded_pmcids[pmcid] = None
            logger.warning(f"No record found for PMCID {pmcid}")

    logger.info(
        f"Downloaded {len(new_pmcids)} new articles, total articles: {len(downloaded_pmcids)}"
    )

    # Save the downloaded PMCIDs to a json file
    with open(downloaded_pmcids_path, "w") as f:
        json.dump(downloaded_pmcids, f)


if __name__ == "__main__":
    update_downloaded_pmcids()
    pmcids = get_unique_pmcids()
    download_articles(pmcids)
