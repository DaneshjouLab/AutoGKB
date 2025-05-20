# Data

This directory contains the primary data files used by the AutoGKB project.

## Directory Structure

- **articles/** - Contains XML files of articles from PubMed Central (PMC), identified by their PMCID (e.g., PMC1234567.xml). These articles are used for text mining and information extraction.

- **variantAnnotations/** - Contains clinical variant annotations and related data:
  - `var_drug_ann.tsv` - Variant-drug annotations. This is what is used in this repo.
  - This can be downloaded using download_and_extract_variant_annotations from the load_variants module

- **Support Files**:
  - `pmcid_mapping.json` - Maps between PMIDs and PMCIDs
  - `unique_pmcids.json` - List of unique PMCIDs in the dataset
  - `pmid_list.json` - List of PMIDs in the dataset
  - `downloaded_pmcids.json` - Tracking which PMCIDs have been downloaded