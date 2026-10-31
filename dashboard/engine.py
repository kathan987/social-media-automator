"""The dashboard's built-in engine: keys from .env, Gemini, tolerant JSON parsing, fonts and the YouTube uploader.
Imported by workflow.py, research.py and app.py. Google libraries load lazily, so the parts you don't use need nothing."""
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
CLIENT_SECRET = ROOT / "client_secret.json"   # YouTube OAuth "Desktop app" client (only for dashboard uploads)
TOKEN_FILE = ROOT / ".youtube_token.json"      # saved after the first sign-in (git-ignored)
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"]  # aliases first: they survive retirements

try:  # module-level so tests can patch it; only needed for uploads
    from googleapiclient.http import MediaFileUpload
except ImportError:  # pragma: no cover
    MediaFileUpload = None


def load_env(path=ROOT / ".env"):
    """KEY=value lines from .env into os.environ. A variable already set in the real environment wins."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text("utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()


def gemini_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    return "" if key.upper().startswith("YOUR") else key


_client, _client_key = None, None


def client():
    """A google-genai client for the current GEMINI_API_KEY (rebuilt if the key changes)."""
    global _client, _client_key
    if not gemini_key():
        raise ValueError("Set GEMINI_API_KEY in .env (aistudio.google.com/apikey), then restart the dashboard")
    if _client is None or _client_key != gemini_key():
        from google import genai
        _client, _client_key = genai.Client(api_key=gemini_key()), gemini_key()
    return _client


def _retryable(err):
    """Quota, overload, transient server or network errors: worth another model or another try."""
    return any(k in str(err) for k in ("429", "RESOURCE_EXHAUSTED", "quota", "503", "UNAVAILABLE", "overloaded",
                                       "500", "INTERNAL", "timed out", "Timeout", "Connection", "ConnectError"))


def _gone(err):
    return any(k in str(err) for k in ("404", "NOT_FOUND", "not found", "is not supported"))


def generate(prompt, temperature=0.9, wait=10):
    """Text from Gemini. Tries GEMINI_MODEL (if set) then MODELS, up to 3 attempts each on retryable errors."""
    from google.genai import types
    chain = list(dict.fromkeys([m for m in [os.environ.get("GEMINI_MODEL", "")] + MODELS if m]))
    last = None
    for model in chain:
        for attempt in range(3):
            try:
                r = client().models.generate_content(model=model, contents=prompt,
                                                     config=types.GenerateContentConfig(temperature=temperature))
                return (r.text or "").strip()
            except Exception as e:  # noqa: BLE001 -- classify, then retry, switch model or re-raise
                last = e
                if _gone(e):
                    break
                if not _retryable(e):
                    raise
                if attempt < 2:
                    time.sleep(wait * (attempt + 1))
    raise RuntimeError(f"Every Gemini model failed (429 = daily quota, 503 = busy, try later). Last error: {last}")


def _close_open(text):
    """Append the brackets and quote a cut-off JSON object is missing, in the right order."""
    stack, in_str, esc = [], False, False
    for ch in text:
        if in_str:
            esc, in_str = (False, in_str) if esc else (ch == "\\", ch != '"')
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack and stack[-1] == ch:
            stack.pop()
    return text + ('"' if in_str else "") + "".join(reversed(stack))


def extract_json(raw, label="Model"):
    """The JSON object in a model reply: strips ``` fences and prose, then repairs trailing commas and cut-off endings."""
    text = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip()).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError(f"{label} returned no JSON.\nRaw:\n{(raw or '')[:600]}")
    end = text.rfind("}")
    for candidate in (text[start:end + 1] if end > start else "", text[start:]):
        if not candidate:
            continue
        for attempt in (candidate, re.sub(r",\s*([}\]])", r"\1", _close_open(candidate))):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError as e:
                err = e
    raise ValueError(f"{label} returned invalid JSON ({err}).\nRaw:\n{raw[:600]}")


_fonts = {}


def font(size):
    """The bold UI font (Anton, else Bebas Neue, from assets/fonts; Pillow's default if neither is there)."""
    from PIL import ImageFont
    if size not in _fonts:
        for name in ("Anton-Regular.ttf", "BebasNeue-Regular.ttf"):
            if (FONTS / name).exists():
                _fonts[size] = ImageFont.truetype(str(FONTS / name), size)
                break
        else:
            _fonts[size] = ImageFont.load_default(size)
    return _fonts[size]


def _get_service():
    """An authorised YouTube Data API client. The first call opens a browser to sign in, then reuses the saved token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), YOUTUBE_SCOPES) if TOKEN_FILE.exists() else None
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CLIENT_SECRET.exists():
            raise FileNotFoundError(f"YouTube OAuth file not found: {CLIENT_SECRET.name} in the repo root (docs/setup.md)")
        creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), YOUTUBE_SCOPES).run_local_server(port=8080)
    TOKEN_FILE.write_text(creds.to_json(), "utf-8")
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(plan, video_path, *, privacy="private", publish_at=None, synthetic=False):
    """Upload final.mp4 with the plan's title, description and tags. Scheduled uploads are always private until
    publish_at. Returns the watch URL."""
    youtube = _get_service()
    body = {"snippet": {"title": plan["title"], "description": plan.get("description", ""), "tags": plan.get("tags", []),
                        "categoryId": plan.get("category_id", "20")},
            "status": {"privacyStatus": "private" if publish_at else privacy, "selfDeclaredMadeForKids": False}}
    if publish_at:
        body["status"]["publishAt"] = publish_at
    if synthetic:
        body["status"]["containsSyntheticMedia"] = True
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
    request = youtube.videos().insert(part=",".join(body), body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return f"https://www.youtube.com/watch?v={response['id']}"
