"""

evaluation_route.py

This page is responsible for handling the evaluation page route

/evaluation/{index}




"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse
import requests
import html2text
router = APIRouter()

templates = Jinja2Templates(directory="src/web_app/static/html")

@router.get("/eval/{md}")
async def eval_render(request: Request, md: str):
    return templates.TemplateResponse("annotation_interface.html", {
        "request": request,
        "md": md
    })

@router.get("/markdown/nih")
async def fetch_nih_article():
    url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6289290/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                      "AppleWebKit/537.36 (KHTML, like Gecko) " \
                      "Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return PlainTextResponse(f"Error fetching article: {e}", status_code=500)

    html = response.text
    markdown = html2text.html2text(html)
    return PlainTextResponse(markdown)