# app/deps.py
#This reads the Supabase JWT from the Authorization header and extracts the user id. 
# For a quick start we decode without verification. You can replace later with JWKS verification.
from fastapi import Header, HTTPException

def _parse_without_verify(jwt_token: str) -> dict:
    import base64, json
    parts = jwt_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT")
    def pad(b: str) -> bytes:
        b = b + "=" * (-len(b) % 4)
        return b.encode("utf-8")
    payload = json.loads(base64.urlsafe_b64decode(pad(parts[1])))
    return payload

async def get_user_id(authorization: str = Header(...)) -> str:
    try:
        token = authorization.split(" ")[1]
        payload = _parse_without_verify(token)
        return payload["sub"]
    except Exception:
        raise HTTPException(401, "Invalid or missing token")
