import requests
import zipfile
import os
from pathlib import Path
import time


def download_variant_annotations(base_dir=Path("data"), override=False) -> Path:
    """
    Download a zip file from a URL and extract its contents.

    Args:
        base_dir: Base directory where files will be downloaded and extracted (default: current directory)
        override: If True, download and extract even if files already exist (default: False)
    """
    url = "https://api.clinpgx.org/v1/download/file/data/variantAnnotations.zip"

    # Create paths
    download_path = Path(base_dir) / "variantAnnotations.zip"
    extract_to = Path(base_dir) / "variantAnnotations"

    # Check if files already exist
    if extract_to.exists() and extract_to.is_dir() and not override:
        print(f"Files already exist in {extract_to}. Skipping download.")
        print(f"Use override=True to re-download.")
        return Path(extract_to)

    # Create directories if they don't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    extract_to.mkdir(parents=True, exist_ok=True)

    print(f"Downloading file from {url}...")

    # Download the file
    for attempt in range(5):  # Retry up to 5 times
        response = requests.get(url, stream=True)
        if response.status_code == 503:
            print("Service unavailable (503). Retrying in 5 seconds...")
            time.sleep(5)  # Wait for 5 seconds before retrying
        else:
            response.raise_for_status()  # Raise an error for other bad status codes
            break  # Exit loop if the request was successful

    # Save the downloaded file
    with open(download_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Download complete! File saved as {download_path}")
    print(f"File size: {os.path.getsize(download_path) / (1024*1024):.2f} MB")

    # Unzip the file
    print(f"\nExtracting files to {extract_to}...")
    with zipfile.ZipFile(download_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    # List extracted files
    extracted_files = list(os.listdir(extract_to))
    print(f"\nExtraction complete! {len(extracted_files)} file(s) extracted:")
    for file in extracted_files:
        file_path = os.path.join(extract_to, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  - {file} ({size:.2f} MB)")
        else:
            print(f"  - {file} (directory)")

    # Remove the zip file after extraction
    os.remove(download_path)
    print(f"\nRemoved {download_path}")

    return extract_to


if __name__ == "__main__":

    try:
        download_variant_annotations()
        print("\nSuccess!")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
    except zipfile.BadZipFile:
        print("Error: The downloaded file is not a valid zip file")
    except Exception as e:
        print(f"An error occurred: {e}")
