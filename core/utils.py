"""
core/utils.py - High-Performance Networking Engine for PW Sovereign Hub v2.
Features connection pooling, TCP keep-alive reuse, automatic HTTP retries,
and JWT profile extraction.
"""
import uuid
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import os

BASE_URL = "https://api.penpencil.co"
ORGANIZATION_ID = "5eb393ee95fab7468a79d189"
REFERER = "https://www.pw.live/"
CONTENT_TYPE = "application/json"
ACCEPT = "application/json"
CLIENT_ID = "system-admin"
CLIENT_SECRET = "KjPXuAVfC5xbmgreETNMaL7z"
GRANT_TYPE = "password"
LATITUDE = 0
LONGITUDE = 0

# Persistent High-Performance HTTP Session with Connection Pooling
_session = None

def get_session() -> requests.Session:
    """Returns a singleton requests.Session with connection pooling & retries."""
    global _session
    if _session is None:
        _session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retries,
            pool_block=False
        )
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session

def get_default_headers(random_id=None):
    if not random_id:
        random_id = str(uuid.uuid4())
    return {
        "Content-Type": CONTENT_TYPE,
        "Accept": ACCEPT,
        "Referer": REFERER,
        "Randomid": random_id,
        "Connection": "keep-alive"
    }

def get_auth_headers(token, random_id=None):
    headers = get_default_headers(random_id)
    headers["Authorization"] = f"Bearer {token}"
    return headers

def verify_token(token):
    url = f"{BASE_URL}/v3/oauth/verify-token"
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.post(url, headers=headers, timeout=8)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("isVerified"):
            return {"success": True}
        else:
            error = data.get("error", {})
            return {
                "success": False,
                "error_message": error.get("message", data.get("message", "Unknown error")),
                "error_status": error.get("status", resp.status_code)
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}
    
def get_token_expiry_info(expires_in):
    current_time_ms = int(time.time() * 1000)
    ms_remaining = expires_in - current_time_ms
    days_remaining = ms_remaining // (1000 * 60 * 60 * 24)
    is_expired = ms_remaining <= 0
    return {
        "is_expired": is_expired,
        "days_remaining": days_remaining if not is_expired else 0
    }

def get_user_profile(token):
    """
    Extracts user details (name, email, initials, username) from JWT token.
    """
    try:
        import base64
        import json
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (-len(payload) % 4)
            data = json.loads(base64.b64decode(payload))
            user_data = data.get("data", {})
            first = user_data.get("firstName", "Niranjan")
            last = user_data.get("lastName", "Barhate")
            full = f"{first} {last}".strip()
            initials = ((first[0] if first else "") + (last[0] if last else "")).upper() or "NB"
            return {
                "name": full or "NiranX",
                "first_name": first,
                "last_name": last,
                "initials": initials,
                "email": user_data.get("email", ""),
                "username": user_data.get("username", ""),
                "streak": 1,
                "xp": 368
            }
    except Exception:
        pass
    return {
        "name": "Niranjan Barhate",
        "first_name": "Niranjan",
        "last_name": "Barhate",
        "initials": "NB",
        "email": "niranjanbarhate64@gmail.com",
        "username": "9764687628",
        "streak": 1,
        "xp": 368
    }
