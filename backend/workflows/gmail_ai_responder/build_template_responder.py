# app/workflows/gmail_ai_responder/build_template_responder.py
import copy
import json
import logging

logger = logging.getLogger(__name__)

def build_workflow_from_template(
    tpl: dict,
    gmail_credential_id: str,
    gmail_credential_name: str,
    openai_credential_id: str,
    openai_credential_name: str,
    gemini_credential_id: str = None,
    gemini_credential_name: str = None,
) -> dict:
    wf = copy.deepcopy(tpl)
    logger.info("Processing workflow template nodes...")

    for i, n in enumerate(wf["nodes"]):
        node_type = n.get("type")
        node_name = n.get("name", f"Node-{i}")
        logger.info(f"Processing node {i}: {node_name} (type: {node_type})")

        n.setdefault("credentials", {})

        if node_type in ["n8n-nodes-base.gmail", "n8n-nodes-base.gmailTrigger"]:
            n["credentials"]["gmailOAuth2"] = {
                "id": str(gmail_credential_id),
                "name": gmail_credential_name,
            }
            logger.f(f"  Set Gmail credential for {node_name}")

        elif node_type == "@n8n/n8n-nodes-langchain.lmChatOpenAi":
            n["credentials"]["openAiApi"] = {
                "id": str(openai_credential_id),
                "name": openai_credential_name,
            }
            logger.info(f"  Set OpenAI credential for {node_name}")

        elif node_type == "@n8n/n8n-nodes-langchain.lmChatGoogleGemini":
            if gemini_credential_id and gemini_credential_name:
                n["credentials"]["googlePalmApi"] = {
                    "id": str(gemini_credential_id),
                    "name": gemini_credential_name,
                }
                # remove any placeholder keys if present
                keys_to_remove = [k for k in list(n["credentials"].keys()) if "PLACEHOLDER" in k]
                for k in keys_to_remove:
                    del n["credentials"][k]
                logger.info(f"  Set Gemini credential for {node_name}")
            else:
                logger.warning(f"  No Gemini credentials for {node_name}")

    logger.info("Finished processing workflow template nodes")
    return {
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
    }

def debug_workflow_json(wf_json: dict, file_path: str = "debug_workflow.json"):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(wf_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved debug workflow JSON to {file_path}")

        json_str = json.dumps(wf_json)
        gmail_cred_count = json_str.count('"gmailOAuth2"')
        gemini_cred_count = json_str.count('"googlePalmApi"')
        logger.info(f"Found {gmail_cred_count} gmailOAuth2 credential assignments")
        logger.info(f"Found {gemini_cred_count} googlePalmApi credential assignments")
    except Exception as e:
        logger.error(f"Failed to save debug JSON: {e}")
