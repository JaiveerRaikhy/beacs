"use client";

import {
  connectMatch,
  getFeed,
  getMatchesReceived,
  respondMatch,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type FeedItem = {
  mentee_id: string;
  name: string;
  university: string;
  location: string;
  current_position: string;
  gpa?: number;
  goals: string;
  help_seeking: string[];
  bilateral_score: number;
  mentor_score: number;
  mentee_score: number;
  goal_alignment_score?: number;
  goal_reasoning: string;
};

export default function MatchPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [isMentor, setIsMentor] = useState(false);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [received, setReceived] = useState<{ id: string; mentor_name: string; mentor_position?: string; mentor_company?: string; status: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedLoaded, setFeedLoaded] = useState(false);

  const loadUser = useCallback(async () => {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      router.push("/login");
      return null;
    }
    const { data: profile } = await supabase.from("profiles").select("is_mentor, is_mentee").eq("id", user.id).single();
    setUserId(user.id);
    setIsMentor(!!profile?.is_mentor);
    return { user, profile };
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const u = await loadUser();
      if (!u || cancelled) return;
      try {
        if (u.profile?.is_mentor) {
          setReceived([]);
        } else if (u.profile?.is_mentee) {
          const res = await getMatchesReceived();
          setReceived(res.matches || []);
          setFeed([]);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [loadUser]);

  const loadFeed = async () => {
    if (!userId) return;
    setError(null);
    setFeedLoaded(true);
    setLoading(true);
    try {
      const res = await getFeed(userId);
      setFeed(res.feed || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load matches");
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (item: FeedItem) => {
    if (!userId) return;
    setActionLoading(item.mentee_id);
    setError(null);
    try {
      await connectMatch(userId, item.mentee_id, {
        bilateral_score: item.bilateral_score,
        mentor_score: item.mentor_score,
        mentee_score: item.mentee_score,
        goal_alignment: item.goal_alignment_score,
      });
      setFeed((prev) => prev.filter((x) => x.mentee_id !== item.mentee_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRespond = async (matchId: string, response: "accepted" | "declined") => {
    setActionLoading(matchId);
    setError(null);
    try {
      const res = await respondMatch(matchId, response);
      setReceived((prev) => prev.filter((m) => m.id !== matchId));
      if (response === "accepted" && (res as { conversation_id?: string }).conversation_id) {
        router.push(`/messages?c=${(res as { conversation_id: string }).conversation_id}`);
        router.refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to respond");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && !feedLoaded && received.length === 0) {
    return (
      <main className="min-h-screen p-6 flex items-center justify-center">
        <p className="text-gray-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-6 max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard" className="text-sm text-gray-600 hover:underline">
          Back to dashboard
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">
          {isMentor ? "Find Mentees" : "Connection requests"}
        </h1>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {isMentor && (
        <>
          {!feedLoaded ? (
            <div className="border border-gray-200 rounded-lg p-6 bg-white">
              <p className="text-gray-600 mb-4">Get personalized mentee matches based on your preferences.</p>
              <button
                type="button"
                onClick={loadFeed}
                disabled={loading}
                className="px-4 py-2 bg-gray-900 text-white rounded font-medium disabled:opacity-50"
              >
                {loading ? "Loading…" : "Get matches"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {feed.length === 0 && !loading && (
                <p className="text-gray-500">No matches above threshold, or you’ve connected with everyone.</p>
              )}
              {feed.map((item) => (
                <div key={item.mentee_id} className="border border-gray-200 rounded-lg p-4 bg-white">
                  <h3 className="font-medium text-gray-900">{item.name}</h3>
                  <p className="text-sm text-gray-500">{item.university} · {item.location}</p>
                  <p className="text-sm text-gray-700 mt-1">{item.current_position}{item.gpa != null ? ` · GPA ${item.gpa}` : ""}</p>
                  {item.goals && <p className="text-sm text-gray-600 mt-1">Goals: {item.goals}</p>}
                  {item.help_seeking?.length > 0 && (
                    <p className="text-sm text-gray-600 mt-1">Help: {item.help_seeking.join(", ")}</p>
                  )}
                  <p className="text-sm text-gray-500 mt-2">
                    Bilateral: {item.bilateral_score} · Your view: {item.mentor_score} · Their view: {item.mentee_score}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{item.goal_reasoning}</p>
                  <div className="flex gap-2 mt-3">
                    <button
                      type="button"
                      onClick={() => handleConnect(item)}
                      disabled={actionLoading === item.mentee_id}
                      className="px-3 py-1.5 bg-gray-900 text-white rounded text-sm disabled:opacity-50"
                    >
                      Connect
                    </button>
                    <button
                      type="button"
                      onClick={() => setFeed((p) => p.filter((x) => x.mentee_id !== item.mentee_id))}
                      className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!isMentor && (
        <div className="space-y-4">
          {received.length === 0 ? (
            <p className="text-gray-500">No connection requests yet.</p>
          ) : (
            received.map((m) => (
              <div key={m.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                <h3 className="font-medium text-gray-900">{m.mentor_name}</h3>
                {(m.mentor_position || m.mentor_company) && (
                  <p className="text-sm text-gray-600">{[m.mentor_position, m.mentor_company].filter(Boolean).join(" at ")}</p>
                )}
                <div className="flex gap-2 mt-3">
                  <button
                    type="button"
                    onClick={() => handleRespond(m.id, "accepted")}
                    disabled={actionLoading === m.id}
                    className="px-3 py-1.5 bg-gray-900 text-white rounded text-sm disabled:opacity-50"
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRespond(m.id, "declined")}
                    disabled={actionLoading === m.id}
                    className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </main>
  );
}
