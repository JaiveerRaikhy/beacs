export const HELP_TAGS = [
  "Career Growth",
  "Resume Review",
  "Interview Prep",
  "Salary Negotiation",
  "Leadership",
  "Industry Transition",
  "Networking",
  "Skill Development",
  "Work-Life Balance",
  "Promotion Strategy",
] as const;

export type HelpTag = (typeof HELP_TAGS)[number];
