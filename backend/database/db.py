# app/db.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE = os.environ["SUPABASE_SERVICE_ROLE"]

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
