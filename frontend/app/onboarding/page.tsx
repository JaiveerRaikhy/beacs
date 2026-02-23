"use client";

import { createClient } from "@/lib/supabase/client";
import { HELP_TAGS } from "@/lib/constants";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type Step = "role" | "profile" | "work" | "mentor" | "mentee" | "done";

interface PastPosition {
  title: string;
  company: string;
  duration: string;
  is_education: boolean;
}

const PREF_LABELS: Record<string, string> = {
  location: "Location",
  uni: "University",
  gpa: "GPA",
  industry_alignment: "Industry",
  help_type: "Help type",
  path_alignment: "Path alignment",
};

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("role");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);

  const [isMentor, setIsMentor] = useState(false);
  const [isMentee, setIsMentee] = useState(false);

  const [fullName, setFullName] = useState("");
  const [location, setLocation] = useState("");
  const [university, setUniversity] = useState("");
  const [currentPosition, setCurrentPosition] = useState("");
  const [currentCompany, setCurrentCompany] = useState("");
  const [currentIndustry, setCurrentIndustry] = useState("");

  const [pastPositions, setPastPositions] = useState<PastPosition[]>([
    { title: "", company: "", duration: "", is_education: false },
  ]);

  const [helpTags, setHelpTags] = useState<string[]>([]);
  const [helpDetails, setHelpDetails] = useState("");
  const [prefs, setPrefs] = useState<Record<string, number>>({
    location: 0,
    uni: 0,
    gpa: 0,
    industry_alignment: 0,
    help_type: 0,
    path_alignment: 0,
  });

  const [gpa, setGpa] = useState("");
  const [goals, setGoals] = useState("");
  const [moreInfo, setMoreInfo] = useState("");
  const [menteeHelpTags, setMenteeHelpTags] = useState<string[]>([]);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => setUserId(user?.id ?? null));
  }, []);

  const runStep = useCallback(
    async (action: () => Promise<void>) => {
      setError(null);
      setLoading(true);
      try {
        await action();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  async function saveRole() {
    if (!userId) return;
    const supabase = createClient();
    const { error: e } = await supabase
      .from("profiles")
      .update({ is_mentor: isMentor, is_mentee: isMentee, updated_at: new Date().toISOString() })
      .eq("id", userId);
    if (e) throw new Error(e.message);
    setStep("profile");
  }

  async function saveProfile() {
    if (!userId) return;
    const supabase = createClient();
    const { error: e } = await supabase
      .from("profiles")
      .update({
        full_name: fullName,
        location,
        university,
        current_position: currentPosition,
        current_company: currentCompany,
        current_industry: currentIndustry,
        updated_at: new Date().toISOString(),
      })
      .eq("id", userId);
    if (e) throw new Error(e.message);
    setStep("work");
  }

  async function saveWork() {
    if (!userId) return;
    const supabase = createClient();
    const { error: del } = await supabase.from("past_positions").delete().eq("profile_id", userId);
    if (del) throw new Error(del.message);
    const toInsert = pastPositions
      .filter((p) => p.title.trim() || p.company.trim())
      .map((p, i) => ({
        profile_id: userId,
        title: p.title.trim() || "",
        company: p.company.trim() || "",
        duration: p.duration.trim() || "",
        is_education: p.is_education,
        sort_order: i,
      }));
    if (toInsert.length) {
      const { error: ins } = await supabase.from("past_positions").insert(toInsert);
      if (ins) throw new Error(ins.message);
    }
    if (isMentor) setStep("mentor");
    else if (isMentee) setStep("mentee");
    else setStep("done");
  }

  async function saveMentor() {
    if (!userId) return;
    const supabase = createClient();
    const row = {
      profile_id: userId,
      help_tags: helpTags,
      help_details: helpDetails,
      pref_location: prefs.location,
      pref_uni: prefs.uni,
      pref_gpa: prefs.gpa,
      pref_industry: prefs.industry_alignment,
      pref_help_type: prefs.help_type,
      pref_path_alignment: prefs.path_alignment,
    };
    const { error: e } = await supabase.from("mentor_details").upsert(row, { onConflict: "profile_id" });
    if (e) throw new Error(e.message);
    if (isMentee) setStep("mentee");
    else setStep("done");
  }

  async function saveMentee() {
    if (!userId) return;
    const supabase = createClient();
    const gpaNum = gpa.trim() ? parseFloat(gpa) : null;
    const row = {
      profile_id: userId,
      gpa: gpaNum,
      goals: goals.trim(),
      more_info: moreInfo.trim(),
      help_tags: menteeHelpTags,
    };
    const { error: e } = await supabase.from("mentee_details").upsert(row, { onConflict: "profile_id" });
    if (e) throw new Error(e.message);
    setStep("done");
  }

  async function finishOnboarding() {
    if (!userId) return;
    const supabase = createClient();
    const { error: e } = await supabase
      .from("profiles")
      .update({ onboarding_complete: true, updated_at: new Date().toISOString() })
      .eq("id", userId);
    if (e) throw new Error(e.message);
    router.push("/dashboard");
    router.refresh();
  }

  const toggleHelpTag = (tag: string, isMenteeTags: boolean) => {
    if (isMenteeTags) {
      setMenteeHelpTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
    } else {
      setHelpTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
    }
  };

  const addPosition = () => setPastPositions((p) => [...p, { title: "", company: "", duration: "", is_education: false }]);
  const updatePosition = (i: number, field: keyof PastPosition, value: string | boolean) => {
    setPastPositions((p) => p.map((pos, j) => (j === i ? { ...pos, [field]: value } : pos)));
  };
  const removePosition = (i: number) => {
    setPastPositions((p) => (p.length > 1 ? p.filter((_, j) => j !== i) : p));
  };

  return (
    <main className="min-h-screen p-6 md:p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Set up your profile</h1>

      {step === "role" && (
        <div className="space-y-4">
          <p className="text-gray-600">I want to join as:</p>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={isMentor} onChange={(e) => setIsMentor(e.target.checked)} className="rounded" />
            <span>Mentor</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={isMentee} onChange={(e) => setIsMentee(e.target.checked)} className="rounded" />
            <span>Mentee</span>
          </label>
          {!isMentor && !isMentee && <p className="text-sm text-amber-600">Select at least one.</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="button"
            disabled={loading || (!isMentor && !isMentee)}
            onClick={() => runStep(saveRole)}
            className="px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50"
          >
            {loading ? "Saving…" : "Continue"}
          </button>
        </div>
      )}

      {step === "profile" && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location (City, State)</label>
            <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. San Francisco, CA" className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">University</label>
            <input value={university} onChange={(e) => setUniversity(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current position</label>
            <input value={currentPosition} onChange={(e) => setCurrentPosition(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current company</label>
            <input value={currentCompany} onChange={(e) => setCurrentCompany(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current industry</label>
            <input value={currentIndustry} onChange={(e) => setCurrentIndustry(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="button" disabled={loading} onClick={() => runStep(saveProfile)} className="px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50">
            {loading ? "Saving…" : "Continue"}
          </button>
        </div>
      )}

      {step === "work" && (
        <div className="space-y-4">
          <p className="text-gray-600">Add work and education history. Use the checkbox for education entries.</p>
          {pastPositions.map((pos, i) => (
            <div key={i} className="border border-gray-200 rounded p-4 space-y-2">
              <input placeholder="Title" value={pos.title} onChange={(e) => updatePosition(i, "title", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
              <input placeholder="Company / School" value={pos.company} onChange={(e) => updatePosition(i, "company", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
              <input placeholder="Duration (e.g. 2 years)" value={pos.duration} onChange={(e) => updatePosition(i, "duration", e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={pos.is_education} onChange={(e) => updatePosition(i, "is_education", e.target.checked)} className="rounded" />
                <span className="text-sm">Education</span>
              </label>
              <button type="button" onClick={() => removePosition(i)} className="text-sm text-gray-500 underline">Remove</button>
            </div>
          ))}
          <button type="button" onClick={addPosition} className="text-sm text-gray-700 underline">+ Add position</button>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="button" disabled={loading} onClick={() => runStep(saveWork)} className="block mt-4 px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50">
            {loading ? "Saving…" : "Continue"}
          </button>
        </div>
      )}

      {step === "mentor" && (
        <div className="space-y-4">
          <p className="text-gray-600">What can you help with? (multi-select)</p>
          <div className="flex flex-wrap gap-2">
            {HELP_TAGS.map((tag) => (
              <label key={tag} className="inline-flex items-center gap-1 border border-gray-300 rounded px-2 py-1 text-sm">
                <input type="checkbox" checked={helpTags.includes(tag)} onChange={() => toggleHelpTag(tag, false)} className="rounded" />
                {tag}
              </label>
            ))}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Help details (optional)</label>
            <textarea value={helpDetails} onChange={(e) => setHelpDetails(e.target.value)} rows={3} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <p className="text-gray-600 text-sm">Preference importance (0 = Don&apos;t care, 1 = most, 5 = least)</p>
          {Object.entries(prefs).map(([key, val]) => (
            <div key={key}>
              <label className="block text-sm text-gray-700">{PREF_LABELS[key] ?? key}</label>
              <input type="range" min={0} max={5} value={val} onChange={(e) => setPrefs((p) => ({ ...p, [key]: Number(e.target.value) }))} className="w-full" />
              <span className="text-sm text-gray-500">{val === 0 ? "Don't care" : val}</span>
            </div>
          ))}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="button" disabled={loading} onClick={() => runStep(saveMentor)} className="px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50">
            {loading ? "Saving…" : "Continue"}
          </button>
        </div>
      )}

      {step === "mentee" && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">GPA (optional)</label>
            <input type="number" step="0.1" min={0} max={4} value={gpa} onChange={(e) => setGpa(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" placeholder="e.g. 3.5" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Goals</label>
            <textarea value={goals} onChange={(e) => setGoals(e.target.value)} rows={3} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">More info (optional)</label>
            <textarea value={moreInfo} onChange={(e) => setMoreInfo(e.target.value)} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded" />
          </div>
          <p className="text-gray-600">What do you need help with?</p>
          <div className="flex flex-wrap gap-2">
            {HELP_TAGS.map((tag) => (
              <label key={tag} className="inline-flex items-center gap-1 border border-gray-300 rounded px-2 py-1 text-sm">
                <input type="checkbox" checked={menteeHelpTags.includes(tag)} onChange={() => toggleHelpTag(tag, true)} className="rounded" />
                {tag}
              </label>
            ))}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="button" disabled={loading} onClick={() => runStep(saveMentee)} className="px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50">
            {loading ? "Saving…" : "Continue"}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="space-y-4">
          <p className="text-gray-600">You&apos;re all set. Complete onboarding to go to your dashboard.</p>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="button" disabled={loading} onClick={() => runStep(finishOnboarding)} className="px-4 py-2 bg-gray-900 text-white rounded disabled:opacity-50">
            {loading ? "Finishing…" : "Go to dashboard"}
          </button>
        </div>
      )}
    </main>
  );
}
