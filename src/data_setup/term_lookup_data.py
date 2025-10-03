"""
Term Lookup Data Preparation
----------------------------

Always download the latest drug and variant term tables from PharmGKB's public
API and materialize lightweight TSVs under `<data_dir>/term_lookup_info/` for
use by the ontology search utilities.

Generated files:
- `<data_dir>/term_lookup_info/drugs.tsv` with columns:
  - Name, PharmGKB Accession Id, Generic Names, Trade Names, RxNorm Identifiers
- `<data_dir>/term_lookup_info/variants.tsv` with columns:
  - Variant Name, Variant ID, Synonyms

Notes:
- This function overwrites existing TSVs on each run to ensure fresh data.
- Network access is required; if the PharmGKB API is unavailable, a
  RuntimeError is raised.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Dict, Any
import requests
import pandas as pd
import shutil


# ClinPGx data sources (see `src/data_setup/README.MD`)
CLINPGX_DRUGS_ZIP_URL = "https://api.clinpgx.org/v1/download/file/data/drugs.zip"
CLINPGX_VARIANTS_ZIP_URL = "https://api.clinpgx.org/v1/download/file/data/variants.zip"
CLINPGX_CHEMICALS_ZIP_URL = (
    "https://api.clinpgx.org/v1/download/file/data/chemicals.zip"
)


def _flatten_list(values: Any, sep: str = ", ") -> str:
    if values is None:
        return ""
    if isinstance(values, (list, tuple, set)):
        # Cast items to str and strip whitespace
        return sep.join(str(v).strip() for v in values if str(v).strip())
    # If it's a single value (string), return as-is
    return str(values).strip()


def _extract_rxnorm_ids(xrefs: Any) -> str:
    """Extract RxNorm identifiers from PharmGKB xrefs list."""
    if not isinstance(xrefs, Iterable) or isinstance(xrefs, (str, bytes)):
        return ""
    rxnorm_ids: List[str] = []
    for x in xrefs:
        try:
            resource = (x.get("resource") or x.get("type") or "").lower()
            if "rxnorm" in resource:
                # Common keys: 'id', 'ids' (list), 'acc'
                if isinstance(x.get("ids"), list):
                    rxnorm_ids.extend(str(i) for i in x["ids"] if str(i).strip())
                elif x.get("id") is not None:
                    rxnorm_ids.append(str(x["id"]))
                elif x.get("acc") is not None:
                    rxnorm_ids.append(str(x["acc"]))
        except Exception:
            continue
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: List[str] = []
    for rid in rxnorm_ids:
        if rid not in seen:
            seen.add(rid)
            deduped.append(rid)
    return ", ".join(deduped)


def _request_json(url: str, timeout: int = 60) -> Dict[str, Any]:
    """Legacy helper retained for compatibility; not used in new ClinPGx flow."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _robust_download(url: str, dest: Path, retries: int = 5, timeout: int = 60) -> Path:
    """Download a URL to dest with simple retry logic. Returns dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        resp = requests.get(url, stream=True, timeout=timeout)
        if resp.status_code == 503 and attempt < retries:
            # transient service unavailable, retry
            import time

            time.sleep(5)
            continue
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return dest
    raise RuntimeError(f"Failed to download after {retries} attempts: {url}")


def _extract_zip(zip_path: Path, extract_to: Path) -> Path:
    import zipfile

    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
    return extract_to


def _find_first_tsv(base: Path, preferred_names: List[str]) -> Path | None:
    """Search for a TSV/CSV file under base, preferring filenames in preferred_names."""
    candidates: List[Path] = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".tsv", ".csv"}:
            candidates.append(p)
    if not candidates:
        return None
    # Prefer exact matches first
    lower_map = {p.name.lower(): p for p in candidates}
    for name in preferred_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    # Otherwise, pick the first
    return sorted(candidates)[0]


def _normalize_drugs_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure drugs dataframe has the expected columns used by ontology search."""
    # Try to map common column variants to expected names
    colmap = {
        "pharmgkb accession id": "PharmGKB Accession Id",
        "pharmgkb_accession_id": "PharmGKB Accession Id",
        "pharmgkb_id": "PharmGKB Accession Id",
        "id": "PharmGKB Accession Id",
        "name": "Name",
        "generic names": "Generic Names",
        "genericnames": "Generic Names",
        "trade names": "Trade Names",
        "tradenames": "Trade Names",
        "rxnorm identifiers": "RxNorm Identifiers",
        "rxnorm_ids": "RxNorm Identifiers",
        "rxnorm": "RxNorm Identifiers",
    }
    renamed = {c: colmap.get(c.lower(), c) for c in df.columns}
    df = df.rename(columns=renamed)
    # Create missing columns if necessary
    for c in [
        "PharmGKB Accession Id",
        "Name",
        "Generic Names",
        "Trade Names",
        "RxNorm Identifiers",
    ]:
        if c not in df.columns:
            df[c] = ""
    return df[
        [
            "PharmGKB Accession Id",
            "Name",
            "Generic Names",
            "Trade Names",
            "RxNorm Identifiers",
        ]
    ].copy()


