# app/routes/gmail_responder_routes.py
import os
import json
import secrets
import time
import logging
import traceback
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from backend.routes.gmail_responder_routes import GMAIL_AI_RESPONDER_TEMPLATE
from database.deps import get_user_id
from database.db import sb
from database.sb_utils import get_data, get_error
from thirdPartyIntegrations.google_oauth import build_auth_url, exchange_code_for_tokens
from workflows.gmail_ai_labelling.provision_n8n import provision_in_n8n

logger = logging.getLogger(__name__)
router = APIRouter()

TEMPLATE_ID = "gmail-ai-labelling"
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "gmail_ai_labelling.json")

# Load template once
try:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        GMAIL_AI_LABELLING_TEMPLATE = json.loads(f.read())
    logger.info("gmail_ai_labelling template loaded")
except Exception as e:
    logger.error(f"Failed to load gmail_ai_labelling template: {e}")
    GMAIL_AI_LABELLING_TEMPLATE = None

class InstallBody(BaseModel):
    templateId: str

def _upsert_user_integration_tokens(user_id: str, tokens: dict) -> None:
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token", "")
    scope = tokens.get("scope", "")
    expires_in = int(tokens.get("expires_in", 3600))
    expiry_ts = int(time.time()) + expires_in

    res = sb.table("user_integrations").upsert(
        {
            "user_id": user_id,
            "provider": "google",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "scope": scope,
            "expiry": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_ts)),
        },
        on_conflict="user_id,provider",
    ).execute()
    err = get_error(res)
    if err:
        raise HTTPException(500, f"Supabase upsert error: {err}")

# app/routes/gmail_responder_routes.py

# ...imports and constants unchanged...

# Remove InstallBody if you only use namespaced install
# class InstallBody(BaseModel):
#     templateId: str

@router.post("/workflows/gmail-ai-responder/install")
def install(user_id: str = Depends(get_user_id)):
    logger.info(f"Install request. templateId={TEMPLATE_ID}, user={user_id}")
    try:
        if not GMAIL_AI_LABELLING_TEMPLATE:
            raise HTTPException(500, "Template not loaded")

        # Check for existing Google tokens
        res = (
            sb.table("user_integrations")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", "google")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        err = get_error(res)
        if err:
            raise HTTPException(500, f"Supabase select error: {err}")

        rows = get_data(res) or []
        tokens_row = rows[0] if isinstance(rows, list) and rows else None

        if not tokens_row:
            state = secrets.token_urlsafe(24)
            ins = sb.table("oauth_states").insert(
                {"state": state, "user_id": user_id, "template_id": TEMPLATE_ID}
            ).execute()
            if get_error(ins):
                raise HTTPException(500, f"Supabase insert error: {get_error(ins)}")

            auth_url = build_auth_url(state)
            return {"needsAuth": True, "authUrl": auth_url, "state": state, "templateId": TEMPLATE_ID}

        # Tokens exist, provision now
        result = provision_in_n8n(
            user_id=user_id,
            template_id=TEMPLATE_ID,
            integ_row=tokens_row,
            tpl=GMAIL_AI_RESPONDER_TEMPLATE,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Install failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Install failed: {e}")