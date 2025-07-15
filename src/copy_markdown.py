from typing import List
import os
import shutil
from loguru import logger
from pathlib import Path

"""
Pass in a list of PMCIDs and have those files copied to a new folder
"""


def copy_markdown(pmcids: List[str]) -> None:
    succesful = 0
    for pmcid in pmcids:
        try:
            source_file = Path("data") / "articles" / f"{pmcid}.md"
            destination = Path("data") / "extractions" / "markdown"
            os.makedirs(destination, exist_ok=True)
            shutil.copy2(source_file, destination / f"{pmcid}.md")
            succesful += 1
        except Exception as e:
            logger.error(e)
    logger.info(
        f"Copied {succesful}/{len(pmcids)} markdown to data/extractions/markdown"
    )


def main():
    pmcids = ["PMC4737107", "PMC5712579", "PMC5728534", "PMC5749368", "PMC11730665"]
    copy_markdown(pmcids=pmcids)


if __name__ == "__main__":
    main()
