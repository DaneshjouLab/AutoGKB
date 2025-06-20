from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

router = APIRouter()

templates = Jinja2Templates(directory="src/web_app/static/html")

# Simulated user "database"
users_db = {
    "alice": {"username": "alice", "full_name": "Alice Wonderland", "password": "1234"},
    "bob": {"username": "bob", "full_name": "Bob Builder", "password": "builder"},
}

@router.get("/")
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_db.get(username)
    if user and user["password"] == password:
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="session_user",
            value=user["username"],
            httponly=True,  # prevents JS from accessing it
            max_age=3600    # 1 hour session
        )
        return response
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid username or password"
    })

@router.get("/dashboard")
async def dashboard(request: Request):
    user = request.cookies.get("session_user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": user
    })

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_user")
    return response