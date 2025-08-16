# app/main.py

from dotenv import load_dotenv
load_dotenv()  # load .env before any local imports that read env

import os, json, secrets, time
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.deps import get_user_id
from database.db import sb
from database.sb_utils import get_data, get_error
from thirdPartyIntegrations.google_oauth import build_auth_url, exchange_code_for_tokens
from n8n.n8n_client import upsert_gmail_credential, create_workflow, activate_workflow, upsert_openai_credential, upsert_gemini_credential
import logging, traceback
from fastapi import status
from fastapi.responses import RedirectResponse
import requests
from datetime import datetime, timezone
import json

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]  # Add this line
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

# Load template once (your JSON is in backend/templates/)
try:
    TEMPLATES = {
        "gmail-ai-responder": json.loads(
            open(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "gmail_ai_responder.json"),
                "r",
                encoding="utf-8",
            ).read()
        )
    }
    logger.info("Templates loaded successfully")
except Exception as e:
    logger.error(f"Failed to load templates: {e}")
    TEMPLATES = {}

class InstallBody(BaseModel):
    templateId: str

def build_workflow_from_template(
    tpl: dict, 
    gmail_credential_id: str, 
    gmail_credential_name: str, 
    openai_credential_id: str, 
    openai_credential_name: str,
    gemini_credential_id: str = None,
    gemini_credential_name: str = None
) -> dict:
    import copy
    wf = copy.deepcopy(tpl)
    
    logger.info("Processing workflow template nodes...")
    
    for i, n in enumerate(wf["nodes"]):
        node_type = n.get("type")
        node_name = n.get("name", f"Node-{i}")
        logger.info(f"Processing node {i}: {node_name} (type: {node_type})")
        
        # Handle Gmail nodes (both regular and trigger)
        if node_type in ["n8n-nodes-base.gmail", "n8n-nodes-base.gmailTrigger"]:
            if "credentials" not in n:
                n["credentials"] = {}
                
            n["credentials"]["gmailOAuth2"] = {
                "id": str(gmail_credential_id),
                "name": gmail_credential_name
            }
            logger.info(f"  Set Gmail credential: ID={gmail_credential_id}, Name={gmail_credential_name}")
                
        # Handle OpenAI nodes
        elif node_type == "@n8n/n8n-nodes-langchain.lmChatOpenAi":
            if "credentials" not in n:
                n["credentials"] = {}
                
            n["credentials"]["openAiApi"] = {
                "id": str(openai_credential_id),
                "name": openai_credential_name
            }
            logger.info(f"  Set OpenAI credential for {node_name}")
            
        # Handle Google Gemini nodes
        elif node_type == "@n8n/n8n-nodes-langchain.lmChatGoogleGemini":
            if "credentials" not in n:
                n["credentials"] = {}
                
            if gemini_credential_id and gemini_credential_name:
                # Replace any placeholder credential key with the correct one
                n["credentials"]["googlePalmApi"] = {  # Correct credential key
                    "id": str(gemini_credential_id),
                    "name": gemini_credential_name
                }
                # Remove any placeholder credentials
                keys_to_remove = [k for k in n["credentials"].keys() if "PLACEHOLDER" in k]
                for key in keys_to_remove:
                    del n["credentials"][key]
                logger.info(f"  Set Gemini credential for {node_name}: ID={gemini_credential_id}, Name={gemini_credential_name}")
            else:
                logger.warning(f"  No Gemini credentials provided for {node_name}")
        
        # Log final credentials after processing
        if "credentials" in n:
            logger.info(f"  Final credentials: {n['credentials']}")
    
    logger.info("Finished processing workflow template nodes")
    
    return {
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
    }

