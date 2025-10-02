import requests
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os

load_dotenv()

class PMIDConverter:
    """Efficient batch converter for PMIDs to PMCIDs using NCBI ID Converter API"""
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    BATCH_SIZE = 200  # API maximum
    RATE_LIMIT_DELAY = 0.34  # ~3 requests per second to be safe
    
    def __init__(self, email: Optional[str] = None, tool: str = "pmid_converter"):
        """
        Initialize converter
        
        Args:
            email: Your email (recommended by NCBI for tracking)
            tool: Tool name for API tracking
        """
        self.email = email
        self.tool = tool
        self.session = requests.Session()
    
    def _build_params(self, pmids: List[str], format: str = "json") -> Dict:
        """Build API request parameters"""
        params = {
            "ids": ",".join(str(p) for p in pmids),
            "format": format,
            "tool": self.tool
        }
        if self.email:
            params["email"] = self.email
        return params
    
    def _parse_response(self, data: Dict) -> Dict[str, str]:
        """Parse API response and extract PMID -> PMCID mappings"""
        mapping = {}
        
        if "records" in data:
            for record in data["records"]:
                pmid = record.get("pmid")
                pmcid = record.get("pmcid")

                # Normalize to strings to avoid type mismatches (e.g., int vs str)
                if pmid is not None:
                    pmid = str(pmid).strip()
                if pmcid is not None:
                    pmcid = str(pmcid).strip()

                if pmid and pmcid:
                    mapping[pmid] = pmcid
        
        return mapping
    
    def _convert_batch(self, pmids: List[str]) -> tuple[Dict[str, str], Set[str]]:
        """
        Convert a single batch of PMIDs to PMCIDs (internal method)

        Args:
            pmids: List of PMIDs (max 200)

        Returns:
            Tuple of (Dictionary mapping PMID -> PMCID, Set of PMIDs not found)
        """
        if len(pmids) > self.BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {self.BATCH_SIZE}")

        params = self._build_params(pmids)

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            mappings = self._parse_response(data)

            # Identify PMIDs that were not found (normalize everything to string)
            batch_ids = set(str(p).strip() for p in pmids)
            found_ids = set(str(k).strip() for k in mappings.keys())
            not_found = batch_ids - found_ids
            return mappings, not_found

        except requests.exceptions.RequestException as e:
            print(f"Error converting batch: {e}")
            return {}, set()
    
    def convert(self, pmids: List[str], show_progress: bool = True) -> Dict[str, str]:
        """
        Convert a list of PMIDs to PMCIDs (in-memory only)

        Args:
            pmids: List of PMIDs to convert
            show_progress: Whether to print progress updates

        Returns:
            Dictionary mapping PMID -> PMCID for all successfully converted IDs
        """
        # Remove duplicates while preserving order
        unique_pmids = list(dict.fromkeys(str(p) for p in pmids))

        # Split into batches
        batches = [
            unique_pmids[i:i + self.BATCH_SIZE]
            for i in range(0, len(unique_pmids), self.BATCH_SIZE)
        ]

        all_mappings = {}
        total_batches = len(batches)

        if show_progress:
            print(f"Converting {len(unique_pmids)} PMIDs in {total_batches} batches...")

        for idx, batch in enumerate(batches, 1):
            mappings, not_found = self._convert_batch(batch)
            all_mappings.update(mappings)

            if show_progress:
                converted = len(mappings)
                print(f"Batch {idx}/{total_batches}")

            # Rate limiting (except for last batch)
            if idx < total_batches:
                time.sleep(self.RATE_LIMIT_DELAY)

        if show_progress:
            success_rate = len(all_mappings) / len(unique_pmids) * 100 if unique_pmids else 0
            print(f"\nTotal: {len(all_mappings)}/{len(unique_pmids)} converted ({success_rate:.1f}%)")

        return all_mappings
    
    def convert_from_file(self, input_file_path: Path, output_path: Path,
                         override: bool = False, show_progress: bool = True) -> Path:
        """
        Convert PMIDs from an input file and save to output JSON file

        Args:
            input_file: Path to file containing PMIDs (one per line, or JSON list)
            output_file: Path to output JSON file for mappings
            override: If False, skip already converted PMIDs (including those not found)
            show_progress: Whether to print progress updates

        Returns:
            Dictionary mapping PMID -> PMCID for all IDs (not found PMIDs map to None)
        """
        output_file_path = output_path / "pmcid_mapping.json"

        # Read PMIDs from input file
        if show_progress:
            print(f"Reading PMIDs from {input_file_path}...")

        pmids = self._read_pmids_from_file(input_file_path)

        if show_progress:
            print(f"Found {len(pmids)} PMIDs in input file")

        # Load existing mappings if file exists and not overriding
        existing_mappings = {}
        if not override and output_file_path.exists():
            try:
                with open(output_file_path, 'r') as f:
                    existing_mappings = json.load(f)
                if show_progress:
                    print(f"Loaded {len(existing_mappings)} existing mappings from {output_file_path}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load existing file: {e}")

        # Remove duplicates and filter out already converted PMIDs (including those marked as not found)
        unique_pmids = list(dict.fromkeys(str(p) for p in pmids))

        if not override and existing_mappings:
            pmids_to_convert = [p for p in unique_pmids if p not in existing_mappings]
            skipped = len(unique_pmids) - len(pmids_to_convert)
            if show_progress and skipped > 0:
                print(f"Skipping {skipped} already processed PMIDs")
        else:
            pmids_to_convert = unique_pmids

        # If nothing to convert, ensure we still return the output file path
        if not pmids_to_convert:
            if show_progress:
                print("All PMIDs already processed!")
            # Ensure the expected output file exists and return its path
            # If it already existed, we keep it; otherwise, create from existing_mappings
            if not output_file_path.exists():
                self._save_mappings(existing_mappings, output_file_path)
            return output_file_path

        # Split into batches
        batches = [
            pmids_to_convert[i:i + self.BATCH_SIZE]
            for i in range(0, len(pmids_to_convert), self.BATCH_SIZE)
        ]

        all_mappings = existing_mappings.copy()
        total_batches = len(batches)
        total_converted = 0
        total_not_found = 0

        if show_progress:
            print(f"Converting {len(pmids_to_convert)} new PMIDs in {total_batches} batches...")

        for idx, batch in enumerate(batches, 1):
            mappings, not_found = self._convert_batch(batch)
            all_mappings.update(mappings)

            # Store not found PMIDs with None value
            for pmid in not_found:
                all_mappings[pmid] = None

            total_converted += len(mappings)
            total_not_found += len(not_found)

            # Save incrementally after each batch
            self._save_mappings(all_mappings, output_file_path)

            if show_progress:
                print(f"Batch {idx}/{total_batches}: {total_converted} converted, {total_not_found} not found")

            # Rate limiting (except for last batch)
            if idx < total_batches:
                time.sleep(self.RATE_LIMIT_DELAY)

        if show_progress:
            new_conversions = total_converted
            new_not_found = total_not_found
            print(f"\nNew conversions: {new_conversions}/{len(pmids_to_convert)}")
            print(f"Not found: {new_not_found}/{len(pmids_to_convert)}")
            print(f"Total mappings: {len(all_mappings)}")
            print(f"Results saved to {output_file_path}")

        return output_file_path
    
    def _read_pmids_from_file(self, input_file: Path) -> List[str]:
        """
        Read PMIDs from a file (supports text file with one PMID per line, or JSON list)
        
        Args:
            input_file: Path to input file
            
        Returns:
            List of PMID strings
        """
        input_file = Path(input_file)
        
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Try to read as JSON first
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(p).strip() for p in data if str(p).strip()]
        except json.JSONDecodeError:
            pass
        
        # Read as text file (one PMID per line)
        with open(input_file, 'r') as f:
            pmids = [line.strip() for line in f if line.strip()]
        
        return pmids
    
    def _save_mappings(self, mappings: Dict[str, str], output_file: Path) -> None:
        """
        Save PMID -> PMCID mappings to a JSON file (internal method)
        
        Args:
            mappings: Dictionary of PMID -> PMCID mappings
            output_file: Path object for output JSON file
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(mappings, f, indent=2)
    
    def load_mappings(self, input_file: Path) -> Dict[str, str]:
        """
        Load PMID -> PMCID mappings from a JSON file
        
        Args:
            input_file: Path object for input JSON file
            
        Returns:
            Dictionary of PMID -> PMCID mappings
        """
        input_file = Path(input_file)
        
        if not input_file.exists():
            raise FileNotFoundError(f"File not found: {input_file}")
        
        with open(input_file, 'r') as f:
            return json.load(f)


# Example usage
if __name__ == "__main__":
    # Initialize converter (add your email for NCBI tracking)
    converter = PMIDConverter(email="your.email@example.com")
    
    # Example PMIDs
    pmids = [
        "32948745", "33495752", "33495753", "33495754", 
        "33495755", "20210808", "19008416", "18771397"
    ]
    
    print("=== Method 1: convert() - In-memory list conversion ===")
    # Simple in-memory conversion
    results = converter.convert(pmids)
    print(f"\nSample results:")
    for pmid, pmcid in list(results.items())[:3]:
        print(f"PMID {pmid} -> {pmcid}")
    
    print("\n=== Method 2: convert_from_file() - File-based conversion ===")
    
    # Create example input file
    input_path = Path("pmids_input.txt")
    with open(input_path, 'w') as f:
        for pmid in pmids * 10:  # Simulate 80 PMIDs
            f.write(f"{pmid}\n")
    
    # First run - converts all PMIDs and saves to file
    output_path = Path("pmid_mappings.json")
    all_results = converter.convert_from_file(input_path, output_path)
    
    # Second run - add more PMIDs to input file, only converts new ones
    print("\n=== Adding more PMIDs (incremental update) ===")
    with open(input_path, 'a') as f:
        f.write("35000000\n35000001\n")
    
    all_results = converter.convert_from_file(input_path, output_path, override=False)
    
    # Third run - force re-conversion with override=True
    print("\n=== Force override (re-converts everything) ===")
    # all_results = converter.convert_from_file(input_path, output_path, override=True)
    
    # Load existing mappings
    print("\n=== Loading saved mappings ===")
    loaded = converter.load_mappings(output_path)
    print(f"Loaded {len(loaded)} mappings from file")