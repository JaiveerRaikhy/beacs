"use client";

import { HELP_TAGS } from "@/lib/constants";
import { createClient } from "@/lib/supabase/client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

type PastPosition = { id?: string; title: string; company: string; duration: string; is_education: boolean };

export default function ProfilePage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [location, setLocation] = useState("");
  const [university, setUniversity] = useState("");
  const [currentPosition, setCurrentPosition] = useState("");
  const [currentCompany, setCurrentCompany] = useState("");
  const [currentIndustry, setCurrentIndustry] = useState("");

  const [pastPositions, setPastPositions] = useState<PastPosition[]>([]);
  const [isMentor, setIsMentor] = useState(false);
  const [isMentee, setIsMentee] = useState(false);

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

  const load = useCallback(async () => {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      router.push("/login");
      return;
    }
    setUserId(user.id);

    const { data: profile } = await supabase.from("profiles").select("*").eq("id", user.id).single();
    if (profile) {
      setFullName(profile.full_name ?? "");
      setLocation(profile.location ?? "");
      setUniversity(profile.university ?? "");
      setCurrentPosition(profile.current_position ?? "");
      setCurrentCompany(profile.current_company ?? "");
      setCurrentIndustry(profile.current_industry ?? "");
      setIsMentor(!!profile.is_mentor);
      setIsMentee(!!profile.is_mentee);
    }

    const { data: positions } = await supabase.from("past_positions").select("id, title, company, duration, is_education").eq("profile_id", user.id).order("sort_order");
    setPastPositions((positions || []).map((p) => ({ id: p.id, title: p.title ?? "", company: p.company ?? "", duration: p.duration ?? "", is_education: !!p.is_education })));
    if (!positions?.length) setPastPositions([{ title: "", company: "", duration: "", is_education: false }]);

    const { data: mentorD } = await supabase.from("mentor_details").select("*").eq("profile_id", user.id).single();
    if (mentorD) {
      setHelpTags(mentorD.help_tags ?? []);
      setHelpDetails(mentorD.help_details ?? "");
      setPrefs({
        location: mentorD.pref_location ?? 0,
        uni: mentorD.pref_uni ?? 0,
        gpa: mentorD.pref_gpa ?? 0,
        industry_alignment: mentorD.pref_industry ?? 0,
        help_type: mentorD.pref_help_type ?? 0,
        path_alignment: mentorD.pref_path_alignment ?? 0,
      });
    }

    const { data: menteeD } = await supabase.from("mentee_details").select("*").eq("profile_id", user.id).single();
    if (menteeD) {
      setGpa(menteeD.gpa != null ? String(menteeD.gpa) : "");
      setGoals(menteeD.goals ?? "");
      setMoreInfo(menteeD.more_info ?? "");
      setMenteeHelpTags(menteeD.help_tags ?? []);
    }

    setLoading(false);
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function saveProfile() {
    if (!userId) return;
    setError(null);
    setSaving(true);
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
    if (e) setError(e.message);
    setSaving(false);
  }

  async function savePastPositions() {
    if (!userId) return;
    setError(null);
    setSaving(true);
    const supabase = createClient();
    await supabase.from("past_positions").delete().eq("profile_id", userId);
    const toInsert = pastPositions
      .filter((p) => p.title.trim() || p.company.trim())
      .map((p, i) => ({
        profile_id: userId,
        title: p.title.trim(),
        company: p.company.trim(),
        duration: p.duration.trim(),
        is_education: p.is_education,
        sort_order: i,
      }));
    if (toInsert.length) {
      const { error: e } = await supabase.from("past_positions").insert(toInsert);
      if (e) setError(e.message);
    }
    setSaving(false);
  }

  async function saveMentorDetails() {
    if (!userId) return;
    setError(null);
    setSaving(true);
    const supabase = createClient();
    const { error: e } = await supabase.from("mentor_details").upsert(
      {
        profile_id: userId,
        help_tags: helpTags,
        help_details: helpDetails,
        pref_location: prefs.location,
        pref_uni: prefs.uni,
        pref_gpa: prefs.gpa,
        pref_industry: prefs.industry_alignment,
        pref_help_type: prefs.help_type,
        pref_path_alignment: prefs.path_alignment,
      },
      { onConflict: "profile_id" }
    );
    if (e) setError(e.message);
    setSaving(false);
  }

  async function saveMenteeDetails() {
    if (!userId) return;
    setError(null);
    setSaving(true);
    const supabase = createClient();
    const gpaNum = gpa.trim() ? parseFloat(gpa) : null;
    const { error: e } = await supabase.from("mentee_details").upsert(
      {
        profile_id: userId,
        gpa: gpaNum,
        goals: goals.trim(),
        more_info: moreInfo.trim(),
        help_tags: menteeHelpTags,
      },
      { onConflict: "profile_id" }
    );
    if (e) setError(e.message);
    setSaving(false);
  }

  const toggleHelpTag = (tag: string, isMenteeTags: boolean) => {
    if (isMenteeTags) setMenteeHelpTags((p) => (p.includes(tag) ? p.filter((t) => t !== tag) : [...p, tag]));
    else setHelpTags((p) => (p.includes(tag) ? p.filter((t) => t !== tag) : [...p, tag]));
  };

  const addPosition = () => setPastPositions((p) => [...p, { title: "", company: "", duration: "", is_education: false }]);
  const updatePosition = (i: number, field: keyof PastPosition, value: string | boolean) => {
    setPastPositions((p) => p.map((pos, j) => (j === i ? { ...pos, [field]: value } : pos)));
  };
  const removePosition = (i: number) => setPastPositions((p) => (p.length > 1 ? p.filter((_, j) => j !== i) : p));

  if (loading) {
    return (
      <main className="min-h-screen p-6 flex items-center justify-center">
        <p className="text-gray-500">Loading…</p>
      </main>
    );
  }

  const prefLabels: Record<string, string> = {
    location: "Location",
    uni: "University",
    gpa: "GPA",
    industry_alignment: "Industry",
    help_type: "Help type",
    path_alignment: "Path alignment",
  };

  return (
    <main className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/dashboard" className="text-sm text-gray-600 hover:underline">
          Dashboard
        </Link>
        <h1 className="text-xl font-semibold text-gray-900">Profile</h1>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      <section className="border border-gray-200 rounded-lg p-4 mb-4 bg-white">
        <h2 className="font-medium text-gray-900 mb-3">Basic info</h2>
        <div className="space-y-2">
          <input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          <input placeholder="Location (City, State)" value={location} onChange={(e) => setLocation(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          <input placeholder="University" value={university} onChange={(e) => setUniversity(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          <input placeholder="Current position" value={currentPosition} onChange={(e) => setCurrentPosition(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          <input placeholder="Current company" value={currentCompany} onChange={(e) => setCurrentCompany(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
          <input placeholder="Current industry" value={currentIndustry} onChange={(e) => setCurrentIndustry(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded" />
        </div>
        <button type="button" onClick={saveProfile} disabled={saving} className="mt-3 px-4 py-2 bg-gray-900 text-white rounded text-sm disabled:opacity-50">
          Save profile
        </button>
      </section>

      <section className="border border-gray-200 rounded-lg p-4 mb-4 bg-white">
        <h2 className="font-medium text-gray-900 mb-3">Work & education</h2>
        {pastPositions.map((pos, i) => (
          <div key={i} className="flex flex-wrap gap-2 mb-2">
            <input placeholder="Title" value={pos.title} onChange={(e) => updatePosition(i, "title", e.target.value)} className="flex-1 min-w-[120px] px-3 py-2 border border-gray-300 rounded text-sm" />
            <input placeholder="Company / School" value={pos.company} onChange={(e) => updatePosition(i, "company", e.target.value)} className="flex-1 min-w-[120px] px-3 py-2 border border-gray-300 rounded text-sm" />
            <input placeholder="Duration" value={pos.duration} onChange={(e) => updatePosition(i, "duration", e.target.value)} className="w-24 px-3 py-2 border border-gray-300 rounded text-sm" />
            <label className="flex items-center gap-1 text-sm">
              <input type="checkbox" checked={pos.is_education} onChange={(e) => updatePosition(i, "is_education", e.target.checked)} className="rounded" />
              Education
            </label>
            <button type="button" onClick={() => removePosition(i)} className="text-sm text-gray-500 underline">Remove</button>
          </div>
        ))}
        <button type="button" onClick={addPosition} className="text-sm text-gray-600 underline">+ Add</button>
        <button type="button" onClick={savePastPositions} disabled={saving} className="block mt-2 px-4 py-2 bg-gray-900 text-white rounded text-sm disabled:opacity-50">
          Save work history
        </button>
      </section>

      {isMentor && (
        <section className="border border-gray-200 rounded-lg p-4 mb-4 bg-white">
          <h2 className="font-medium text-gray-900 mb-3">Mentor details</h2>
          <p className="text-sm text-gray-600 mb-2">Help tags</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {HELP_TAGS.map((tag) => (
              <label key={tag} className="inline-flex items-center gap-1 border border-gray-300 rounded px-2 py-1 text-sm">
                <input type="checkbox" checked={helpTags.includes(tag)} onChange={() => toggleHelpTag(tag, false)} className="rounded" />
                {tag}
              </label>
            ))}
          </div>
          <textarea placeholder="Help details" value={helpDetails} onChange={(e) => setHelpDetails(e.target.value)} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded text-sm mb-3" />
          <p className="text-sm text-gray-600 mb-2">Preference weights (0 = Don&apos;t care)</p>
          <div className="space-y-1 mb-3">
            {Object.entries(prefs).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="w-32 text-sm text-gray-700">{prefLabels[key]}</span>
                <input type="range" min={0} max={5} value={val} onChange={(e) => setPrefs((p) => ({ ...p, [key]: Number(e.target.value) }))} className="flex-1" />
                <span className="text-xs text-gray-500">{val}</span>
              </div>
            ))}
          </div>
          <button type="button" onClick={saveMentorDetails} disabled={saving} className="px-4 py-2 bg-gray-900 text-white rounded text-sm disabled:opacity-50">
            Save mentor details
          </button>
        </section>
      )}

      {isMentee && (
        <section className="border border-gray-200 rounded-lg p-4 mb-4 bg-white">
          <h2 className="font-medium text-gray-900 mb-3">Mentee details</h2>
          <input type="number" step="0.1" placeholder="GPA (optional)" value={gpa} onChange={(e) => setGpa(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded text-sm mb-2" />
          <textarea placeholder="Goals" value={goals} onChange={(e) => setGoals(e.target.value)} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded text-sm mb-2" />
          <textarea placeholder="More info" value={moreInfo} onChange={(e) => setMoreInfo(e.target.value)} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded text-sm mb-2" />
          <p className="text-sm text-gray-600 mb-2">Help needed</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {HELP_TAGS.map((tag) => (
              <label key={tag} className="inline-flex items-center gap-1 border border-gray-300 rounded px-2 py-1 text-sm">
                <input type="checkbox" checked={menteeHelpTags.includes(tag)} onChange={() => toggleHelpTag(tag, true)} className="rounded" />
                {tag}
              </label>
            ))}
          </div>
          <button type="button" onClick={saveMenteeDetails} disabled={saving} className="px-4 py-2 bg-gray-900 text-white rounded text-sm disabled:opacity-50">
            Save mentee details
          </button>
        </section>
      )}
    </main>
  );
}