def _normalize_variants_df(df: pd.DataFrame) -> pd.DataFrame:
    colmap = {
        "variant id": "Variant ID",
        "variant_id": "Variant ID",
        "id": "Variant ID",
        "variant name": "Variant Name",
        "symbol": "Variant Name",
        "name": "Variant Name",
        "synonyms": "Synonyms",
        "alternative names": "Synonyms",
        "alternative_names": "Synonyms",
    }
    renamed = {c: colmap.get(c.lower(), c) for c in df.columns}
    df = df.rename(columns=renamed)
    for c in ["Variant Name", "Variant ID", "Synonyms"]:
        if c not in df.columns:
            df[c] = ""
    return df[["Variant Name", "Variant ID", "Synonyms"]].copy()


def _download_drugs_df(data_dir: Path) -> pd.DataFrame:
    tmp_dir = data_dir / "_tmp_lookup_downloads/drugs"
    zip_path = tmp_dir / "drugs.zip"
    _robust_download(CLINPGX_DRUGS_ZIP_URL, zip_path)
    extracted = _extract_zip(zip_path, tmp_dir / "extracted")
    # Prefer a file named 'drugs.tsv' or 'drugs.csv'
    tsv = _find_first_tsv(extracted, ["drugs.tsv", "drugs.csv"])
    if tsv is None:
        raise RuntimeError(
            f"No TSV/CSV found in downloaded drugs archive from {CLINPGX_DRUGS_ZIP_URL}"
        )
    df = pd.read_csv(
        tsv, sep="\t" if tsv.suffix.lower() == ".tsv" else ",", low_memory=False
    )
    return _normalize_drugs_df(df)


def _download_variants_df(data_dir: Path) -> pd.DataFrame:
    tmp_dir = data_dir / "_tmp_lookup_downloads/variants"
    zip_path = tmp_dir / "variants.zip"
    _robust_download(CLINPGX_VARIANTS_ZIP_URL, zip_path)
    extracted = _extract_zip(zip_path, tmp_dir / "extracted")
    # Prefer a file named 'variants.tsv' or 'variants.csv'
    tsv = _find_first_tsv(extracted, ["variants.tsv", "variants.csv"])
    if tsv is None:
        # Some archives may name the file 'chemicals' or similar; try fallback list
        tsv = _find_first_tsv(extracted, ["variant.tsv", "variant.csv"])  # alt naming
    if tsv is None:
        raise RuntimeError(
            f"No TSV/CSV found in downloaded variants archive from {CLINPGX_VARIANTS_ZIP_URL}"
        )
    df = pd.read_csv(
        tsv, sep="\t" if tsv.suffix.lower() == ".tsv" else ",", low_memory=False
    )
    # Try to coerce list-like synonyms to string
    if "synonyms" in df.columns:
        df["synonyms"] = df["synonyms"].apply(_flatten_list)
    return _normalize_variants_df(df)


def prepare_term_lookup_data(data_dir: str | Path) -> Path:
    """
    Download and write fresh drug and variant lookup TSVs to `<data_dir>/term_lookup_info`.

    This always overwrites existing files to ensure the latest data are used.

    Args:
        data_dir: Base data directory that will contain `term_lookup_info/`.

    Returns:
        Path: The `<data_dir>/term_lookup_info` directory path containing new TSVs.
    """
    if isinstance(data_dir, str):
        data_dir = Path(data_dir)

    target_dir = data_dir / "term_lookup_info"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download latest data and write minimal TSVs expected by search utilities
    drugs_df = _download_drugs_df(data_dir)
    variants_df = _download_variants_df(data_dir)

    drugs_path = target_dir / "drugs.tsv"
    variants_path = target_dir / "variants.tsv"

    drugs_df.to_csv(drugs_path, sep="\t", index=False)
    variants_df.to_csv(variants_path, sep="\t", index=False)
    print(f"Wrote {len(drugs_df)} drugs to {drugs_path}")
    print(f"Wrote {len(variants_df)} variants to {variants_path}")

    # Cleanup temporary downloads directory
    tmp_dir_root = data_dir / "_tmp_lookup_downloads"
    try:
        if tmp_dir_root.exists():
            shutil.rmtree(tmp_dir_root)
    except Exception:
        # Non-fatal if cleanup fails
        pass

    return target_dir


if __name__ == "__main__":
    # Default to repository `data/` for ad-hoc runs
    prepare_term_lookup_data(Path("data"))
