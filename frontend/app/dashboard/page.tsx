"use client";

import {
  getConversations,
  getMatchesReceived,
  getMatchesSent,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<{ is_mentor?: boolean; is_mentee?: boolean } | null>(null);
  const [conversations, setConversations] = useState<{ id: string; other_party_name: string; unread_count: number }[]>([]);
  const [sent, setSent] = useState<{ id: string; mentee_name: string; status: string }[]>([]);
  const [received, setReceived] = useState<{ id: string; mentor_name: string; status: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.push("/login");
        return;
      }
      const { data: profileRow } = await supabase
        .from("profiles")
        .select("is_mentor, is_mentee")
        .eq("id", user.id)
        .single();
      setProfile(profileRow || null);

      try {
        const [convRes, sentRes, recvRes] = await Promise.all([
          getConversations(),
          getMatchesSent(),
          getMatchesReceived(),
        ]);
        setConversations(convRes.conversations || []);
        setSent(sentRes.matches || []);
        setReceived(recvRes.matches || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  if (loading) {
    return (
      <main className="min-h-screen p-6 flex items-center justify-center">
        <p className="text-gray-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-6 max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <div className="flex gap-2">
          <Link href="/profile" className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50">
            Profile
          </Link>
          <button
            type="button"
            onClick={async () => {
              const supabase = createClient();
              await supabase.auth.signOut();
              router.push("/");
              router.refresh();
            }}
            className="px-3 py-1.5 text-sm text-gray-600 hover:underline"
          >
            Sign out
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {profile?.is_mentor && (
        <section className="mb-6 border border-gray-200 rounded-lg p-4 bg-white">
          <h2 className="font-medium text-gray-900 mb-2">Your connection requests</h2>
          {sent.length === 0 ? (
            <p className="text-sm text-gray-500">None yet.</p>
          ) : (
            <ul className="space-y-2">
              {sent.slice(0, 5).map((m) => (
                <li key={m.id} className="text-sm text-gray-700">
                  {m.mentee_name} — <span className="text-gray-500">{m.status}</span>
                </li>
              ))}
            </ul>
          )}
          <Link href="/match" className="inline-block mt-3 px-4 py-2 bg-gray-900 text-white rounded text-sm font-medium hover:bg-gray-800">
            Find Mentees
          </Link>
        </section>
      )}

      {profile?.is_mentee && (
        <section className="mb-6 border border-gray-200 rounded-lg p-4 bg-white">
          <h2 className="font-medium text-gray-900 mb-2">Match requests &amp; active matches</h2>
          {received.length === 0 ? (
            <p className="text-sm text-gray-500">None yet.</p>
          ) : (
            <ul className="space-y-2">
              {received.slice(0, 5).map((m) => (
                <li key={m.id} className="text-sm text-gray-700">
                  {m.mentor_name} — <span className="text-gray-500">{m.status}</span>
                </li>
              ))}
            </ul>
          )}
          <Link href="/match" className="inline-block mt-3 px-4 py-2 bg-gray-900 text-white rounded text-sm font-medium hover:bg-gray-800">
            Find Mentors
          </Link>
        </section>
      )}

      <section className="border border-gray-200 rounded-lg p-4 bg-white">
        <h2 className="font-medium text-gray-900 mb-2">Conversations</h2>
        {conversations.length === 0 ? (
          <p className="text-sm text-gray-500">No conversations yet.</p>
        ) : (
          <ul className="space-y-2">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link href={`/messages?c=${c.id}`} className="flex justify-between items-center text-sm text-gray-700 hover:bg-gray-50 rounded p-2">
                  <span>{c.other_party_name}</span>
                  {c.unread_count > 0 && (
                    <span className="bg-gray-900 text-white text-xs rounded-full px-2 py-0.5">
                      {c.unread_count}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
        <Link href="/messages" className="inline-block mt-3 text-sm text-gray-600 underline">
          Open messages
        </Link>
      </section>
    </main>
  );
}
