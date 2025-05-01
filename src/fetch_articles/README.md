# PubMed Document Fetching
## Goal
Given a PMID, fetch the paper from PubMed. Ignore papers where there are paywall issues

## Process Overview
1. Download the zip of variants from pharmgkb (handled in load_data module)
2. Get a PMID list from the variants tsv (column PMID) (handled in load_data module)
3. Convert the PMID to PMCID 
4. Fetch the content from the PMCID

## Saved Data
pmcid_mapping.json: Maps the PMID to the PMCID {"PMID": "PMCID" or Null, ..}
unique_pmcids.json: List of all the unique PMCIDs from pmcid_mapping.json (["PMCID1", "PMCID2", ...])