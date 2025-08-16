def get_data(res):
    # Works for both PostgrestResponse objects and dicts
    if res is None:
        return None
    if hasattr(res, "data"):
        return res.data
    if isinstance(res, dict):
        return res.get("data", None)
    return None

def get_error(res):
    if res is None:
        return "No response from Supabase"
    if hasattr(res, "error") and res.error:
        return res.error
    if isinstance(res, dict):
        return res.get("error", None)
    return None
