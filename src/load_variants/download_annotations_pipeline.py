from loguru import logger
from src.load_variants.load_clinical_variants import download_and_extract_variant_annotations, load_raw_annotations, get_pmid_list

def variant_annotations_pipeline():
    """
    Loads the variant annotations tsv file and saves the unique PMIDs to a json file.
    """
    # Download and extract the variant annotations
    logger.info("Downloading and extracting variant annotations...")
    download_and_extract_variant_annotations()

    # Load the variant annotations
    logger.info("Loading variant annotations...")
    df = load_raw_annotations()

    # Get the PMIDs
    logger.info("Getting PMIDs...")
    pmid_list = get_pmid_list()
    logger.info(f"Number of unique PMIDs: {len(pmid_list)}")


if __name__ == "__main__":
    variant_annotations_pipeline()