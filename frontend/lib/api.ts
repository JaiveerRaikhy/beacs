const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getSessionToken(): Promise<string | null> {
  const { createClient } = await import("@/lib/supabase/client");
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getSessionToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function getFeed(mentorId: string) {
  return apiFetch("/api/match", {
    method: "POST",
    body: JSON.stringify({ mentor_id: mentorId }),
  });
}

export async function connectMatch(mentorId: string, menteeId: string, scores?: { bilateral_score?: number; mentor_score?: number; mentee_score?: number; goal_alignment?: number }) {
  return apiFetch("/api/match/connect", {
    method: "POST",
    body: JSON.stringify({
      mentor_id: mentorId,
      mentee_id: menteeId,
      ...scores,
    }),
  });
}

export async function respondMatch(matchId: string, response: "accepted" | "declined") {
  return apiFetch("/api/match/respond", {
    method: "POST",
    body: JSON.stringify({ match_id: matchId, response }),
  });
}

export async function getMatchesReceived() {
  return apiFetch("/api/matches/received");
}

export async function getMatchesSent() {
  return apiFetch("/api/matches/sent");
}

export async function getConversations() {
  return apiFetch("/api/conversations");
}

export async function getMessages(conversationId: string) {
  return apiFetch(`/api/messages/${conversationId}`);
}

export async function sendMessage(conversationId: string, body: string) {
  return apiFetch(`/api/messages/${conversationId}`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export async function markMessagesRead(conversationId: string) {
  return apiFetch(`/api/messages/${conversationId}/read`, { method: "POST" });
}
