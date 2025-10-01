"""
1. Download the latest data from ClinPGx (void) --> filepath
2. Filter out for the PMCIDs that are of interest for the benchmark (filepath) --> 
3. Save the data to a jsonl file
"""

from pathlib import Path
from typing import List
from .clingpx_download import download_variant_annotations
from .pmcid_converter import PMIDConverter
import json
import pandas as pd


def download_latest_data(data_dir: Path, override=False) -> Path:
    """
    Download the latest data from ClinPGx
    """
    return download_variant_annotations(data_dir, override=False)

def get_all_pmids(annotation_dir: Path, output_dir: Path) -> Path:
    """
    Get all the PMCIDs from the data and save to a txt file all_pmids.txt
    """
    pmids = set()

    # Files that have PMID column directly
    files_with_pmid = [
        'var_drug_ann.tsv',
        'var_pheno_ann.tsv',
        'var_fa_ann.tsv'
    ]

    for file in files_with_pmid:
        df = pd.read_csv(
            annotation_dir / file,
            sep='\t',
            usecols=['PMID'],  # Only load the PMID column
            low_memory=False
        )
        pmids.update(df['PMID'].dropna().astype(str))  # Add to set, drop NaN values, convert to string

    # save to a txt file
    output_file = output_dir / "all_pmids.txt"
    with open(output_file, 'w') as f:
        for pmid in pmids:
            f.write(pmid + '\n')
    return output_file

def convert_pmids_to_pmcids(pmids: Path, output_dir: Path) -> Path:
    """
    Convert PMIDs to PMCIDs and save to a mapping file mapped_pmcids.json
    """

    pmcid_converter = PMIDConverter()
    output_file = output_dir / "mapped_pmcids.json"
    mapped_pmcids = pmcid_converter.convert_from_file(pmids, output_file)
    return output_file

if __name__ == "__main__":
    data_dir = Path('data/next_data/')
    download_latest_data(data_dir, override=False)
    annotation_dir = data_dir / "variantAnnotations"
    output_dir = data_dir
    pmids = get_all_pmids(annotation_dir, output_dir)
    convert_pmids_to_pmcids(pmids, output_dir)