# PubMed Document Fetching
## Goal
Given a PMID, fetch the paper from PubMed. Ignore papers where there are paywall issues

## General process
1. Download the zip of variants from pharmgkb
2. Get a PMID list from the variants tsv (column PMID)
3. Convert the PMID to PMCID 
4. Fetch the content from the PMCID