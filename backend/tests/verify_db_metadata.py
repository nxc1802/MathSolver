import os
import json
from app.supabase_client import get_supabase

def verify_metadata():
    supabase = get_supabase()
    
    # Get the 5 most recent assistant messages
    res = supabase.table("messages") \
        .select("id, role, content, metadata, created_at") \
        .eq("role", "assistant") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()
    
    if not res.data:
        print("No assistant messages found.")
        return

    for i, msg in enumerate(res.data):
        print(f"\n--- Message {i+1} (ID: {msg['id']}, Created: {msg['created_at']}) ---")
        metadata = msg.get("metadata", {})
        
        required_fields = ["job_id", "coordinates", "polygon_order", "drawing_phases", "circles"]
        missing = [f for f in required_fields if f not in metadata]
        
        if not missing:
            print("✅ All mandatory fields present in metadata.")
            # Print a snippet of the data
            print(f"   - job_id: {metadata.get('job_id')}")
            print(f"   - polygon_order: {metadata.get('polygon_order')}")
            print(f"   - drawing_phases count: {len(metadata.get('drawing_phases', []))}")
            print(f"   - circles count: {len(metadata.get('circles', []))}")
        else:
            print(f"❌ Missing fields in metadata: {missing}")
            print(f"   Metadata keys: {list(metadata.keys())}")

if __name__ == "__main__":
    verify_metadata()
