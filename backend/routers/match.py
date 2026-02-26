"""
Match and respond endpoints. Run from repo root: uvicorn backend.main:app
"""
import os
import sys
from datetime import datetime, timezone

# Ensure repo root is on path so algorithm modules load
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from db_adapter import get_all_mentees_dict, get_mentor_dict
from auth import get_user_id_from_request

router = APIRouter(prefix="/api", tags=["match"])


class MatchRequest(BaseModel):
    mentor_id: str


class MatchRespondRequest(BaseModel):
    match_id: str
    response: str  # "accepted" | "declined"


class MatchConnectRequest(BaseModel):
    mentor_id: str
    mentee_id: str
    bilateral_score: float | None = None
    mentor_score: float | None = None
    mentee_score: float | None = None
    goal_alignment: float | None = None


def _supabase():
    from supabase import create_client
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@router.get("/matches/received")
def get_matches_received(user_id: str = Depends(get_user_id_from_request)):
    """For mentee: matches where mentor has sent a request (mentor_decided_at set), status pending."""
    sb = _supabase()
    r = sb.table("matches").select("id, mentor_id, mentee_id, status, bilateral_score, mentor_score, mentee_score, goal_alignment, mentor_decided_at, created_at").eq("mentee_id", user_id).order("created_at", desc=True).execute()
    rows = [m for m in (r.data or []) if m.get("mentor_decided_at")]  # mentor has sent request
    if not rows:
        return {"matches": []}
    out = []
    for m in rows:
        mentor = sb.table("profiles").select("full_name, current_position, current_company, current_industry, location").eq("id", m["mentor_id"]).execute()
        mentor_data = mentor.data[0] if mentor.data and len(mentor.data) > 0 else {}
        out.append({
            "id": m["id"],
            "mentor_id": str(m["mentor_id"]),
            "status": m["status"],
            "bilateral_score": m.get("bilateral_score"),
            "mentor_score": m.get("mentor_score"),
            "mentee_score": m.get("mentee_score"),
            "goal_alignment": m.get("goal_alignment"),
            "mentor_decided_at": m.get("mentor_decided_at"),
            "created_at": m["created_at"],
            "mentor_name": mentor_data.get("full_name") or "Unknown",
            "mentor_position": mentor_data.get("current_position"),
            "mentor_company": mentor_data.get("current_company"),
            "mentor_industry": mentor_data.get("current_industry"),
            "mentor_location": mentor_data.get("location"),
        })
    return {"matches": out}


@router.get("/matches/sent")
def get_matches_sent(user_id: str = Depends(get_user_id_from_request)):
    """For mentor: matches they have sent (mentor_id = user)."""
    sb = _supabase()
    r = sb.table("matches").select("id, mentor_id, mentee_id, status, bilateral_score, mentor_decided_at, mentee_decided_at, created_at").eq("mentor_id", user_id).order("created_at", desc=True).execute()
    if not r.data:
        return {"matches": []}
    out = []
    for m in r.data:
        mentee = sb.table("profiles").select("full_name, current_position, current_company").eq("id", m["mentee_id"]).execute()
        mentee_data = mentee.data[0] if mentee.data and len(mentee.data) > 0 else {}
        out.append({
            "id": m["id"],
            "mentee_id": str(m["mentee_id"]),
            "status": m["status"],
            "bilateral_score": m.get("bilateral_score"),
            "mentor_decided_at": m.get("mentor_decided_at"),
            "mentee_decided_at": m.get("mentee_decided_at"),
            "created_at": m["created_at"],
            "mentee_name": mentee_data.get("full_name") or "Unknown",
            "mentee_position": mentee_data.get("current_position"),
            "mentee_company": mentee_data.get("current_company"),
        })
    return {"matches": out}


@router.post("/match")
def post_match(body: MatchRequest, user_id: str = Depends(get_user_id_from_request)):
    """Auth required. Build feed for mentor using algorithm. Returns ranked mentees with scores."""
    if body.mentor_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    mentor_dict = get_mentor_dict(body.mentor_id)
    if not mentor_dict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor profile not found")

    sb = _supabase()
    existing = sb.table("matches").select("mentee_id").eq("mentor_id", body.mentor_id).execute()
    excluded_ids = [str(r["mentee_id"]) for r in (existing.data or [])]

    all_mentees = get_all_mentees_dict()
    filtered_mentees = [m for m in all_mentees if m["id"] not in excluded_ids]
    data = {"mentors": [mentor_dict], "mentees": filtered_mentees}

    from beacon_feed_generation_v2 import generate_mentor_feed

    feed = generate_mentor_feed(
        body.mentor_id,
        data,
        feed_size=20,
        min_bilateral_score=50.0,
        excluded_mentee_ids=excluded_ids,
    )
    return {"feed": feed}


@router.post("/match/connect")
def post_match_connect(body: MatchConnectRequest, user_id: str = Depends(get_user_id_from_request)):
    """Mentor creates a connection request (match row with status pending, mentor_decided_at set)."""
    if body.mentor_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    sb = _supabase()
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "mentor_id": body.mentor_id,
        "mentee_id": body.mentee_id,
        "status": "pending",
        "mentor_decided_at": now,
        "updated_at": now,
    }
    if body.bilateral_score is not None:
        row["bilateral_score"] = body.bilateral_score
    if body.mentor_score is not None:
        row["mentor_score"] = body.mentor_score
    if body.mentee_score is not None:
        row["mentee_score"] = body.mentee_score
    if body.goal_alignment is not None:
        row["goal_alignment"] = body.goal_alignment
    ins = sb.table("matches").insert(row).execute()
    if not ins.data or len(ins.data) == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create match")
    return {"ok": True, "match_id": str(ins.data[0]["id"])}


@router.post("/match/respond")
def post_match_respond(body: MatchRespondRequest, user_id: str = Depends(get_user_id_from_request)):
    """Update match status; if both accept, create conversation."""
    if body.response not in ("accepted", "declined"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="response must be accepted or declined")

    sb = _supabase()
    r = sb.table("matches").select("*").eq("id", body.match_id).execute()
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    row = r.data[0]
    mentor_id = str(row["mentor_id"])
    mentee_id = str(row["mentee_id"])

    now = datetime.now(timezone.utc).isoformat()
    if user_id == mentor_id:
        sb.table("matches").update({
            "status": body.response,
            "mentor_decided_at": now,
            "updated_at": now,
        }).eq("id", body.match_id).execute()
    elif user_id == mentee_id:
        sb.table("matches").update({
            "status": body.response,
            "mentee_decided_at": now,
            "updated_at": now,
        }).eq("id", body.match_id).execute()
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # If both accepted, ensure conversation exists
    if body.response == "accepted":
        recheck = sb.table("matches").select("mentor_decided_at, mentee_decided_at, status").eq("id", body.match_id).execute()
        if recheck.data and len(recheck.data) > 0:
            m = recheck.data[0]
            if m.get("status") == "accepted" and m.get("mentor_decided_at") and m.get("mentee_decided_at"):
                existing_conv = sb.table("conversations").select("id").eq("match_id", body.match_id).execute()
                if not existing_conv.data or len(existing_conv.data) == 0:
                    ins = sb.table("conversations").insert({
                        "match_id": body.match_id,
                        "mentor_id": mentor_id,
                        "mentee_id": mentee_id,
                    }).execute()
                    if ins.data and len(ins.data) > 0:
                        return {"ok": True, "conversation_id": str(ins.data[0]["id"])}
    return {"ok": True}
