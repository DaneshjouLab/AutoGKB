"""
1. Download the latest data from ClinPGx (void) --> filepath
2. Filter out for the PMCIDs that are of interest for the benchmark (filepath) --> 
3. Save the data to a jsonl file
"""

from pathlib import Path
from typing import Set
from .clingpx_download import download_variant_annotations
from .pmcid_converter import PMIDConverter
import json
import math
import pandas as pd
import numpy as np
from src.utils import get_article_text, get_title


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

def _normalize_pmid_series(series: pd.Series) -> pd.Series:
    """Return a string PMID series with only digit characters; invalid entries set to NA."""
    # Cast to string, extract contiguous digits, drop empty matches
    s = series.astype(str)
    s = s.replace({"nan": np.nan, "None": np.nan})
    s = s.str.extract(r"(\d+)", expand=False)
    return s


def _normalize_id_series(series: pd.Series) -> pd.Series:
    """Return an ID series as strings; NaNs preserved as NA."""
    s = series.astype(str)
    s = s.replace({"nan": np.nan, "None": np.nan})
    s = s.str.strip()
    s = s.where(s.ne(""))
    return s


def _clean_nans(obj):
    """Recursively replace NaN/Inf/pandas NA with None in nested structures."""
    # Handle dict
    if isinstance(obj, dict):
        return {k: _clean_nans(v) for k, v in obj.items()}
    # Handle list/tuple
    if isinstance(obj, (list, tuple)):
        return [_clean_nans(v) for v in obj]
    # Preserve None
    if obj is None:
        return None
    # Handle pandas NA / numpy NaN / inf
    try:
        # pandas.isna handles numpy/pandas dtypes
        if pd.isna(obj):
            return None
    except Exception:
        pass
    # Also explicitly guard float nan/inf
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


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

    # Normalize PMIDs to a comparable string column (digits only)
    for df in (var_drug_ann, var_pheno_ann, var_fa_ann):
        if "PMID" in df.columns:
            df["PMID_norm"] = _normalize_pmid_series(df["PMID"])  # may be NA
        else:
            df["PMID_norm"] = np.nan

    # Normalize Variant Annotation IDs for joining
    if "Variant Annotation ID" in study_params.columns:
        study_params["Variant Annotation ID_norm"] = _normalize_id_series(
            study_params["Variant Annotation ID"]
        )
    else:
        study_params["Variant Annotation ID_norm"] = np.nan

    # Group annotations by PMCID
    annotations_by_pmcid: dict[str, dict] = {}

    # Get unique PMIDs from variant annotations
    all_pmids: Set[str] = set()
    for df in (var_drug_ann, var_pheno_ann, var_fa_ann):
        if "PMID_norm" in df.columns:
            pmids = df["PMID_norm"].dropna().astype(str).unique().tolist()
            all_pmids.update(pmids)

    for pmid_str in all_pmids:
        pmcid = pmid_to_pmcid.get(pmid_str)

        if not pmcid:
            continue

        # Get variant annotations for this PMID
        drug_anns = var_drug_ann[var_drug_ann["PMID_norm"] == pmid_str].copy()
        pheno_anns = var_pheno_ann[var_pheno_ann["PMID_norm"] == pmid_str].copy()
        fa_anns = var_fa_ann[var_fa_ann["PMID_norm"] == pmid_str].copy()

        # Get study parameters by joining on Variant Annotation ID
        variant_annotation_ids: Set[str] = set()
        for df in (drug_anns, pheno_anns, fa_anns):
            if "Variant Annotation ID" in df.columns:
                df["Variant Annotation ID_norm"] = _normalize_id_series(
                    df["Variant Annotation ID"]
                )
                variant_annotation_ids.update(
                    df["Variant Annotation ID_norm"].dropna().astype(str)
                )

        study_params_for_pmid = study_params[
            study_params["Variant Annotation ID_norm"].isin(list(variant_annotation_ids))
        ].copy()

        # Try to load study title from local markdown, if available
        title = None
        try:
            article_md = get_article_text(pmcid=pmcid, remove_references=False)
            title = get_title(article_md)
        except Exception:
            # Title is optional; skip if article markdown is unavailable
            title = None

        # Create entry for this PMCID
        entry = {
            "pmid": pmid_str,
            "title": title,
            "study_parameters": study_params_for_pmid.to_dict("records"),
            "var_drug_ann": drug_anns.to_dict("records"),
            "var_pheno_ann": pheno_anns.to_dict("records"),
            "var_fa_ann": fa_anns.to_dict("records"),
        }

        annotations_by_pmcid[pmcid] = entry

    # Save to JSON file
    output_file = output_dir / "annotations_by_pmcid.json"
    # Deep-clean any remaining NaN/Inf just before serialization
    cleaned = _clean_nans(annotations_by_pmcid)
    with open(output_file, 'w') as f:
        json.dump(cleaned, f, indent=2, allow_nan=False)

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
    
