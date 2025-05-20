# PubMed Document Fetching

## Goal
Given a PMID, fetch the paper from PubMed. Ignore papers where there are paywall issues.

## Process Overview
1. Download the zip of variants from pharmgkb (handled in load_data module)
2. Get a PMID list from the variants tsv (column PMID) (handled in load_data module)
3. Convert the PMID to PMCID 
4. Fetch the content from the PMCID

## Key Functions

### PMCID Converter (`pmcid_converter.py`)

- `batch_pmid_to_pmcid(pmids, email, batch_size, delay)`: Converts a list of PMIDs to PMCIDs using NCBI's ID Converter API. Processes PMIDs in batches and handles rate limiting.
  - Arguments:
    - `pmids`: List of PMIDs (as strings)
    - `email`: Your email for NCBI tool identification
    - `batch_size`: Number of PMIDs per request (max: 200)
    - `delay`: Seconds between requests (default: 0.4)
  - Returns: Dict mapping each PMID to PMCID (or None if not available)

- `get_unique_pmcids()`: Returns a list of unique PMCIDs from the PMCID mapping file.

- `load_saved_pmcid_mapping()`: Loads previously saved PMCID mappings from disk.

- `get_project_root()`: Returns the project root directory path.

### Article Downloader (`article_downloader.py`)

- `fetch_pmc_content(pmcid)`: Fetches a single article's content from PubMed Central.
  - Arguments:
    - `pmcid`: The PubMed Central ID to fetch
  - Returns: Article content in XML format or None if fetching failed

- `download_articles(pmcids)`: Downloads multiple articles from PubMed Central.
  - Arguments:
    - `pmcids`: List of PMCIDs to download
  - Saves downloaded articles to `data/articles/` as XML files
  - Tracks downloaded PMCIDs to avoid duplicating work

- `update_downloaded_pmcids()`: Updates tracking of downloaded PMCIDs from files in `data/articles/` directory.

## Created Data
- `pmcid_mapping.json`: Maps the PMID to the PMCID `{"PMID": "PMCID" or Null, ..}`
- `unique_pmcids.json`: List of all the unique PMCIDs from pmcid_mapping.json `["PMCID1", "PMCID2", ...]`
- `downloaded_pmcids.json`: Maps PMCIDs to filenames or None if download failed `{"PMCID": "PMCID.xml" or null, ..}`
- `<articles>.xml`: Downloaded articles

## Usage Examples

### Convert PMIDs to PMCIDs

```python
from src.fetch_articles.pmcid_converter import batch_pmid_to_pmcid
from src.load_data import get_pmid_list
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables (NCBI_EMAIL)

# Get list of PMIDs from variant data
pmid_list = get_pmid_list()

# Convert PMIDs to PMCIDs
pmcid_mapping = batch_pmid_to_pmcid(
    pmids=pmid_list,
    email=os.getenv("NCBI_EMAIL"),
    batch_size=100,
    delay=0.4
)

print(f"Successfully mapped {len(pmcid_mapping)} PMIDs to PMCIDs")
```

### Download Articles Using PMCIDs

```python
from src.fetch_articles.article_downloader import download_articles
from src.fetch_articles.pmcid_converter import get_unique_pmcids

# Get unique PMCIDs from saved mapping
pmcids = get_unique_pmcids()

# Download articles
download_articles(pmcids)
```

### Download a Single Article

```python
from src.fetch_articles.article_downloader import fetch_pmc_content
from src.fetch_articles.pmcid_converter import get_project_root
import os
from pathlib import Path

# Get project root
project_root = get_project_root()

# Fetch a single article
pmcid = "PMC1234567"
content = fetch_pmc_content(pmcid)

if content:
    # Save the article content
    articles_dir = project_root / "data" / "articles"
    os.makedirs(articles_dir, exist_ok=True)
    
    with open(articles_dir / f"{pmcid}.xml", "w") as f:
        f.write(content.decode("utf-8"))
    print(f"Successfully downloaded article {pmcid}")
else:
    print(f"Failed to download article {pmcid}")
```

### Update Downloaded PMCIDs

```python
from src.fetch_articles.article_downloader import update_downloaded_pmcids

# Update downloaded_pmcids.json with articles in data/articles/
update_downloaded_pmcids()
```

## Full Pipeline Execution

To run the complete pipeline (convert PMIDs to PMCIDs and download articles):

```python
# Full pipeline from PMIDs to downloaded articles
from src.fetch_articles.pmcid_converter import batch_pmid_to_pmcid
from src.fetch_articles.article_downloader import download_articles
from src.load_data import get_pmid_list
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Get PMIDs from variant data
pmid_list = get_pmid_list()

# 2. Convert PMIDs to PMCIDs
pmcid_mapping = batch_pmid_to_pmcid(pmid_list, os.getenv("NCBI_EMAIL"))

# 3. Extract only valid PMCIDs (not None)
valid_pmcids = [pmcid for pmcid in pmcid_mapping.values() if pmcid]

# 4. Download articles
download_articles(valid_pmcids)
```

Alternatively, run the module scripts directly:

```bash
# First convert PMIDs to PMCIDs
python -m src.fetch_articles.pmcid_converter

# Then download articles
python -m src.fetch_articles.article_downloader
```