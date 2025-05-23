# data_download.py
# This script downloads and extracts clinical variant and variant annotation data from specified URLs.

import requests
import zipfile
import io
from config import CLINICAL_VARIANTS_URL, VARIANT_ANNOTATIONS_URL

def download_and_extract_zip(url, extract_path):
    """Download and extract a ZIP file from the given URL."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(extract_path)
        print(f"Successfully downloaded and unpacked {url} to {extract_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file from {url}: {e}")
    except zipfile.BadZipFile as e:
        print(f"Error unpacking the zip file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")