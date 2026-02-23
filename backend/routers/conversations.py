"""
Conversations and messages endpoints.
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth import get_user_id_from_request

router = APIRouter(prefix="/api", tags=["conversations"])


def _supabase():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@router.get("/conversations")
def get_conversations(user_id: str = Depends(get_user_id_from_request)):
    """Return all conversations for the authenticated user (mentor or mentee)."""
    sb = _supabase()
    r = sb.table("conversations").select("id, match_id, mentor_id, mentee_id, created_at").or_(f"mentor_id.eq.{user_id},mentee_id.eq.{user_id}").execute()
    if not r.data:
        return {"conversations": []}
    # Enrich with other party profile and unread count
    out = []
    for c in r.data:
        other_id = c["mentee_id"] if str(c["mentor_id"]) == user_id else c["mentor_id"]
        profile = sb.table("profiles").select("full_name").eq("id", other_id).execute()
        name = profile.data[0]["full_name"] if profile.data and len(profile.data) > 0 else "Unknown"
        # Unread: messages in this conversation where read_at IS NULL and sender_id != user_id
        unread = sb.table("messages").select("id").eq("conversation_id", c["id"]).is_("read_at", "null").neq("sender_id", user_id).execute()
        count = len(unread.data) if unread.data else 0
        out.append({
            "id": c["id"],
            "match_id": c["match_id"],
            "mentor_id": str(c["mentor_id"]),
            "mentee_id": str(c["mentee_id"]),
            "created_at": c["created_at"],
            "other_party_id": str(other_id),
            "other_party_name": name,
            "unread_count": count,
        })
    return {"conversations": out}


@router.get("/messages/{conversation_id}")
def get_messages(conversation_id: str, user_id: str = Depends(get_user_id_from_request)):
    """Return all messages in a conversation. User must be participant."""
    sb = _supabase()
    conv = sb.table("conversations").select("id, mentor_id, mentee_id").eq("id", conversation_id).execute()
    if not conv.data or len(conv.data) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    c = conv.data[0]
    if str(c["mentor_id"]) != user_id and str(c["mentee_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    r = sb.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
    return {"messages": r.data or []}


class SendMessageBody(BaseModel):
    body: str


@router.post("/messages/{conversation_id}")
def post_message(conversation_id: str, body: SendMessageBody, user_id: str = Depends(get_user_id_from_request)):
    """Send a message. User must be participant."""
    sb = _supabase()
    conv = sb.table("conversations").select("id, mentor_id, mentee_id").eq("id", conversation_id).execute()
    if not conv.data or len(conv.data) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    c = conv.data[0]
    if str(c["mentor_id"]) != user_id and str(c["mentee_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    ins = sb.table("messages").insert({
        "conversation_id": conversation_id,
        "sender_id": user_id,
        "body": body.body.strip(),
    }).execute()
    if not ins.data or len(ins.data) == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send")
    return {"message": ins.data[0]}


@router.post("/messages/{conversation_id}/read")
def mark_messages_read(conversation_id: str, user_id: str = Depends(get_user_id_from_request)):
    """Mark all messages in this conversation (where recipient is user) as read."""
    sb = _supabase()
    conv = sb.table("conversations").select("id, mentor_id, mentee_id").eq("id", conversation_id).execute()
    if not conv.data or len(conv.data) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    c = conv.data[0]
    if str(c["mentor_id"]) != user_id and str(c["mentee_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    now = datetime.now(timezone.utc).isoformat()
    # Update messages in this conversation that are not from user (so we mark as read messages we received)
    msgs = sb.table("messages").select("id").eq("conversation_id", conversation_id).neq("sender_id", user_id).is_("read_at", "null").execute()
    if msgs.data:
        for m in msgs.data:
            sb.table("messages").update({"read_at": now}).eq("id", m["id"]).execute()
    return {"ok": True}
