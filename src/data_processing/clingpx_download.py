import requests
import zipfile
import os
from pathlib import Path

def download_variant_annotations(base_dir='data/', override=False) -> Path:
    """
    Download a zip file from a URL and extract its contents.

    Args:
        base_dir: Base directory where files will be downloaded and extracted (default: current directory)
        override: If True, download and extract even if files already exist (default: False)
    """
    url = "https://api.clinpgx.org/v1/download/file/data/variantAnnotations.zip"

    # Create paths
    download_path = os.path.join(base_dir, 'variantAnnotations.zip')
    extract_to = os.path.join(base_dir, 'variantAnnotations')

    # Check if files already exist
    if os.path.exists(extract_to) and os.listdir(extract_to) and not override:
        print(f"Files already exist in {extract_to}. Skipping download.")
        print(f"Use override=True to re-download.")
        return Path(extract_to)

    # Create directories if they don't exist
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    Path(extract_to).mkdir(parents=True, exist_ok=True)

    print(f"Downloading file from {url}...")
    
    # Download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an error for bad status codes
    
    # Save the downloaded file
    with open(download_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Download complete! File saved as {download_path}")
    print(f"File size: {os.path.getsize(download_path) / (1024*1024):.2f} MB")
    
    # Unzip the file
    print(f"\nExtracting files to {extract_to}...")
    with zipfile.ZipFile(download_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # List extracted files
    extracted_files = os.listdir(extract_to)
    print(f"\nExtraction complete! {len(extracted_files)} file(s) extracted:")
    for file in extracted_files:
        file_path = os.path.join(extract_to, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path) / (1024*1024)
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