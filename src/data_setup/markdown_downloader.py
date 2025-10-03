from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
import shutil

import gdown

GOOGLE_DRIVE_URL = "https://drive.google.com/file/d/1jD3okYclzYmZqLLiY7kBO0erhKm6bWBl/view"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download benchmark article markdowns, unzip to data/articles/, and clean up."
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "skip-existing", "clean"],
        default="overwrite",
        help="How to handle existing files in data/articles/.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download even if zip already exists.",
    )
    return parser.parse_args()


def download_markdown_zip(data_dir: Path, force_download: bool) -> Path:
    articles_dir = data_dir / "articles"
    # Ensure destination directory exists before download
    articles_dir.mkdir(parents=True, exist_ok=True)
    zip_path = articles_dir / "markdown.zip"

    if zip_path.exists() and not force_download:
        print(f"Zip already exists at {zip_path}. Skipping download (use --force-download to re-fetch).")
        return zip_path

    print(f"Downloading markdown zip to: {zip_path}")
    gdown.download(url=GOOGLE_DRIVE_URL, output=str(zip_path), fuzzy=True, quiet=False)

    if not zip_path.exists() or zip_path.stat().st_size == 0:
        raise RuntimeError(f"Download failed or produced an empty file: {zip_path}")

    return zip_path


def _safe_join(base: Path, *paths: str) -> Path:
    # Prevent path traversal during extraction
    dest = base.joinpath(*paths).resolve()
    if not str(dest).startswith(str(base.resolve())):
        raise RuntimeError(f"Unsafe path detected during extraction: {dest}")
    return dest


def unzip_markdown(zip_path: Path, articles_dir: Path, mode: str) -> None:
    if mode == "clean":
        # Remove everything inside articles_dir (but keep the dir itself)
        print(f"Cleaning directory: {articles_dir}")
        for p in articles_dir.iterdir():
            # It's fine if we also remove a pre-existing zip before extraction
            if p.is_file() or p.is_symlink():
                p.unlink(missing_ok=True)
            else:
                shutil.rmtree(p, ignore_errors=True)

    print(f"Unzipping {zip_path} into {articles_dir} with mode={mode}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Skip directory entries; create them as needed
            if member.is_dir():
                target_dir = _safe_join(articles_dir, member.filename)
                target_dir.mkdir(parents=True, exist_ok=True)
                continue

            target_path = _safe_join(articles_dir, member.filename)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if mode == "skip-existing" and target_path.exists():
                # Do not overwrite existing files
                continue

            # Extract member
            with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)


def remove_zip(zip_path: Path) -> None:
    if zip_path and zip_path.exists():
        print(f"Removing {zip_path}")
        try:
            zip_path.unlink()
        except Exception as e:
            print(f"Warning: could not remove zip {zip_path}: {e}", file=sys.stderr)


def download_articles(
    data_dir: Path | str = Path("data"),
    *,
    mode: str = "overwrite",
    force_download: bool = False,
) -> None:
    """Download article markdowns zip to data_dir/articles, unzip, and cleanup.

    Args:
        data_dir: Base data directory (contains the `articles/` subdirectory).
        mode: One of {"overwrite", "skip-existing", "clean"} controlling extraction behavior.
        force_download: If True, always re-download the zip even if it exists.
    """
    if isinstance(data_dir, str):
        data_dir = Path(data_dir)

    zip_path = None
    try:
        zip_path = download_markdown_zip(data_dir, force_download=force_download)
        # Extract into the articles directory (not the base data dir)
        articles_dir = data_dir / "articles"
        unzip_markdown(zip_path, articles_dir, mode=mode)
    except Exception as e:
        print(f"Error while downloading/unzipping: {e}", file=sys.stderr)
        # Best effort cleanup of a potentially corrupt zip
        potential_zip = data_dir / "articles" / "markdown.zip"
        if potential_zip.exists():
            try:
                potential_zip.unlink()
            except Exception:
                pass
        raise
    finally:
        # Remove the zip regardless of success/failure of extraction
        remove_zip(zip_path)

    print("Markdown download and extraction complete.")


def main():
    args = parse_args()
    # Bridge CLI args to library-style function
    download_articles(
        data_dir=Path("data"),
        mode=args.mode,
        force_download=args.force_download,
    )


if __name__ == "__main__":
    main()