from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from msal import ConfidentialClientApplication
import requests, os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
authority = "https://login.microsoftonline.com/common"
redirect_uri = os.getenv("REDIRECT_URI", "https://testinglocal.onrender.com/auth/callback")
SCOPES = ["Mail.Read"]

msal_app = ConfidentialClientApplication(
    client_id=client_id,
    authority=authority,
    client_credential=client_secret
)

EMAIL_DATA = []

def get_all_messages(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    messages = []
    url = "https://graph.microsoft.com/v1.0/me/messages?$top=50"

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Failed to get emails:", response.text)
            break
        data = response.json()
        for email in data.get("value", []):
            # Format datetime for display
            email["sentDateTimeFormatted"] = datetime.fromisoformat(
                email["sentDateTime"].replace("Z", "+00:00")
            ).strftime("%Y-%m-%d %H:%M:%S")
        messages.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return messages

@app.get("/", response_class=HTMLResponse)
def show_login(request: Request):
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return templates.TemplateResponse("index.html", {"request": request, "auth_url": auth_url})

@app.get("/auth/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not provided"}

    token_response = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    if "access_token" in token_response:
        access_token = token_response["access_token"]
        global EMAIL_DATA
        EMAIL_DATA = get_all_messages(access_token)
        return RedirectResponse("/emails")
    else:
        return {"error": "Failed to acquire token", "details": token_response}

@app.get("/emails", response_class=HTMLResponse)
def show_emails(request: Request):
    return templates.TemplateResponse("emails.html", {"request": request, "emails": EMAIL_DATA})
