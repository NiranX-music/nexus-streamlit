# core/dashboard.py

import requests
from core.utils import get_auth_headers, BASE_URL

def fetch_batch_lecture_stats(token, batch_id):
    """
    Fetch lecture statistics for a complete batch.
    Returns a dict: {
        'completedChapter', 'completedLectures', 'totalWatchTime', 'totalChapters', 'totalLectures'
    }
    """
    url = f"{BASE_URL}/v3/performance/lecture?batchId={batch_id}"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        d = data.get("data", {})
        return {
            "completedChapter": d.get("completedChapter"),
            "completedLectures": d.get("completedLectures"),
            "totalWatchTime": d.get("totalWatchTime"),
            "totalChapters": d.get("totalChapters"),
            "totalLectures": d.get("totalLectures")
        }
    except Exception:
        return {}

def fetch_subject_lecture_stats(token, batch_id):
    """
    Fetch lecture statistics for each subject in a batch.
    Returns a list of dicts:
        {
            'subjectName', 'completedChapter', 'completedLectures',
            'totalWatchTime', 'totalLectures', 'totalChapters'
        }
    """
    url = f"{BASE_URL}/v3/performance/lecture/subjects?batchId={batch_id}"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        stats = []
        for item in data.get("data", []):
            subject = item.get("subjectId", {})
            stats.append({
                "subjectName": subject.get("name"),
                "completedChapter": item.get("completedChapter"),
                "completedLectures": item.get("completedLectures"),
                "totalWatchTime": item.get("totalWatchTime"),
                "totalLectures": item.get("totalLectures"),
                "totalChapters": item.get("totalChapters")
            })
        return stats
    except Exception:
        return []

def fetch_batch_quiz_stats(token, batch_id):
    """
    Fetch combined DPP-Quiz stats for a batch.
    Returns a list of dicts: {
        'key', 'accuracy', 'marksObtained', 'correctQuestions',
        'completedQuiz', 'totalQuiz'
    }
    """
    url = f"{BASE_URL}/v3/performance/quiz?batchId={batch_id}"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        result = []
        for item in data.get("data", []):
            val = item.get("value", {})
            result.append({
                "key": item.get("key"),
                "accuracy": val.get("accuracy"),
                "marksObtained": val.get("marksObtained"),
                "correctQuestions": val.get("correctQuestions"),
                "completedQuiz": val.get("completedQuiz"),
                "totalQuiz": val.get("totalQuiz")
            })
        return result
    except Exception:
        return []

def fetch_subject_quiz_stats(token, batch_id, quiz_type="OBJECTIVE"):
    """
    Fetch DPP-Quiz stats for each subject in a batch.
    Returns a list of dicts: {
        'subjectName', 'accuracy', 'marksObtained', 'totalQuestions',
        'correctQuestions', 'attemptedQuestions', 'attempted', 'totalQuiz'
    }
    """
    url = f"{BASE_URL}/v3/performance/quiz/subjects?batchId={batch_id}&type={quiz_type}"
    headers = get_auth_headers(token)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        result = []
        for item in data.get("data", []):
            subject = item.get("subjectId", {})
            result.append({
                "subjectName": subject.get("name"),
                "accuracy": item.get("accuracy"),
                "marksObtained": item.get("marksObtained"),
                "totalQuestions": item.get("totalQuestions"),
                "correctQuestions": item.get("correctQuestions"),
                "attemptedQuestions": item.get("attemptedQuestions"),
                "attempted": item.get("attempted"),
                "totalQuiz": item.get("totalQuiz")
            })
        return result
    except Exception:
        return []
