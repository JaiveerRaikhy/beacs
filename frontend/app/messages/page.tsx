"use client";

import {
  getConversations,
  getMessages,
  markMessagesRead,
  sendMessage,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

type Message = { id: string; sender_id: string; body: string; created_at: string; read_at: string | null };
type Conversation = { id: string; other_party_name: string; unread_count: number };

function MessagesContent() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("c");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    const res = await getConversations();
    setConversations(res.conversations || []);
  }, []);

  const loadMessages = useCallback(
    async (convId: string) => {
      if (!convId) {
        setMessages([]);
        return;
      }
      setLoading(true);
      try {
        const res = await getMessages(convId);
        setMessages(res.messages || []);
        await markMessagesRead(convId);
        await loadConversations();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load messages");
      } finally {
        setLoading(false);
      }
    },
    [loadConversations]
  );

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      setUserId(user?.id ?? null);
      try {
        await loadConversations();
      } catch {
        setConversations([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [loadConversations]);

  useEffect(() => {
    if (selectedId) loadMessages(selectedId);
    else setMessages([]);
  }, [selectedId, loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Real-time: subscribe to messages for selected conversation
  useEffect(() => {
    if (!selectedId || !userId) return;
    const supabase = createClient();
    const channel = supabase
      .channel(`messages:${selectedId}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "messages", filter: `conversation_id=eq.${selectedId}` },
        () => {
          loadMessages(selectedId);
        }
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [selectedId, userId, loadMessages]);

  const handleSend = async () => {
    const text = body.trim();
    if (!text || !selectedId || sending) return;
    setSending(true);
    setError(null);
    try {
      await sendMessage(selectedId, text);
      setBody("");
      await loadMessages(selectedId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send");
    } finally {
      setSending(false);
    }
  };

  const selectedConv = conversations.find((c) => c.id === selectedId);

  return (
    <main className="min-h-screen flex flex-col md:flex-row">
      <aside className="w-full md:w-72 border-b md:border-b-0 md:border-r border-gray-200 bg-white flex-shrink-0">
        <div className="p-4 border-b border-gray-200 flex items-center gap-2">
          <Link href="/dashboard" className="text-sm text-gray-600 hover:underline">
            Dashboard
          </Link>
        </div>
        <ul className="divide-y divide-gray-100">
          {conversations.map((c) => (
            <li key={c.id}>
              <Link
                href={`/messages?c=${c.id}`}
                className={`block p-3 text-sm ${selectedId === c.id ? "bg-gray-100 font-medium text-gray-900" : "text-gray-700 hover:bg-gray-50"}`}
              >
                <span className="flex justify-between items-center">
                  {c.other_party_name}
                  {c.unread_count > 0 && (
                    <span className="bg-gray-900 text-white text-xs rounded-full px-2 py-0.5">
                      {c.unread_count}
                    </span>
                  )}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {conversations.length === 0 && !loading && (
          <p className="p-4 text-sm text-gray-500">No conversations.</p>
        )}
      </aside>

      <section className="flex-1 flex flex-col min-h-[60vh]">
        {selectedId ? (
          <>
            <div className="p-4 border-b border-gray-200 bg-white">
              <h2 className="font-medium text-gray-900">{selectedConv?.other_party_name ?? "Conversation"}</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {loading ? (
                <p className="text-gray-500">Loading…</p>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${msg.sender_id === userId ? "ml-auto bg-gray-900 text-white" : "bg-white border border-gray-200 text-gray-900"}`}
                  >
                    {msg.body}
                  </div>
                ))
              )}
              <div ref={bottomRef} />
            </div>
            {error && <p className="px-4 py-2 text-sm text-red-600">{error}</p>}
            <div className="p-4 border-t border-gray-200 bg-white flex gap-2">
              <input
                type="text"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Type a message…"
                className="flex-1 px-3 py-2 border border-gray-300 rounded text-gray-900"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={sending || !body.trim()}
                className="px-4 py-2 bg-gray-900 text-white rounded font-medium disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-8 text-gray-500">
            Select a conversation or go to dashboard to start one.
          </div>
        )}
      </section>
    </main>
  );
}

export default function MessagesPage() {
  return (
    <Suspense fallback={<main className="min-h-screen p-6 flex items-center justify-center"><p className="text-gray-500">Loading…</p></main>}>
      <MessagesContent />
    </Suspense>
  );
}
