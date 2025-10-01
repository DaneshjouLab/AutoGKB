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

def convert_pmids_to_pmcids(pmids: Path, output_dir: Path, override: bool = False) -> Path:
    """
    Convert PMIDs to PMCIDs and save to a mapping file mapped_pmcids.json
    """

    pmcid_converter = PMIDConverter()
    output_file = output_dir / "mapped_pmcids.json"
    mapped_pmcids = pmcid_converter.convert_from_file(pmids, output_file, override=override)
    return output_file

def create_pmcid_groupings(annotation_dir: Path, pmcid_mapping: Path, output_dir: Path) -> Path:
    """
    Create the pmcid groupings from the annotations
    """
    # Load the PMID to PMCID mapping
    with open(pmcid_mapping, 'r') as f:
        pmid_to_pmcid = json.load(f)

    # Load all the dataframes
    study_params = pd.read_csv(annotation_dir / "study_parameters.tsv", sep='\t', low_memory=False)
    var_drug_ann = pd.read_csv(annotation_dir / "var_drug_ann.tsv", sep='\t', low_memory=False)
    var_pheno_ann = pd.read_csv(annotation_dir / "var_pheno_ann.tsv", sep='\t', low_memory=False)
    var_fa_ann = pd.read_csv(annotation_dir / "var_fa_ann.tsv", sep='\t', low_memory=False)

    # Group annotations by PMCID
    annotations_by_pmcid = {}

    # Get unique PMIDs from variant annotations
    all_pmids = set()
    all_pmids.update(var_drug_ann['PMID'].dropna().astype(int))
    all_pmids.update(var_pheno_ann['PMID'].dropna().astype(int))
    all_pmids.update(var_fa_ann['PMID'].dropna().astype(int))

    for pmid in all_pmids:
        pmid_str = str(pmid)
        pmcid = pmid_to_pmcid.get(pmid_str)

        if not pmcid:
            continue

        # Get variant annotations for this PMID
        drug_anns = var_drug_ann[var_drug_ann['PMID'] == pmid]
        pheno_anns = var_pheno_ann[var_pheno_ann['PMID'] == pmid]
        fa_anns = var_fa_ann[var_fa_ann['PMID'] == pmid]

        # Get study parameters by joining on Variant Annotation ID
        variant_annotation_ids = set()
        variant_annotation_ids.update(drug_anns['Variant Annotation ID'].dropna())
        variant_annotation_ids.update(pheno_anns['Variant Annotation ID'].dropna())
        variant_annotation_ids.update(fa_anns['Variant Annotation ID'].dropna())

        study_params_for_pmid = study_params[study_params['Variant Annotation ID'].isin(variant_annotation_ids)]

        # Create entry for this PMCID
        entry = {
            "pmid": pmid,
            "study_parameters": study_params_for_pmid.to_dict('records'),
            "var_drug_ann": drug_anns.to_dict('records'),
            "var_pheno_ann": pheno_anns.to_dict('records'),
            "var_fa_ann": fa_anns.to_dict('records')
        }

        annotations_by_pmcid[pmcid] = entry

    # Save to JSON file
    output_file = output_dir / "annotations_by_pmcid.json"
    with open(output_file, 'w') as f:
        json.dump(annotations_by_pmcid, f, indent=2)

    print(f"Created {len(annotations_by_pmcid)} PMCID groupings in {output_file}")
    return output_file

if __name__ == "__main__":
    data_dir = Path('data/next_data/')
    download_latest_data(data_dir, override=False)
    annotation_dir = data_dir / "variantAnnotations"
    output_dir = data_dir
    pmids = get_all_pmids(annotation_dir, output_dir)
    convert_pmids_to_pmcids(pmids, output_dir, override=False)
    create_pmcid_groupings(annotation_dir, output_dir / "mapped_pmcids.json", output_dir)
    