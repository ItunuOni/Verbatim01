from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Service role client for admin operations
supabase_admin: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def get_supabase_client() -> Client:
    """Get the Supabase client"""
    return supabase


def get_supabase_admin_client() -> Client:
    """Get the Supabase admin client"""
    return supabase_admin
