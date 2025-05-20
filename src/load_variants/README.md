# Load Data Module

This module handles the loading and preprocessing of PharmGKB clinical variants data.

## Methods

1. **`download_and_extract_variant_annotations(override: bool = False)`**
   - Downloads and extracts the variant annotations ZIP file from PharmGKB
   - Saves data to `data/variantAnnotations/`
   - Can override existing downloads if needed

2. **`load_raw_variant_annotations(override: bool = False)`**
   - Loads the variant annotations TSV file into a pandas DataFrame
   - Automatically downloads data if not present
   - Returns the DataFrame containing variant-drug annotations

3. **`unique_variants(df: pd.DataFrame)`**
   - Helper function that generates a dictionary of unique values for each column
   - Used for data analysis and validation

4. **`get_pmid_list(override: bool = False)`**
   - Main function to extract PMIDs from the variant annotations
   - Returns a list of unique PMIDs
   - Caches results in `data/pmid_list.json`
   - Used as input for PMCID conversion

The module handles all data downloading, extraction, and preprocessing steps needed to get the PMID list for subsequent steps in the pipeline.

