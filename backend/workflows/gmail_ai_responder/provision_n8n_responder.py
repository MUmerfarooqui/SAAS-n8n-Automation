# app/workflows/gmail_ai_responder/provision_n8n_responder.py
import os
import logging
from datetime import datetime
from fastapi import HTTPException

from database.db import sb
from database.sb_utils import get_error
from n8n.n8n_client import (
    upsert_gmail_credential,
    upsert_openai_credential,
    upsert_gemini_credential,
    create_workflow,
    activate_workflow,
)
from .build_template_responder import build_workflow_from_template, debug_workflow_json

logger = logging.getLogger(__name__)

OPENAI_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

def _ensure_gmail_cred(user_id: str, integ_row: dict):
    name = f"gmail-oauth2-{user_id}"
    payload = {
        "clientId": GOOGLE_CLIENT_ID,
        "clientSecret": GOOGLE_CLIENT_SECRET,
        "oauthTokenData": {
            "access_token": integ_row["access_token"],
            "refresh_token": integ_row.get("refresh_token") or "",
            "scope": integ_row.get("scope", ""),
            "token_type": "Bearer",
        },
    }
    if integ_row.get("expiry"):
        try:
            expiry_ms = int(datetime.fromisoformat(integ_row["expiry"].replace("Z", "+00:00")).timestamp() * 1000)
            payload["oauthTokenData"]["expiry_date"] = expiry_ms
        except Exception as e:
            logger.warning(f"Could not parse expiry date: {e}")
    return upsert_gmail_credential(name, payload)

def _ensure_openai_cred(user_id: str):
    return upsert_openai_credential(f"openai-{user_id}", OPENAI_KEY)

def _ensure_gemini_cred(user_id: str):
    return upsert_gemini_credential(f"gemini-{user_id}", GEMINI_KEY)

def provision_in_n8n(user_id: str, template_id: str, integ_row: dict, tpl: dict) -> dict:
    logger.info(f"Provision start user={user_id} template={template_id}")

    gmail_cred_info = _ensure_gmail_cred(user_id, integ_row)
    openai_cred_info = _ensure_openai_cred(user_id)
    gemini_cred_info = _ensure_gemini_cred(user_id)

    wf_json = build_workflow_from_template(
        tpl,
        gmail_credential_id=gmail_cred_info["id"],
        gmail_credential_name=gmail_cred_info["name"],
        openai_credential_id=openai_cred_info["id"],
        openai_credential_name=openai_cred_info["name"],
        gemini_credential_id=gemini_cred_info["id"],
        gemini_credential_name=gemini_cred_info["name"],
    )

    debug_workflow_json(wf_json, f"debug_workflow_{user_id}_{template_id}.json")

    wid = create_workflow(f"{template_id}-{user_id}", wf_json)
    logger.info(f"Created workflow id={wid}")

    try:
        activate_workflow(wid)
        logger.info(f"Activated workflow id={wid}")
    except Exception as e:
        logger.error(f"Activation failed: {e}")
        raise

    ins = sb.table("workflows").insert(
        {
            "user_id": user_id,
            "template_id": template_id,
            "name": template_id,
            "description": "Auto provisioned Gmail AI responder",
            "n8n_workflow_id": str(wid),
            "status": "active",
            "workflow_config": {},
        }
    ).execute()
    err = get_error(ins)
    if err:
        raise HTTPException(500, f"Supabase insert error: {err}")

    return {"activated": True, "workflowId": wid}
