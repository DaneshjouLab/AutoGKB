# main entry point for the app, 
import subprocess
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web_app.routes import primary_page, evaluation_route

app = FastAPI()

# Static files and templates
app.mount("/static", StaticFiles(directory="src/web_app/static"), name="static")
templates = Jinja2Templates(directory="src/web_app/static/html")

# Include routes
app.include_router(primary_page.router)
app.include_router(evaluation_route.router)


def run_uvicorn(host="127.0.0.1", port=8060, reload=True):
    url = f"http://{host}:{port}"
    print(f"\n🚀 Server running at: \033[94m{url}\033[0m (Ctrl+C to stop)\n")  # Blue clickable in most terminals

    command = [
        sys.executable, "-m", "uvicorn",
        "src.web_app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    if reload:
        command.append("--reload")

    subprocess.run(command, check=True)

if __name__ == "__main__":
    run_uvicorn()
