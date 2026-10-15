import requests
from core.utils import verify_token, get_auth_headers, BASE_URL

def fetch_batches(token, page=1):
    """
    Fetches all purchased batches for the authenticated user.
    Returns a list of dicts with: name, _id, slug, startDate, endDate, expiryDate.
    """
    # Verify token before proceeding
    verification = verify_token(token)
    if not verification.get("success"):
        return {
            "success": False,
            "error_message": verification.get("error_message", "Token verification failed"),
            "error_status": verification.get("error_status", None)
        }
    
    url = f"{BASE_URL}/batch-service/v1/batches/purchased-batches?amount=paid&page={page}&type=ALL"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success") and isinstance(data.get("data"), list):
            result = []
            for batch in data["data"]:
                result.append({
                    "name": batch.get("name"),
                    "_id": batch.get("_id"),
                    "slug": batch.get("slug"),
                    "startDate": batch.get("startDate"),
                    "endDate": batch.get("endDate"),
                    "expiryDate": batch.get("expiryDate"),
                })
            return {"success": True, "batches": result}
        else:
            return {
                "success": False,
                "error_message": data.get("message", "Failed to fetch batches"),
                "error_status": resp.status_code
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}

def fetch_announcements(token, batch_id, page=1):
    """
    Fetches announcements for a specific batch.
    Returns a list of dicts with: announcement, _id, scheduleTime, attachment (name, baseUrl, key).
    """
    # Verify token before proceeding
    verification = verify_token(token)
    if not verification.get("success"):
        return {
            "success": False,
            "error_message": verification.get("error_message", "Token verification failed"),
            "error_status": verification.get("error_status", None)
        }
    
    url = f"{BASE_URL}/v1/batches/{batch_id}/announcement?page={page}"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("success") and isinstance(data.get("data"), list):
            result = []
            for ann in data["data"]:
                announcement_info = {
                    "announcement": ann.get("announcement"),
                    "_id": ann.get("_id"),
                    "scheduleTime": ann.get("scheduleTime"),
                }
                attachment = ann.get("attachment")
                if attachment:
                    announcement_info["attachment"] = {
                        "name": attachment.get("name"),
                        "baseUrl": attachment.get("baseUrl"),
                        "key": attachment.get("key"),
                    }
                else:
                    announcement_info["attachment"] = None
                result.append(announcement_info)
            return {"success": True, "announcements": result}
        else:
            return {
                "success": False,
                "error_message": data.get("message", "Failed to fetch announcements"),
                "error_status": resp.status_code
            }
    except Exception as e:
        return {"success": False, "error_message": str(e), "error_status": None}
