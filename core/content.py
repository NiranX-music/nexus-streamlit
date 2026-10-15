"""
core/content.py - High-Throughput Content Engine for PW Hub v2.
Parallelized multi-page fetching, connection pooling, and SQLite cache integration.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.utils import get_auth_headers, BASE_URL, get_session
import core.db as db

def fetch_starred_batch_ids(token: str) -> set:
    """Fetches user starred/pinned batch IDs from PW."""
    headers = get_auth_headers(token)
    url = f"{BASE_URL}/batch-service/v1/batches/purchased-batches?amount=starred&page=1&limit=100"
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            return {b["_id"] for b in resp.json().get("data", []) if "_id" in b}
    except Exception:
        pass
    return set()

def _fetch_single_batch_page(session, url, headers, mode, starred_ids):
    try:
        resp = session.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get("data", [])
        if not items or not isinstance(items, list):
            return []
        
        parsed = []
        for batch in items:
            b_id = batch.get("_id")
            if not b_id:
                continue
            is_free = bool(batch.get("isFree", False)) or (mode == "free")
            img_dict = batch.get("previewImage") or {}
            preview_img = None
            if img_dict.get("baseUrl") and img_dict.get("key"):
                preview_img = img_dict["baseUrl"].rstrip("/") + "/" + img_dict["key"].lstrip("/")

            parsed.append({
                "_id": b_id,
                "name": batch.get("name") or "Unnamed Batch",
                "slug": batch.get("slug") or "",
                "startDate": batch.get("startDate"),
                "endDate": batch.get("endDate"),
                "expiryDate": batch.get("expiryDate", ""),
                "is_free": is_free,
                "is_starred": b_id in starred_ids,
                "type": "FREE" if is_free else "PAID",
                "preview_image": preview_img,
                "exam": batch.get("exam", ""),
                "class": batch.get("class", ""),
            })
        return parsed
    except Exception:
        return []

def fetch_batches(token, amount="all", page=1, fetch_all=True, use_cache=True):
    """
    High-throughput batch fetching:
    1. If use_cache=True, checks local SQLite first (<1ms).
    2. Uses ThreadPoolExecutor with pooled session to concurrently fetch pages in ~0.6s.
    3. Caches all batches in SQLite.
    """
    if use_cache:
        cached = db.get_cached_batches(
            starred_only=(amount == "starred"),
            paid_only=(amount == "paid"),
            free_only=(amount == "free")
        )
        if cached and len(cached) > 0:
            return cached

    session = get_session()
    headers = get_auth_headers(token)
    starred_ids = fetch_starred_batch_ids(token)

    modes = ["paid", "free"] if amount == "all" else [amount]
    tasks = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for mode in modes:
            for p in range(1, 10 if fetch_all else 2):
                url = f"{BASE_URL}/batch-service/v1/batches/purchased-batches?amount={mode}&page={p}&type=ALL"
                tasks.append(executor.submit(_fetch_single_batch_page, session, url, headers, mode, starred_ids))

    all_batches = []
    seen = set()
    for future in as_completed(tasks):
        items = future.result()
        for b in items:
            if b["_id"] not in seen:
                seen.add(b["_id"])
                all_batches.append(b)

    # Save to SQLite
    if all_batches:
        db.save_batches(all_batches)

    return all_batches

def fetch_subjects(token, batch_slug):
    """Fetches all subjects for a given batch using pooled session."""
    url = f"{BASE_URL}/v3/batches/{batch_slug}/details"
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=8)
        data = resp.json()
        subjects = data.get("data", {}).get("subjects", [])
        res = []
        for s in subjects:
            res.append({
                "_id": s.get("_id"),
                "subject": s.get("subject"),
                "slug": s.get("slug"),
                "teacherIds": [
                    {
                        "firstName": t.get("firstName"),
                        "lastName": t.get("lastName"),
                        "experience": t.get("experience"),
                        "qualification": t.get("qualification"),
                        "email": t.get("email")
                    }
                    for t in s.get("teacherIds", [])
                ],
                "tagCount": s.get("tagCount"),
                "displayOrder": s.get("displayOrder"),
                "lectureCount": s.get("lectureCount")
            })
        return res
    except Exception:
        return []

def fetch_topics(token, batch_slug, subject_slug, page=1):
    """Fetch topics/chapters for a subject using pooled session."""
    url = f"{BASE_URL}/v2/batches/{batch_slug}/subject/{subject_slug}/topics?page={page}"
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=8)
        data = resp.json()
        topics = data.get("data", [])
        return [
            {
                "_id": t.get("_id"),
                "name": t.get("name"),
                "displayOrder": t.get("displayOrder"),
                "notes": t.get("notes"),
                "exercises": t.get("exercises"),
                "videos": t.get("videos"),
                "lectureVideos": t.get("lectureVideos"),
                "slug": t.get("slug")
            }
            for t in topics
        ]
    except Exception:
        return []

def fetch_notes(token, batch_slug, subject_slug, topic_slug, page=1):
    url = (f"{BASE_URL}/v2/batches/{batch_slug}/subject/{subject_slug}"
           f"/contents?page={page}&contentType=notes&tag={topic_slug}")
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=8)
        data = resp.json()
        notes_list = []
        for entry in data.get("data", []):
            for hw in entry.get("homeworkIds", []):
                notes_list.append({
                    "topic": hw.get("topic"),
                    "attachments": [
                        {
                            "_id": att.get("_id"),
                            "baseUrl": att.get("baseUrl"),
                            "key": att.get("key"),
                            "name": att.get("name"),
                        }
                        for att in hw.get("attachmentIds", [])
                    ]
                })
        return notes_list
    except Exception:
        return []

def fetch_dpp(token, batch_slug, subject_slug, topic_slug, page=1):
    url = (f"{BASE_URL}/v2/batches/{batch_slug}/subject/{subject_slug}"
           f"/contents?page={page}&contentType=DppNotes&tag={topic_slug}")
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=8)
        data = resp.json()
        dpp_list = []
        for entry in data.get("data", []):
            for hw in entry.get("homeworkIds", []):
                dpp_list.append({
                    "topic": hw.get("topic"),
                    "attachments": [
                        {
                            "_id": att.get("_id"),
                            "baseUrl": att.get("baseUrl"),
                            "key": att.get("key"),
                            "name": att.get("name"),
                        }
                        for att in hw.get("attachmentIds", [])
                    ]
                })
        return dpp_list
    except Exception:
        return []

def fetch_videos(token, batch_slug, subject_slug, topic_slug, page=1):
    url = f"{BASE_URL}/v2/batches/{batch_slug}/subject/{subject_slug}/contents?page={page}&contentType=videos&tag={topic_slug}"
    headers = get_auth_headers(token)
    session = get_session()
    try:
        resp = session.get(url, headers=headers, timeout=8)
        data = resp.json().get("data", [])
        if not isinstance(data, list):
            return []
        vids = []
        for item in data:
            v_details = item.get("videoDetails") or {}
            duration_sec = v_details.get("duration", 0)
            mins = duration_sec // 60 if duration_sec else 0
            vids.append({
                "_id": item.get("_id"),
                "topic": item.get("topic") or "Lecture Video",
                "url": item.get("url") or item.get("ytStreamUrl") or "",
                "duration_seconds": duration_sec,
                "duration_formatted": f"{mins} mins" if mins else "Standard Lecture",
                "image": v_details.get("image") or item.get("timeline"),
                "startTime": item.get("startTime", ""),
                "hasAttachment": bool(item.get("hasAttachment", False)),
            })
        return vids
    except Exception:
        return []
