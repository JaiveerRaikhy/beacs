# Supabase Database Schema

## `profiles`
Linked to `auth.users.id`. Core user table for both mentors and mentees.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key, linked to auth.users.id |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| full_name | text | |
| location | text | |
| university | text | |
| current_position | text | |
| current_company | text | |
| current_industry | text | |
| is_mentor | bool | |
| is_mentee | bool | |
| onboarding_complete | bool | |

---

## `mentor_details`
Extended profile data for mentors.

| Column | Type | Notes |
|---|---|---|
| profile_id | uuid | Primary key, FK → profiles.id |
| help_tags | _text | Array of topics mentor can help with |
| help_details | text | |
| pref_location | int4 | Preference weight |
| pref_uni | int4 | Preference weight |
| pref_gpa | int4 | Preference weight |
| pref_industry | int4 | Preference weight |
| pref_help_type | int4 | Preference weight |
| pref_path_alignment | int4 | Preference weight |

---

## `mentee_details`
Extended profile data for mentees.

| Column | Type | Notes |
|---|---|---|
| profile_id | uuid | Primary key, FK → profiles.id |
| gpa | numeric | |
| goals | text | |
| more_info | text | |
| help_tags | _text | Array of topics mentee needs help with |

---

## `past_positions`
Work and education history for a profile.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| profile_id | uuid | FK → profiles.id |
| title | text | |
| company | text | |
| duration | text | |
| is_education | bool | true if this is an education entry |
| sort_order | int4 | For ordering entries |

---

## `matches`
Stores bilateral match results between a mentor and mentee.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| mentor_id | uuid | FK → profiles.id |
| mentee_id | uuid | FK → profiles.id |
| status | match_status | Enum (e.g. pending, accepted, declined) |
| bilateral_score | numeric | Combined match score |
| mentor_score | numeric | How well mentee fits mentor's preferences |
| mentee_score | numeric | How well mentor fits mentee's needs |
| goal_alignment | numeric | |
| mentor_decided_at | timestamptz | |
| mentee_decided_at | timestamptz | |
| expires_at | timestamptz | |

---

## `conversations`
One conversation thread per match.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| created_at | timestamptz | |
| match_id | uuid | FK → matches.id |
| mentor_id | uuid | FK → profiles.id |
| mentee_id | uuid | FK → profiles.id |

---

## `messages`
Individual messages within a conversation.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key |
| created_at | timestamptz | |
| conversation_id | uuid | FK → conversations.id |
| sender_id | uuid | FK → profiles.id |
| body | text | |
| read_at | timestamptz | Null if unread |
