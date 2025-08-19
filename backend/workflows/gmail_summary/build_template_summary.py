import copy
import logging
import json

logger = logging.getLogger(__name__)

def build_workflow_from_template(
    tpl: dict,
    gmail_credential_id: str,
    gmail_credential_name: str,
    openai_credential_id: str,
    openai_credential_name: str,
) -> dict:
    
    wf = copy.deepcopy(tpl)
    logger.info("Processing gmail summary agent workflow template nodes...")
    
    for i, n in enumerate(wf["nodes"]):
        node_type = n.get("type")
        node_name = n.get("name", f"Node-{i}")
        logger.info(f"Processing node {i}: {node_name} (type: {node_type})")

        n.setdefault("credentials", {})
        
        if node_type in ["n8n-nodes-base.gmail", "n8n-nodes-base.gmailTrigger"]:
            n["credentials"]["gmailOAuth2"] = {
                "id": str(gmail_credential_id),
                "name": gmail_credential_name
            }
            
            logger.info(f"  Set Gmail credential for {node_name}")
        elif node_type == "@n8n/n8n-nodes-langchain.lmChatOpenAi":
            n["credentials"]["openAi"] = {
                "id": str(openai_credential_id),
                "name": openai_credential_name
            }
            logger.info(f"  Set OpenAI credential for {node_name}")
        
    logger.info("Finished processing gmail summary agent workflow template nodes")
    return {
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf["settings"]
    }
    
def debug_workflow_json(wf_json: dict, file_path: str = "debug_gmail_summary_workflow.json"):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(wf_json, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved debug workflow JSON to {file_path}")

        json_str = json.dumps(wf_json)
        gmail_cred_count = json_str.count('"gmailOAuth2"')
        openai_cred_count = json_str.count('"openAiApi"')
        logger.info(f"Found {gmail_cred_count} gmailOAuth2 credential assignments")
        logger.info(f"Found {openai_cred_count} openAiApi credential assignments")
    except Exception as e:
        logger.error(f"Failed to save debug JSON: {e}")
