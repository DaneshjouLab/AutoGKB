# main entry point for the app, 



from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import subprocess
import sys

from src.web_app.routes.evaluation_route import route as eval_route

app = FastAPI()

app.include_router(eval_route)
app.mount("/static", StaticFiles(directory="src/web_app/static"), name="static")

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
