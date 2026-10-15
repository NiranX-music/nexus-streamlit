# core/generate_token.py

import requests
from core.utils import (
    get_default_headers, BASE_URL, ORGANIZATION_ID,
    CLIENT_ID, CLIENT_SECRET, GRANT_TYPE, LATITUDE, LONGITUDE
)

def send_otp(phone: str, country_code: str, random_id=None):
    """
    Sends OTP to the given phone number and country code.
    Returns a dict with success or error info.
    """
    url = f"{BASE_URL}/v1/users/get-otp?smsType=0"
    headers = get_default_headers(random_id)
    payload = {
        "username": phone,
        "countryCode": country_code,
        "organizationId": ORGANIZATION_ID
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success"):
            return {"success": True}
        else:
            error = data.get("error", {})
            return {
                "success": False,
                "error_message": error.get("message", "Unknown error"),
                "error_status": error.get("status", resp.status_code)
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}

def get_token(phone: str, otp: str, random_id=None):
    """
    Exchanges phone and OTP for an access token.
    Returns a dict with access token or error info.
    """
    url = f"{BASE_URL}/v3/oauth/token"
    headers = get_default_headers(random_id)
    payload = {
        "username": phone,
        "otp": otp,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": GRANT_TYPE,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "organizationId": ORGANIZATION_ID
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success") and "data" in data:
            return {
                "success": True,
                "access_token": data["data"]["access_token"],
                "expires_in": data["data"]["expires_in"]
            }
        else:
            error = data.get("error", {})
            return {
                "success": False,
                "error_message": error.get("message", data.get("message", "Unknown error")),
                "error_status": error.get("status", resp.status_code)
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}
