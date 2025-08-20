import os 
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
import time

from database.db import sb
from database.sb_utils import get_data, get_error
from thirdPartyIntegrations.google_oauth import  exchange_code_for_tokens

from gmail_responder_routes import _upsert_user_integration_tokens

logger = logging.getLogger(__name__)
router = APIRouter()



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



@router.get("/oauth/google/callback")
def google_callback(code: str, state: str):
    logger.info(f"OAuth callback state={state}")
    try:
        # 1) Validate state & get user_id and template_id
        s_res = sb.table("oauth_states").select("*").eq("state", state).maybe_single().execute()
        err = get_error(s_res)
        if err:
            raise HTTPException(500, f"Supabase select error: {err}")
        s = get_data(s_res)
        if not s:
            raise HTTPException(400, "Invalid state")

        user_id = s["user_id"]
        template_id = s["template_id"]
        
        # 2) Exchange code for tokens and upsert
        tokens = exchange_code_for_tokens(code)
        _upsert_user_integration_tokens(user_id, tokens)
        
        # 3) Delete used state
        del_res = sb.table("oauth_states").delete().eq("state", state).execute()
        
        # 4) Read back most recent tokens
        r2 = sb.table("user_integrations").select("*").eq("user_id", user_id).eq("provider", "google").order("created_at", desc=True).limit(1).execute()
        rows = get_data(r2) or []
        row = rows[0] if isinstance(rows, list) and rows else rows
        
        # 5) Determine which template to use and provision
        if template_id == "gmail-ai-responder":
            from routes.gmail_responder_routes import GMAIL_AI_RESPONDER_TEMPLATE as template
        elif template_id == "gmail-summary":
            from routes.gmail_summary_routes import GMAIL_SUMMARY_TEMPLATE as template
        else:
            raise HTTPException(400, f"Unknown template ID: {template_id}")
            
        # Import the correct provision function
        if template_id == "gmail-ai-responder":
            result = provision_in_n8n_responder(user_id=user_id, template_id=template_id, integ_row=row, tpl=template)
        elif template_id == "gmail-summary":
            result = provision_in_n8n_summary(user_id=user_id, template_id=template_id, integ_row=row, tpl=template)
        elif template_id == "gmail-ai-labelling":
            result = provision_in_n8n_labelling(user_id=user_id, template_id=template_id, integ_row=row, tpl=template)
            
        # 6) Redirect back to frontend
        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        url = f"{frontend}/dashboard?installed={template_id}&workflowId={result['workflowId']}"
        return RedirectResponse(url=url, status_code=302)
        
    except Exception as e:
        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        msg = f"OAuth callback failed: {str(e)}"
        try:
            from requests.utils import requote_uri
            msg = requote_uri(msg)
        except Exception:
            pass
        url = f"{frontend}/dashboard?oauth_error={msg}"
        return RedirectResponse(url=url, status_code=302)