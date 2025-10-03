from typing import Optional
from pathlib import Path

"""
Get the title of an article from the markdown file
This relies on the markdown files downloaded by the article_markdown_downloader
"""


def get_title_from_markdown(
    markdown_path: Path,
) -> Optional[str]:
    with open(markdown_path, "r") as f:
        content = f.read()
    # Read the first heading of the markdown file
    return content.split("\n")[0].split("# ")[1]


def construct_markdown_path_from_pmcid(pmcid: str, data_dir: Path) -> Path:
    return data_dir / "articles" / f"{pmcid}.md"


def get_title_from_pmcid(pmcid: str, data_dir: Path) -> Optional[str]:
    markdown_path = construct_markdown_path_from_pmcid(pmcid, data_dir)
    return get_title_from_markdown(markdown_path)


if __name__ == "__main__":
    pmcid = "PMC12146598"
    data_dir = Path("data")
    title = get_title_from_pmcid(pmcid, data_dir)
    print(title)
