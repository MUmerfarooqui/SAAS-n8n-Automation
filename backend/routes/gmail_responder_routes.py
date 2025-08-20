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

from database.deps import get_user_id
from database.db import sb
from database.sb_utils import get_data, get_error
from thirdPartyIntegrations.google_oauth import build_auth_url, exchange_code_for_tokens
from workflows.gmail_ai_responder.provision_n8n_responder import provision_in_n8n

logger = logging.getLogger(__name__)
router = APIRouter()

TEMPLATE_ID = "gmail-ai-responder"
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "gmail_ai_responder.json")

# Load template once
try:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        GMAIL_AI_RESPONDER_TEMPLATE = json.loads(f.read())
    logger.info("gmail_ai_responder template loaded")
except Exception as e:
    logger.error(f"Failed to load gmail_ai_responder template: {e}")
    GMAIL_AI_RESPONDER_TEMPLATE = None

class InstallBody(BaseModel):
    templateId: str

# app/routes/gmail_responder_routes.py

# ...imports and constants unchanged...

# Remove InstallBody if you only use namespaced install
# class InstallBody(BaseModel):
#     templateId: str

@router.post("/workflows/gmail-ai-responder/install")
def install(user_id: str = Depends(get_user_id)):
    logger.info(f"Install request. templateId={TEMPLATE_ID}, user={user_id}")
    try:
        if not GMAIL_AI_RESPONDER_TEMPLATE:
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


# @router.get("/oauth/google/callback")
# def google_callback(code: str, state: str):
#     logger.info(f"OAuth callback state={state}")
#     try:
#         # 1) validate state
#         s_res = (
#             sb.table("oauth_states")
#             .select("*")
#             .eq("state", state)
#             .maybe_single()
#             .execute()
#         )
#         err = get_error(s_res)
#         if err:
#             raise HTTPException(500, f"Supabase select error: {err}")
#         s = get_data(s_res)
#         if not s:
#             raise HTTPException(400, "Invalid state")

#         user_id = s["user_id"]
#         template_id = s["template_id"]
#         if template_id != TEMPLATE_ID:
#             raise HTTPException(400, "Unknown templateId")

#         # 2) exchange code for tokens and upsert
#         tokens = exchange_code_for_tokens(code)
#         _upsert_user_integration_tokens(user_id, tokens)

#         # 3) delete used state
#         del_res = sb.table("oauth_states").delete().eq("state", state).execute()
#         err = get_error(del_res)
#         if err:
#             raise HTTPException(500, f"Supabase delete error: {err}")

#         # 4) read back most recent tokens
#         r2 = (
#             sb.table("user_integrations")
#             .select("*")
#             .eq("user_id", user_id)
#             .eq("provider", "google")
#             .order("created_at", desc=True)
#             .limit(1)
#             .execute()
#         )
#         err = get_error(r2)
#         if err:
#             raise HTTPException(500, f"Supabase select error: {err}")

#         rows = get_data(r2) or []
#         row = rows[0] if isinstance(rows, list) and rows else rows
#         if not row:
#             raise HTTPException(400, "Missing tokens after OAuth")

#         # 5) provision
#         if not GMAIL_AI_RESPONDER_TEMPLATE:
#             raise HTTPException(500, "Template not loaded")
#         result = provision_in_n8n(user_id=user_id, template_id=TEMPLATE_ID, integ_row=row, tpl=GMAIL_AI_RESPONDER_TEMPLATE)

#         # 6) redirect back to frontend
#         frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
#         url = f"{frontend}/dashboard?installed={template_id}&workflowId={result['workflowId']}"
#         return RedirectResponse(url=url, status_code=302)

#     except HTTPException as he:
#         frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
#         url = f"{frontend}/dashboard?oauth_error={he.detail}"
#         return RedirectResponse(url=url, status_code=302)
#     except Exception as e:
#         frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
#         msg = f"OAuth callback failed: {str(e)}"
#         try:
#             from requests.utils import requote_uri
#             msg = requote_uri(msg)
#         except Exception:
#             pass
#         url = f"{frontend}/dashboard?oauth_error={msg}"
#         return RedirectResponse(url=url, status_code=302)