def debug_workflow_json(wf_json: dict, file_path: str = "debug_workflow.json"):
    """Save the processed workflow JSON to a file for inspection"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(wf_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved debug workflow JSON to {file_path}")
        
        # Check for credential assignment
        json_str = json.dumps(wf_json)
        gmail_cred_count = json_str.count('"gmailOAuth2"')
        gemini_cred_count = json_str.count('"googlePalmApi"')
        logger.info(f"✅ Found {gmail_cred_count} gmailOAuth2 credential assignments")
        logger.info(f"✅ Found {gemini_cred_count} googlePalmApi credential assignments")
            
    except Exception as e:
        logger.error(f"Failed to save debug JSON: {e}")

def _upsert_user_integration_tokens(user_id: str, tokens: dict) -> None:
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    scope = tokens.get("scope", "")
    expires_in = int(tokens.get("expires_in", 3600))
    expiry_ts = int(time.time()) + expires_in

    res = sb.table("user_integrations").upsert(
        {
            "user_id": user_id,
            "provider": "google",
            "access_token": access_token,
            "refresh_token": refresh_token or "",
            "scope": scope,
            "expiry": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_ts)),
        },
        on_conflict="user_id,provider",
    ).execute()
    err = get_error(res)
    if err:
        raise HTTPException(500, f"Supabase upsert error: {err}")

def _provision_in_n8n(user_id: str, template_id: str, integ_row: dict) -> dict:
    logger.info(f"Starting n8n provisioning for user {user_id}, template {template_id}")
    
    # Create Gmail credential
    gmail_cred_name = f"gmail-oauth2-{user_id}"
    gmail_payload = {
        "clientId": GOOGLE_CLIENT_ID,
        "clientSecret": GOOGLE_CLIENT_SECRET,
        "oauthTokenData": {
            "access_token": integ_row["access_token"],
            "refresh_token": integ_row.get("refresh_token") or "",
            "scope": integ_row.get("scope", ""),
            "token_type": "Bearer",
        }
    }
    
    if integ_row.get("expiry"):
        try:
            expiry_ms = int(datetime.fromisoformat(
                integ_row["expiry"].replace("Z", "+00:00")
            ).timestamp() * 1000)
            gmail_payload["oauthTokenData"]["expiry_date"] = expiry_ms
            logger.info(f"Added expiry_date: {expiry_ms}")
        except Exception as e:
            logger.warning(f"Could not parse expiry date: {e}")

    logger.info("Creating gmailOAuth2 credential in n8n...")
    gmail_cred_info = upsert_gmail_credential(gmail_cred_name, gmail_payload)
    logger.info(f"Created Gmail credential: {gmail_cred_info}")

    # Create OpenAI credential
    openai_cred_name = f"openai-{user_id}"
    logger.info("Creating openAiApi credential in n8n...")
    openai_cred_info = upsert_openai_credential(openai_cred_name, OPENAI_KEY)
    logger.info(f"Created OpenAI credential: {openai_cred_info}")

    # Create Gemini credential
    gemini_cred_name = f"gemini-{user_id}"
    logger.info("Creating googleGeminiApi credential in n8n...")
    gemini_cred_info = upsert_gemini_credential(gemini_cred_name, GEMINI_KEY)
    logger.info(f"Created Gemini credential: {gemini_cred_info}")

    logger.info("Building workflow from template...")
    wf_json = build_workflow_from_template(
        TEMPLATES[template_id],
        gmail_credential_id=gmail_cred_info["id"],
        gmail_credential_name=gmail_cred_info["name"],
        openai_credential_id=openai_cred_info["id"],
        openai_credential_name=openai_cred_info["name"],
        gemini_credential_id=gemini_cred_info["id"],
        gemini_credential_name=gemini_cred_info["name"],
    )
    
    # Debug the processed workflow
    debug_workflow_json(wf_json, f"debug_workflow_{user_id}_{template_id}.json")
    
    logger.info("Creating workflow in n8n...")
    wid = create_workflow(f"{template_id}-{user_id}", wf_json)
    logger.info(f"Created workflow with ID: {wid}")
    
    logger.info(f"Attempting to activate workflow {wid}...")
    
    try:
        activate_workflow(wid)
        logger.info(f"Successfully activated workflow {wid}")
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

# ... rest of your code remains the same ...

# ... rest of your code remains the same ...

# Replace the install function in your main.py with this fixed version

@app.post("/workflows/install")
def install(body: InstallBody, user_id: str = Depends(get_user_id)):
    logger.info(f"Install request for template: {body.templateId}, user: {user_id}")
    
    try:
        if body.templateId not in TEMPLATES:
            logger.error(f"Unknown templateId: {body.templateId}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown templateId")

        logger.info("Checking for existing user integrations...")
        # FIXED: Use order().limit(1) instead of maybe_single()
        res = (
            sb.table("user_integrations")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", "google")
            .order("created_at", desc=True)  # newest first
            .limit(1)
            .execute()
        )
        err = get_error(res)
        if err:
            logger.error(f"Supabase select error: {err}")
            raise HTTPException(500, f"Supabase select error: {err}")
        
        rows = get_data(res) or []
        tokens_row = rows[0] if isinstance(rows, list) and rows else None

        if not tokens_row:
            logger.info("No existing tokens, creating OAuth state...")
            state = secrets.token_urlsafe(24)
            ins = sb.table("oauth_states").insert(
                {"state": state, "user_id": user_id, "template_id": body.templateId}
            ).execute()
            if get_error(ins):
                logger.error(f"Supabase insert error: {get_error(ins)}")
                raise HTTPException(500, f"Supabase insert error: {get_error(ins)}")
            
            auth_url = build_auth_url(state)
            logger.info(f"Returning OAuth URL: {auth_url}")
            return {"needsAuth": True, "authUrl": auth_url, "state": state, "templateId": body.templateId}

        # tokens exist → provision now
        logger.info("Tokens exist, provisioning in n8n...")
        result = _provision_in_n8n(user_id, body.templateId, tokens_row)
        logger.info(f"Provisioning successful: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Install failed with exception: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Install failed: {e}")


@app.get("/oauth/google/callback")
def google_callback(code: str, state: str):
    logger.info(f"OAuth callback received with state: {state}")

    try:
        # 1) find and validate state
        s_res = (
            sb.table("oauth_states")
            .select("*")
            .eq("state", state)
            .maybe_single()
            .execute()
        )
        err = get_error(s_res)
        if err:
            logger.error(f"Supabase select error: {err}")
            raise HTTPException(500, f"Supabase select error: {err}")
        s = get_data(s_res)
        if not s:
            logger.error(f"Invalid state: {state}")
            raise HTTPException(400, "Invalid state")

        user_id = s["user_id"]
        template_id = s["template_id"]
        if template_id not in TEMPLATES:
            logger.error(f"Unknown templateId in callback: {template_id}")
            raise HTTPException(400, "Unknown templateId")

        # 2) exchange authorization code for tokens
        logger.info("Exchanging OAuth code for tokens...")
        tokens = exchange_code_for_tokens(code)
        _upsert_user_integration_tokens(user_id, tokens)

        # 3) delete the used state
        del_res = sb.table("oauth_states").delete().eq("state", state).execute()
        err = get_error(del_res)
        if err:
            logger.error(f"Supabase delete error: {err}")
            raise HTTPException(500, f"Supabase delete error: {err}")

        # 4) read back most recent google tokens for safety
        r2 = (
            sb.table("user_integrations")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", "google")
            .order("created_at", desc=True)   # keep newest if duplicates exist
            .limit(1)
            .execute()
        )
        err = get_error(r2)
        if err:
            logger.error(f"Supabase select error: {err}")
            raise HTTPException(500, f"Supabase select error: {err}")

        rows = get_data(r2) or []
        row = rows[0] if isinstance(rows, list) and rows else rows
        if not row:
            logger.error("Missing tokens after OAuth")
            raise HTTPException(400, "Missing tokens after OAuth")

        # 5) provision in n8n
        result = _provision_in_n8n(user_id, template_id, row)
        logger.info(f"OAuth callback successful: {result}")

        # 6) redirect back to dashboard with success flags
        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        url = f"{frontend}/dashboard?installed={template_id}&workflowId={result['workflowId']}"
        return RedirectResponse(url=url, status_code=302)

    except HTTPException as he:
        # on error, redirect with an error message so the UI can toast it
        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        url = f"{frontend}/dashboard?oauth_error={he.detail}"
        logger.error(f"OAuth callback failed: {he.detail}")
        return RedirectResponse(url=url, status_code=302)

    except Exception as e:
        frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        msg = f"OAuth callback failed: {str(e)}"
        logger.error(msg)
        url = f"{frontend}/dashboard?oauth_error={requests.utils.requote_uri(msg) if 'requests' in globals() else msg}"
        return RedirectResponse(url=url, status_code=302)