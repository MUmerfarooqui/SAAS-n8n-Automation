# n8n/n8n_client.py
import os
import requests

N8N_BASE = os.environ["N8N_BASE_URL"].rstrip("/")
N8N_KEY = os.environ["N8N_API_KEY"]

def _headers():
    return {
        "X-N8N-API-KEY": N8N_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def _raise_for_status(resp: requests.Response):
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f"{e} :: {resp.text}") from e

def upsert_gmail_credential(name: str, payload: dict) -> dict:
    """Create a new gmailOAuth2 credential and return its ID and name."""
    import time
    unique_name = f"{name}-{int(time.time())}"
    
    r = requests.post(
        f"{N8N_BASE}/api/v1/credentials",
        json={
            "name": unique_name,
            "type": "gmailOAuth2",
            "data": payload,
        },
        headers=_headers(),
        timeout=20,
    )
    _raise_for_status(r)
    j = r.json()
    
    return {
        "id": j.get("id") if isinstance(j, dict) else j,
        "name": unique_name
    }

def upsert_openai_credential(name: str, api_key: str) -> dict:
    """Create a new openAiApi credential and return its ID and name."""
    import time
    unique_name = f"{name}-{int(time.time())}"
    
    r = requests.post(
        f"{N8N_BASE}/api/v1/credentials",
        json={
            "name": unique_name,
            "type": "openAiApi",
            "data": {
                "apiKey": api_key
            },
        },
        headers=_headers(),
        timeout=20,
    )
    _raise_for_status(r)
    j = r.json()
    
    return {
        "id": j.get("id") if isinstance(j, dict) else j,
        "name": unique_name
    }

def upsert_gemini_credential(name: str, api_key: str) -> dict:
    """Create a new Google Gemini credential and return its ID and name."""
    import time
    unique_name = f"{name}-{int(time.time())}"
    
    r = requests.post(
        f"{N8N_BASE}/api/v1/credentials",
        json={
            "name": unique_name,
            "type": "googlePalmApi",  # Correct credential type for Google Gemini
            "data": {
                "host": "https://generativelanguage.googleapis.com",
                "apiKey": api_key
            },
        },
        headers=_headers(),
        timeout=20,
    )
    _raise_for_status(r)
    j = r.json()
    
    return {
        "id": j.get("id") if isinstance(j, dict) else j,
        "name": unique_name
    }

def create_workflow(name: str, wf_json: dict) -> int:
    r = requests.post(
        f"{N8N_BASE}/api/v1/workflows",
        json={
            "name": name,
            "nodes": wf_json["nodes"],
            "connections": wf_json["connections"],
            "settings": wf_json.get("settings", {}),
        },
        headers=_headers(),
        timeout=20,
    )
    _raise_for_status(r)
    j = r.json()
    return j.get("id") if isinstance(j, dict) else j

def activate_workflow(wid: int) -> None:
    r = requests.post(
        f"{N8N_BASE}/api/v1/workflows/{wid}/activate",
        headers=_headers(),
        timeout=20,
    )
    _raise_for_status(r)