"""
DB adapter: maps Supabase data to algorithm-ready dicts.
Uses SUPABASE_SERVICE_ROLE_KEY only. Do not expose to frontend.
"""
import os
from typing import Any, Optional

from supabase import create_client

def _client():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def _pref_value(db_val: Optional[int]) -> Any:
    """Map DB preference 0-5 to algorithm: 0 -> 'Don't care', else int 1-5."""
    if db_val is None or db_val == 0:
        return "Don't care"
    return max(1, min(5, int(db_val)))


def _past_positions_list(rows: list) -> list[dict]:
    """Build past_positions list from DB rows (use is_education from DB)."""
    return [
        {
            "title": r.get("title") or "",
            "company": r.get("company") or "",
            "duration": r.get("duration") or "",
            "is_education": bool(r.get("is_education")),
        }
        for r in (rows or [])
    ]


def get_mentor_dict(profile_id: str) -> Optional[dict]:
    """
    Query profiles, mentor_details, past_positions and return a dict
    matching the algorithm's expected mentor structure.
    Returns None if not found or not a mentor.
    """
    client = _client()
    pid = profile_id if isinstance(profile_id, str) else str(profile_id)

    # Profile
    r = client.table("profiles").select("*").eq("id", pid).execute()
    if not r.data or len(r.data) == 0:
        return None
    profile = r.data[0]
    if not profile.get("is_mentor"):
        return None

    # Mentor details
    md = client.table("mentor_details").select("*").eq("profile_id", pid).execute()
    mentor_details = md.data[0] if md.data and len(md.data) > 0 else None
    if not mentor_details:
        # Mentor must have mentor_details to be used in algorithm
        mentor_details = {
            "help_tags": [],
            "help_details": "",
            "pref_location": 0,
            "pref_uni": 0,
            "pref_gpa": 0,
            "pref_industry": 0,
            "pref_help_type": 0,
            "pref_path_alignment": 0,
        }

    # Past positions (order by sort_order)
    pp = (
        client.table("past_positions")
        .select("title, company, duration, is_education, sort_order")
        .eq("profile_id", pid)
        .order("sort_order")
        .execute()
    )
    past = _past_positions_list(pp.data or [])

    return {
        "id": pid,
        "name": profile.get("full_name") or "",
        "current_industry": profile.get("current_industry") or "",
        "location": profile.get("location") or "",
        "current_position": profile.get("current_position") or "",
        "current_company": profile.get("current_company") or "",
        "university": profile.get("university") or "",
        "past_positions": past,
        "what_i_can_help_with": {
            "tags": list(mentor_details.get("help_tags") or []),
            "details": mentor_details.get("help_details") or "",
        },
        "preferences": {
            "location": _pref_value(mentor_details.get("pref_location")),
            "uni": _pref_value(mentor_details.get("pref_uni")),
            "gpa": _pref_value(mentor_details.get("pref_gpa")),
            "industry_alignment": _pref_value(mentor_details.get("pref_industry")),
            "help_type": _pref_value(mentor_details.get("pref_help_type")),
            "path_alignment": _pref_value(mentor_details.get("pref_path_alignment")),
        },
    }


def get_mentee_dict(profile_id: str) -> Optional[dict]:
    """
    Query profiles, mentee_details, past_positions and return a dict
    matching the algorithm's expected mentee structure.
    Returns None if not found or not a mentee.
    """
    client = _client()
    pid = profile_id if isinstance(profile_id, str) else str(profile_id)

    # Profile
    r = client.table("profiles").select("*").eq("id", pid).execute()
    if not r.data or len(r.data) == 0:
        return None
    profile = r.data[0]
    if not profile.get("is_mentee"):
        return None

    # Mentee details (allow missing; use defaults so algorithm can still score)
    md = client.table("mentee_details").select("*").eq("profile_id", pid).execute()
    mentee_details = md.data[0] if md.data and len(md.data) > 0 else {}
    if not mentee_details:
        mentee_details = {"gpa": None, "goals": "", "more_info": "", "help_tags": []}

    # Past positions
    pp = (
        client.table("past_positions")
        .select("title, company, duration, is_education, sort_order")
        .eq("profile_id", pid)
        .order("sort_order")
        .execute()
    )
    past = _past_positions_list(pp.data or [])

    gpa = mentee_details.get("gpa")
    if gpa is not None:
        try:
            gpa = float(gpa)
        except (TypeError, ValueError):
            gpa = None

    return {
        "id": pid,
        "name": profile.get("full_name") or "",
        "current_position": profile.get("current_position") or "",
        "current_company": profile.get("current_company") or "",
        "current_industry": profile.get("current_industry") or "",
        "location": profile.get("location") or "",
        "past_positions": past,
        "gpa": gpa,
        "goals": mentee_details.get("goals") or "",
        "more_info": mentee_details.get("more_info") or "",
        "what_i_need_help_with": list(mentee_details.get("help_tags") or []),
    }


def get_all_mentees_dict() -> list[dict]:
    """Return list of all mentee dicts (algorithm shape). IDs = profile uuid as string."""
    client = _client()
    profiles = (
        client.table("profiles").select("id").eq("is_mentee", True).execute()
    )
    if not profiles.data:
        return []
    out = []
    for row in profiles.data:
        pid = row["id"]
        mentee = get_mentee_dict(str(pid))
        if mentee:
            out.append(mentee)
    return out
