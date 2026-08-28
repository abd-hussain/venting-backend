# Venting — Database Schema Design

> Designed for the Venting mobile app and [`api-endpoints.md`](./api-endpoints.md).  
> Goal: enough tables for clean domain boundaries, not so many that queries become slow or hard to maintain.

| Item | Value |
|------|--------|
| Recommended DB | PostgreSQL 15+ |
| Money | `NUMERIC(12,2)` (USD) |
| IDs | `UUID` primary keys |
| Timestamps | `TIMESTAMPTZ` UTC |
| Soft delete | `deleted_at` on users (cascade hide related rows in queries) |
| **Total tables** | **43** |

---

## How to read this doc

| Column | Meaning |
|--------|---------|
| **PK** | Primary key |
| **FK** | Foreign key → other table |
| **UQ** | Unique |
| **IDX** | Recommended index |
| **?** | Nullable |

---

## Quick index (all 44 tables)

| # | Table | Domain |
|--:|-------|--------|
| 1 | `users` | Auth |
| 2 | `refresh_tokens` | Auth |
| 2b | `auth_identities` | Auth — social *(proposed)* |
| 2c | `password_reset_tokens` | Auth — forgot-password one-time links |
| 3 | `ventor_profiles` | Ventor |
| 4 | `listener_profiles` | Listener |
| 5 | `listener_identity_verifications` | Listener onboarding |
| 6 | `languages` | Lookups — **one** speaking-language catalog (ventor + listener) |
| 7 | `comfort_areas` | Lookups — interests/comfort (`icon_emoji` + optional `icon_url`) |
| 8 | `life_experiences` | Lookups |
| 9 | `boundaries` | Lookups |
| 10 | `ventor_languages` | Ventor tags → `languages` |
| 10b | `ventor_interests` | Ventor tags → `comfort_areas` |
| 11 | `listener_languages` | Listener tags |
| 12 | `listener_comfort_areas` | Listener tags |
| 13 | `listener_life_experiences` | Listener tags |
| 14 | `listener_boundaries` | Listener tags |
| 15 | `listener_availability_settings` | Availability |
| 16 | `listener_availability_slots` | Availability |
| 17 | `ventor_favorites` | Ventor |
| 18 | `mood_checkins` | Wellness |
| 19 | `achievements` | Catalog |
| 20 | `ventor_achievements` | Ventor |
| 21 | `ventor_privacy_settings` | Settings |
| 22 | `listener_privacy_settings` | Settings |
| 23 | `ventor_notification_preferences` | Settings |
| 24 | `listener_notification_preferences` | Settings |
| 25 | `session_requests` | Sessions |
| 26 | `sessions` | Sessions |
| 27 | `session_payments` | Money |
| 28 | `session_ratings` | Feedback |
| 29 | `session_listener_feedback` | Feedback |
| 30 | `session_reports` | Safety |
| 31 | `listener_wallets` | Earnings |
| 32 | `wallet_ledger_entries` | Earnings |
| 33 | `payout_methods` | Payouts |
| 34 | `payouts` | Payouts |
| 35 | `reward_offers` | Rewards |
| 36 | `reward_trades` | Rewards |
| 37 | `invite_codes` | Invites |
| 38 | `invite_events` | Invites |
| 39 | `notifications` | Notifications |
| 40 | `training_modules` | Training |
| 41 | `listener_training_progress` | Training |
| 42 | `promo_codes` | Promo |
| 43 | `promo_redemptions` | Promo |

| Band | Count |
|------|------:|
| Auth | 2 |
| Profiles + identity | 3 |
| Lookups + tag links | 10 |
| Availability | 2 |
| Ventor social / wellness | 4 |
| Settings | 4 |
| Sessions + payments + feedback | 6 |
| Wallet / payouts | 4 |
| Rewards / invites | 4 |
| Notifications | 1 |
| Training | 2 |
| Promo | 2 |
| **Total** | **43** |

---

## Entity relationship (high level)

```mermaid
erDiagram
  users ||--o| ventor_profiles : "role=ventor"
  users ||--o| listener_profiles : "role=listener"
  users ||--o{ refresh_tokens : has
  users ||--o{ notifications : receives

  ventor_profiles ||--o{ mood_checkins : logs
  ventor_profiles ||--o{ ventor_favorites : saves
  ventor_profiles ||--o{ ventor_languages : speaks
  ventor_profiles ||--o{ ventor_interests : picks
  ventor_profiles ||--o| ventor_privacy_settings : has
  languages ||--o{ ventor_languages : tagged
  languages ||--o{ listener_languages : tagged
  comfort_areas ||--o{ ventor_interests : tagged
  comfort_areas ||--o{ listener_comfort_areas : tagged
  ventor_profiles ||--o| ventor_notification_preferences : has
  ventor_profiles ||--o{ ventor_achievements : unlocks
  ventor_profiles ||--o| invite_codes : owns
  ventor_profiles ||--o{ reward_trades : redeems

  listener_profiles ||--o| listener_availability_settings : has
  listener_availability_settings ||--o{ listener_availability_slots : defines
  listener_profiles ||--o| listener_privacy_settings : has
  listener_profiles ||--o| listener_notification_preferences : has
  listener_profiles ||--o| listener_wallets : has
  listener_profiles ||--o{ listener_training_progress : tracks
  listener_profiles ||--o{ listener_identity_verifications : submits

  session_requests }o--|| ventor_profiles : from
  session_requests }o--|| listener_profiles : to
  sessions }o--|| ventor_profiles : ventor
  sessions }o--|| listener_profiles : listener
  sessions ||--o| session_payments : billed
  sessions ||--o| session_ratings : ventor_rates
  sessions ||--o| session_listener_feedback : listener_rates
  sessions ||--o{ session_reports : reported
  listener_wallets ||--o{ wallet_ledger_entries : ledger
  listener_wallets ||--o{ payouts : withdraws
  payout_methods }o--|| listener_profiles : belongs
```

---

## Shared enums (use DB enums or check constraints)

| Enum | Values |
|------|--------|
| `user_role` | `ventor`, `listener` |
| `gender` | `male`, `female`, `prefer_not_to_say` |
| `profile_status` | `incomplete`, `under_review`, `approved`, `rejected` |
| `setup_step_status` | `done`, `in_progress`, `locked` |
| `day_of_week` | `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` |
| `session_time_mode` | `instant`, `nearest`, `scheduled` |
| `call_mode` | `voice`, `video` |
| `session_request_status` | `pending`, `accepted`, `declined`, `expired`, `cancelled` |
| `session_status` | `upcoming`, `live`, `completed`, `cancelled`, `missed` |
| `payment_status` | `pending`, `paid`, `refunded`, `failed` |
| `report_reason` | `inappropriate_behavior`, `harassment`, `hate_speech`, `safety_concern`, `not_listening`, `technical_issue`, `other` |
| `reported_role` | `ventor`, `listener` |
| `ledger_entry_type` | `session_earning`, `tip`, `penalty`, `payout`, `payout_reversal`, `adjustment` |
| `payout_status` | `pending`, `completed`, `failed` |
| `payout_method_type` | `bank`, `paypal` |
| `reward_offer_kind` | `percent_off`, `free_minutes`, `priority_match` |
| `earnings_tier` | `starter`, `rising`, `trusted`, `expert`, `elite` |
| `invite_status` | `pending`, `joined`, `first_session`, `booked_call` |
| `notification_type` | `welcome`, `complete_registration`, `book_first_session`, `session_request`, `session_reminder`, `review`, `payout`, `system`, `rewards` |
| `training_status` | `not_started`, `in_progress`, `completed` |
| `mood_kind` | `great`, `okay`, `anxious`, `sad`, `angry` |

---

## 1. Auth

### 1. `users`

Core login identity. One row per account.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `email` | VARCHAR(255) | **UQ**, lowercased |
| `password_hash` | VARCHAR(255) | Nullable for social-only accounts — see [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md) |
| `role` | `user_role` | ventor \| listener |
| `is_active` | BOOLEAN | default true |
| `registration_complete` | BOOLEAN | default false |
| `registration_completed_steps` | JSONB | Array of saved step slugs, e.g. `["profile","identity"]` — ventor + listener onboarding |
| `registration_next_step` | VARCHAR(64) | Next wizard step slug for resume (`profile`, `languages`, …) |
| `last_login_at` | TIMESTAMPTZ | ? |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `deleted_at` | TIMESTAMPTZ | ? soft delete |

**Indexes:** `UQ(email)`, `IDX(role)`, `IDX(deleted_at)`

---

### 2. `refresh_tokens`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `user_id` | UUID | **FK → users** |
| `token_hash` | VARCHAR(255) | **UQ** |
| `device_info` | VARCHAR(255) | ? |
| `expires_at` | TIMESTAMPTZ | |
| `revoked_at` | TIMESTAMPTZ | ? |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `IDX(user_id)`, `UQ(token_hash)`

---

### 2b. `auth_identities` *(proposed — social auth)*

> Full requirements: [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md)

Links a Venting user to a Google or Apple identity (`sub`).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `user_id` | UUID | **FK → users** |
| `provider` | VARCHAR(16) | `google` \| `apple` |
| `provider_user_id` | VARCHAR(255) | Provider `sub` |
| `email` | VARCHAR(255) | ? last known email from provider |
| `raw_profile` | JSONB | ? non-secret claims |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `UQ(provider, provider_user_id)`, `UQ(user_id, provider)`

### 2c. `password_reset_tokens`

Used by `#2b forgot-password` / `#2c reset-password`. Store **hash only**, never the raw email token.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `user_id` | UUID | **FK → users** |
| `token_hash` | VARCHAR(128) | **UQ** — SHA-256 (or stronger) of raw token |
| `expires_at` | TIMESTAMPTZ | typically now + 60 minutes |
| `used_at` | TIMESTAMPTZ | ? set on successful reset |
| `requested_ip` | VARCHAR(64) | ? |
| `locale` | VARCHAR(8) | `en` \| `ar` — for email + link |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `UQ(token_hash)`, `IDX(user_id)`, `IDX(expires_at)`

### 2d. `user_push_tokens`

Optional FCM device tokens from ventor `#8e` / listener `#22j` registration complete (`fcm_token`). Registration succeeds without a token.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `user_id` | UUID | **FK → users** |
| `token` | VARCHAR(512) | **UQ** — raw FCM token |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `UQ(token)`, `IDX(user_id)`

---

## 2. Profiles

### 3. `ventor_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | UUID | **PK, FK → users** |
| `nickname` | VARCHAR(20) | |
| `gender` | `gender` | |
| `avatar_url` | TEXT | ? |
| `quote` | VARCHAR(280) | ? |
| `is_anonymous` | BOOLEAN | default true |
| `points_balance` | INT | default 0 |
| `active_reward_offer_id` | UUID | ? **FK → reward_offers** |
| `mood_streak_days` | INT | default 0 |
| `last_mood_checkin_date` | DATE | ? UTC date for streak |
| `completed_sessions_count` | INT | cached counter |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### 4. `listener_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | UUID | **PK, FK → users** |
| `full_name` | VARCHAR(120) | |
| `phone_e164` | VARCHAR(32) | ? |
| `phone_country_iso` | CHAR(2) | ? |
| `avatar_url` | TEXT | ? |
| `about_me` | TEXT | ? |
| `date_of_birth` | DATE | ? |
| `country` | VARCHAR(100) | ? |
| `country_iso` | CHAR(2) | ? **IDX** |
| `city` | VARCHAR(30) | ? |
| `gender` | `gender` | ? |
| `bio` | TEXT | ? public short bio |
| `voice_intro_url` | TEXT | ? |
| `voice_intro_seconds` | INT | ? |
| `is_online` | BOOLEAN | default false **IDX** |
| `is_verified` | BOOLEAN | default false |
| `profile_status` | `profile_status` | **IDX** |
| `accept_instant_calls` | BOOLEAN | default true |
| `session_length_minutes` | INT | default 30 |
| `break_length_minutes` | INT | default 15 |
| `time_zone_id` | VARCHAR(64) | e.g. `Asia/Beirut` |
| `rate_per_minute` | NUMERIC(8,2) | derived from tier; cache for discovery |
| `current_tier` | `earnings_tier` | default `starter` |
| `rating_avg` | NUMERIC(3,2) | cached |
| `rating_count` | INT | cached |
| `session_count` | INT | cached completed |
| `rating_breakdown` | JSONB | `{ "5": 86, "4": 10, ... }` |
| `setup_identity_status` | `setup_step_status` | |
| `setup_profile_status` | `setup_step_status` | |
| `setup_availability_status` | `setup_step_status` | |
| `setup_training_status` | `setup_step_status` | |
| `setup_tutorial_status` | `setup_step_status` | |
| `first_session_tutorial_acked_at` | TIMESTAMPTZ | ? |
| `agreed_to_terms_at` | TIMESTAMPTZ | ? |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `(is_online, profile_status)`, `(rate_per_minute)`, `(rating_avg)`, `(country_iso)`, GIN on `rating_breakdown` only if queried

---

### 5. `listener_identity_verifications`

Used for listener KYC documents. **First upload** is created from listener registration step `identity` (`PATCH /v1/listeners/register/steps/identity`). **Resubmit** after admin rejection uses `#23 identity-verification`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `listener_id` | UUID | **FK → listener_profiles** |
| `identity_document_url` | TEXT | Single government-ID photo (not front/back). Replaces deprecated `document_front_url` |
| `selfie_url` | TEXT | |
| `status` | `profile_status` | pending/approved/rejected via under_review |
| `reviewed_at` | TIMESTAMPTZ | ? |
| `reviewer_note` | TEXT | ? |
| `created_at` | TIMESTAMPTZ | |

> **Deprecated (do not use in new code):** `document_front_url`, `document_back_url` — mobile captures **one** ID image + selfie only.

**Indexes:** `IDX(listener_id, created_at DESC)`

---

## 3. Lookups & tag links

Stable catalogs (seed once). App uses string ids like `anxiety_stress`, `en`, `politics`.

### 6. `languages`

> **Single catalog** for all speaking-language UIs (ventor registration language step, listener registration languages, discovery filters, availability).  
> Do **not** create a separate “speaking_languages” table — use this one. Managed from the admin portal (`/catalogs` → Languages).

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(16) | **PK** e.g. `en`, `ar`, `hi` |
| `name_en` | VARCHAR(64) | English name (`English`) |
| `name_native` | VARCHAR(64) | Native script label (`العربية`, `हिन्दी`) |
| `name_ar` | VARCHAR(64) | Arabic label of the language name |
| `flag_url` | TEXT | **Required for active rows** — absolute HTTPS URL of flag image (CDN / object storage uploaded via portal) |
| `flag_emoji` | VARCHAR(16) | ? optional fallback only (e.g. `🇺🇸`); mobile prefers `flag_url` |
| `sort_order` | INT | default 0 |
| `is_active` | BOOLEAN | default true |

**Consumers of the same rows:**

| Consumer | Link |
|----------|------|
| Ventor registration `#75` | `GET /v1/catalog/languages` → `#8` `language_ids` → `ventor_languages` |
| Listener registration / profile | same catalog ids → `listener_languages` |
| Discovery `#40` filters | `languages` query csv of these ids |

### 7. `comfort_areas`

> Interest / comfort categories for ventor registration and listener comfort tags. Managed from the admin portal (`/catalogs` → Comfort areas / Interests).

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) | **PK** |
| `name_en` | VARCHAR(120) | |
| `name_ar` | VARCHAR(120) | |
| `icon_emoji` | VARCHAR(16) | Unicode emoji for the row icon (e.g. `❤️`, `💼`) — same idea as `languages.flag_emoji` |
| `icon_url` | TEXT | ? optional CDN image URL; mobile prefers `icon_url` when set, else `icon_emoji` |
| `sort_order` | INT | default 0 — ascending display order |
| `allows_custom_text` | BOOLEAN | default false — e.g. `other` shows free-text field |
| `audience` | VARCHAR(32) | `ventor` \| `listener` \| `all` — optional admin metadata; **mobile `#74` does not filter by this** — both ventor and listener see the same active list |
| `topic_group` | VARCHAR(64) | ? e.g. anxiety, relationships |
| `is_active` | BOOLEAN | |

### 8. `life_experiences`

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) | **PK** |
| `name_en` | VARCHAR(120) | |
| `name_ar` | VARCHAR(120) | |
| `sort_order` | INT | Ascending — portal-managed |
| `is_active` | BOOLEAN | |

Exposed publicly via `#76 GET /v1/catalog/life-experiences` (active rows only).

### 9. `boundaries`

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) | **PK** |
| `name_en` | VARCHAR(120) | |
| `name_ar` | VARCHAR(120) | |
| `icon_emoji` | VARCHAR(16) | Unicode emoji — same pattern as `comfort_areas.icon_emoji` |
| `icon_url` | TEXT | ? optional CDN image URL |
| `sort_order` | INT | Ascending — portal-managed |
| `allows_custom_text` | BOOLEAN | default false — e.g. optional “Other” |
| `is_active` | BOOLEAN | |

Exposed publicly via `#77 GET /v1/catalog/boundaries` (active rows only).

### 10. `ventor_languages`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **FK → ventor_profiles** |
| `language_id` | VARCHAR(16) | **FK → languages** |
| | | **PK (`ventor_id`, `language_id`)** |

Written from ventor registration step `languages` (`PATCH /v1/ventors/register/steps/languages`). Same `languages` catalog as listeners.

### 10b. `ventor_interests`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **FK → ventor_profiles** |
| `comfort_area_id` | VARCHAR(64) | **FK → comfort_areas** |
| `custom_text` | TEXT | ? free text when category `allows_custom_text` — from `#8` `other_interest_text` |
| | | **PK (`ventor_id`, `comfort_area_id`)** |

### 11. `listener_languages`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **FK** |
| `language_id` | VARCHAR(16) | **FK** |
| | | **PK (listener_id, language_id)** |

### 12. `listener_comfort_areas`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **FK** |
| `comfort_area_id` | VARCHAR(64) | **FK** |
| `custom_text` | TEXT | ? when category `allows_custom_text` — from `#22` `custom_comfort_area_text` |
| | | **PK (listener_id, comfort_area_id)** |

**Extra:** store custom free-text experiences on listener if needed:

### 13. `listener_life_experiences`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **FK** |
| `life_experience_id` | VARCHAR(64) | **FK** (or custom slug) |
| `custom_label` | VARCHAR(120) | ? when user typed custom |
| | | **PK (listener_id, life_experience_id)** |

### 14. `listener_boundaries`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **FK** |
| `boundary_id` | VARCHAR(64) | **FK** |
| `custom_text` | TEXT | ? when boundary `allows_custom_text` — from `#22` `custom_boundary_text` |
| | | **PK (listener_id, boundary_id)** |

---

## 4. Availability

### 15. `listener_availability_settings`

1:1 with listener (mirrors fields also cached on profile for discovery).

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **PK, FK** |
| `accept_instant_calls` | BOOLEAN | |
| `session_length_minutes` | INT | |
| `break_length_minutes` | INT | |
| `time_zone_id` | VARCHAR(64) | |
| `updated_at` | TIMESTAMPTZ | |

> Optional: drop this table and keep only columns on `listener_profiles` + slots table. Keeping it makes the availability API cleaner.

### 16. `listener_availability_slots`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `listener_id` | UUID | **FK** **IDX** |
| `day` | `day_of_week` | |
| `start_time` | TIME | local to `time_zone_id` |
| `end_time` | TIME | |
| `created_at` | TIMESTAMPTZ | |

**Indexes:** `IDX(listener_id, day)`, check `end_time > start_time`

---

## 5. Ventor social / wellness

### 17. `ventor_favorites`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **FK** |
| `listener_id` | UUID | **FK** |
| `created_at` | TIMESTAMPTZ | |
| | | **PK (ventor_id, listener_id)** |

### 18. `mood_checkins`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `ventor_id` | UUID | **FK** **IDX** |
| `mood` | `mood_kind` | |
| `note` | TEXT | ? |
| `checked_in_at` | TIMESTAMPTZ | |
| `checkin_date` | DATE | UTC date for streak **UQ(ventor_id, checkin_date)** |

### 19. `achievements`

Catalog.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) | **PK** |
| `title_key` | VARCHAR(128) | l10n key |
| `subtitle_key` | VARCHAR(128) | |
| `description_key` | VARCHAR(128) | |
| `sort_order` | INT | |
| `is_active` | BOOLEAN | |

### 20. `ventor_achievements`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **FK** |
| `achievement_id` | VARCHAR(64) | **FK** |
| `unlocked_at` | TIMESTAMPTZ | |
| | | **PK (ventor_id, achievement_id)** |

---

## 6. Settings

### 21. `ventor_privacy_settings`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **PK, FK** |
| `show_mood_journey` | BOOLEAN | default true |
| `show_achievements` | BOOLEAN | |
| `show_stats` | BOOLEAN | |
| `show_favorite_listeners` | BOOLEAN | |
| `allow_listener_discovery` | BOOLEAN | |
| `updated_at` | TIMESTAMPTZ | |

### 22. `listener_privacy_settings`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **PK, FK** |
| `profile_visible` | BOOLEAN | default true — when false, hide listener from in-app discovery |
| `show_online_status` | BOOLEAN | default true |
| `visible_in_all_countries` | BOOLEAN | default true |
| `visible_countries` | CHAR(2)[] | ISO list when not all |
| `allow_search_indexing` | BOOLEAN | default true |
| `updated_at` | TIMESTAMPTZ | |

**Removed columns** (v2): `show_languages`, `show_comfort_areas`, `show_experience_and_ratings`, `show_boundaries` — profile information is always visible when the listener profile is shown in the app.

**Migration:** `ALTER TABLE listener_privacy_settings ADD COLUMN profile_visible BOOLEAN NOT NULL DEFAULT true;` then drop the four `show_*` columns; `ALTER COLUMN allow_search_indexing SET DEFAULT true`.

### 23. `ventor_notification_preferences`

| Column | Type | Notes |
|--------|------|-------|
| `ventor_id` | UUID | **PK, FK** |
| `push_enabled` | BOOLEAN | |
| `session_reminder_30_min` | BOOLEAN | |
| `session_reminder_15_min` | BOOLEAN | |
| `session_reminder_10_min` | BOOLEAN | |
| `session_reminder_5_min` | BOOLEAN | |
| `rewards_updates` | BOOLEAN | |
| `promotions_updates` | BOOLEAN | |
| `email_enabled` | BOOLEAN | |
| `updated_at` | TIMESTAMPTZ | |

### 24. `listener_notification_preferences`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **PK, FK** |
| `push_enabled` | BOOLEAN | |
| `new_session_requests` | BOOLEAN | |
| `session_reminder_15_min` | BOOLEAN | |
| `session_reminder_10_min` | BOOLEAN | |
| `session_reminder_5_min` | BOOLEAN | |
| `reviews_feedback` | BOOLEAN | |
| `tips_earnings` | BOOLEAN | |
| `promotions_updates` | BOOLEAN | |
| `email_enabled` | BOOLEAN | |
| `updated_at` | TIMESTAMPTZ | |

---

## 7. Sessions, payments, feedback

### 25. `session_requests`

Created when ventor books / requests a listener (before accept for non-auto flows).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `ventor_id` | UUID | **FK** **IDX** |
| `listener_id` | UUID | **FK** **IDX** (null if broadcast instant?) |
| `status` | `session_request_status` | **IDX** |
| `message` | TEXT | ? ventor note |
| `chosen_reason` | VARCHAR(120) | ? |
| `tags` | TEXT[] | topic tags |
| `duration_minutes` | INT | |
| `time_mode` | `session_time_mode` | |
| `scheduled_at` | TIMESTAMPTZ | ? |
| `call_mode` | `call_mode` | |
| `speech_language` | VARCHAR(64) | |
| `voice_change_enabled` | BOOLEAN | default false |
| `is_instant` | BOOLEAN | |
| `promo_code_id` | UUID | ? **FK → promo_codes** |
| `reward_offer_id` | UUID | ? **FK → reward_offers** |
| `quoted_amount` | NUMERIC(12,2) | |
| `expires_at` | TIMESTAMPTZ | ? for instant race |
| `session_id` | UUID | ? set when accepted **FK → sessions** |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `(listener_id, status)`, `(ventor_id, status)`, `(is_instant, status, created_at)`

---

### 26. `sessions`

Canonical booked / live / history session.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `request_id` | UUID | ? **UQ FK → session_requests** |
| `ventor_id` | UUID | **FK** **IDX** |
| `listener_id` | UUID | **FK** **IDX** |
| `status` | `session_status` | **IDX** |
| `duration_minutes` | INT | booked length |
| `actual_duration_seconds` | INT | ? after end |
| `time_mode` | `session_time_mode` | |
| `scheduled_at` | TIMESTAMPTZ | ? **IDX** |
| `started_at` | TIMESTAMPTZ | ? |
| `ended_at` | TIMESTAMPTZ | ? |
| `call_mode` | `call_mode` | |
| `speech_language` | VARCHAR(64) | |
| `voice_change_enabled` | BOOLEAN | |
| `is_instant` | BOOLEAN | |
| `message` | TEXT | ? |
| `chosen_reason` | VARCHAR(120) | ? |
| `tags` | TEXT[] | |
| `listener_history_outcome` | VARCHAR(16) | ? `accepted` \| `declined` for history UI |
| `missed_by_listener` | BOOLEAN | default false |
| `call_channel_id` | VARCHAR(128) | ? VoIP |
| `cancelled_at` | TIMESTAMPTZ | ? |
| `cancel_reason` | TEXT | ? |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `(ventor_id, status, scheduled_at)`, `(listener_id, status, scheduled_at)`

---

### 27. `session_payments`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `session_id` | UUID | **UQ FK → sessions** |
| `currency` | CHAR(3) | default `USD` |
| `session_price` | NUMERIC(12,2) | |
| `voice_change_fee` | NUMERIC(12,2) | default 0 |
| `discount_amount` | NUMERIC(12,2) | default 0 |
| `tip_amount` | NUMERIC(12,2) | default 0 (after rating) |
| `amount_paid` | NUMERIC(12,2) | |
| `refunded_amount` | NUMERIC(12,2) | default 0 |
| `status` | `payment_status` | |
| `provider` | VARCHAR(32) | ? stripe, etc. |
| `provider_payment_id` | VARCHAR(128) | ? |
| `promo_code_id` | UUID | ? |
| `reward_offer_id` | UUID | ? |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### 28. `session_ratings`

Ventor rates listener (stars + review + optional tip).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `session_id` | UUID | **UQ FK** |
| `ventor_id` | UUID | **FK** |
| `listener_id` | UUID | **FK** **IDX** |
| `stars` | SMALLINT | 1–5 |
| `review` | TEXT | ? |
| `tip_amount` | NUMERIC(12,2) | ? |
| `created_at` | TIMESTAMPTZ | |

---

### 29. `session_listener_feedback`

Listener rates the session experience.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `session_id` | UUID | **UQ FK** |
| `listener_id` | UUID | **FK** |
| `ventor_id` | UUID | **FK** |
| `stars` | SMALLINT | 1–5 |
| `felt_heard` | BOOLEAN | |
| `talk_again` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

---

### 30. `session_reports`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `session_id` | UUID | **FK** **IDX** |
| `reporter_user_id` | UUID | **FK → users** |
| `reported_role` | `reported_role` | who is reported |
| `reason` | `report_reason` | |
| `details` | TEXT | ? |
| `status` | VARCHAR(32) | `open` \| `reviewed` \| `closed` |
| `created_at` | TIMESTAMPTZ | |

---

## 8. Wallet & payouts

### 31. `listener_wallets`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **PK, FK** |
| `available_balance` | NUMERIC(12,2) | default 0 |
| `pending_balance` | NUMERIC(12,2) | default 0 |
| `lifetime_earned` | NUMERIC(12,2) | default 0 |
| `updated_at` | TIMESTAMPTZ | |

### 32. `wallet_ledger_entries`

Append-only money movement (earnings chart + audit).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `listener_id` | UUID | **FK** **IDX** |
| `type` | `ledger_entry_type` | |
| `amount` | NUMERIC(12,2) | + credit / − debit |
| `balance_after` | NUMERIC(12,2) | |
| `session_id` | UUID | ? |
| `payout_id` | UUID | ? |
| `idempotency_key` | VARCHAR(64) | **UQ** |
| `note` | TEXT | ? |
| `created_at` | TIMESTAMPTZ | **IDX (listener_id, created_at)** |

### 33. `payout_methods`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `listener_id` | UUID | **FK** **IDX** |
| `type` | `payout_method_type` | |
| `is_default` | BOOLEAN | |
| `account_holder_name` | VARCHAR(120) | ? |
| `bank_name` | VARCHAR(120) | ? |
| `iban_or_account` | VARCHAR(64) | ? |
| `swift_code` | VARCHAR(32) | ? |
| `paypal_email` | VARCHAR(255) | ? |
| `label` | VARCHAR(120) | display |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `deleted_at` | TIMESTAMPTZ | ? |

### 34. `payouts`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `listener_id` | UUID | **FK** **IDX** |
| `payout_method_id` | UUID | **FK** |
| `amount` | NUMERIC(12,2) | |
| `status` | `payout_status` | |
| `method_label` | VARCHAR(120) | snapshot |
| `reference` | VARCHAR(64) | ? |
| `requested_at` | TIMESTAMPTZ | |
| `processed_at` | TIMESTAMPTZ | ? |
| `failure_reason` | TEXT | ? |

---

## 9. Rewards & invites

### 35. `reward_offers`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `code` | VARCHAR(64) | **UQ** e.g. `off_20_any` |
| `kind` | `reward_offer_kind` | |
| `points_cost` | INT | |
| `percent_off` | INT | ? |
| `free_minutes` | INT | ? |
| `min_tier` | `earnings_tier` | ? audience |
| `max_tier` | `earnings_tier` | ? |
| `is_welcome_gift` | BOOLEAN | default false |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

### 36. `reward_trades`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `ventor_id` | UUID | **FK** **IDX** |
| `offer_id` | UUID | **FK → reward_offers** |
| `points_spent` | INT | |
| `is_welcome_gift` | BOOLEAN | |
| `traded_at` | TIMESTAMPTZ | |

### 37. `invite_codes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `ventor_id` | UUID | **UQ FK** |
| `code` | VARCHAR(32) | **UQ** |
| `invite_link` | TEXT | |
| `created_at` | TIMESTAMPTZ | |
| `refreshed_at` | TIMESTAMPTZ | ? |

### 38. `invite_events`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `invite_code_id` | UUID | **FK** |
| `inviter_ventor_id` | UUID | **FK** |
| `invitee_user_id` | UUID | ? **FK → users** |
| `invitee_display_name` | VARCHAR(120) | |
| `status` | `invite_status` | |
| `points_earned` | INT | default 0 |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes:** `IDX(inviter_ventor_id, status)`

---

## 10. Notifications

### 39. `notifications`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `user_id` | UUID | **FK** **IDX** |
| `type` | `notification_type` | |
| `title` | VARCHAR(200) | |
| `body` | TEXT | |
| `data` | JSONB | ? deep-link payload |
| `is_read` | BOOLEAN | default false |
| `created_at` | TIMESTAMPTZ | |
| `deleted_at` | TIMESTAMPTZ | ? |

**Indexes:** `(user_id, is_read, created_at DESC)`, `(user_id, deleted_at)`

---

## 11. Training

### 40. `training_modules`

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) | **PK** e.g. `art_of_listening` |
| `title_key` | VARCHAR(128) | |
| `content_url` | TEXT | |
| `sort_order` | INT | |
| `is_active` | BOOLEAN | |

### 41. `listener_training_progress`

| Column | Type | Notes |
|--------|------|-------|
| `listener_id` | UUID | **FK** |
| `module_id` | VARCHAR(64) | **FK** |
| `status` | `training_status` | |
| `completed_at` | TIMESTAMPTZ | ? |
| | | **PK (listener_id, module_id)** |

---

## 12. Promo codes

### 42. `promo_codes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `code` | VARCHAR(32) | **UQ** uppercased |
| `percent_off` | INT | ? |
| `fixed_amount` | NUMERIC(12,2) | ? |
| `max_redemptions` | INT | ? |
| `redemption_count` | INT | default 0 |
| `valid_from` | TIMESTAMPTZ | ? |
| `valid_to` | TIMESTAMPTZ | ? |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

### 43. `promo_redemptions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | **PK** |
| `promo_code_id` | UUID | **FK** |
| `ventor_id` | UUID | **FK** |
| `session_id` | UUID | ? **FK** |
| `discount_amount` | NUMERIC(12,2) | |
| `created_at` | TIMESTAMPTZ | |
| | | **UQ (promo_code_id, ventor_id, session_id)** optional |


## Design choices (performance & efficiency)

1. **Cached counters on profiles** (`rating_avg`, `session_count`, `points_balance`, `rate_per_minute`) — discovery and home screens avoid heavy aggregates.
2. **Append-only `wallet_ledger_entries`** — source of truth for money; wallet balances updated in the same transaction.
3. **`session_requests` → `sessions`** — keeps accept/decline race (instant first-wins) clean without mutating history oddly.
4. **1:1 settings tables** — match GET/PUT API shapes; no JSON soup for toggles you query often.
5. **Lookup + junction tags** — filter listeners by language/comfort/boundary with indexed joins.
6. **JSONB only where flexible** — `rating_breakdown`, notification `data`, not core money fields.
7. **Soft delete users** — preserve session/payment history; filter `deleted_at IS NULL` in auth.

### Optional merge (if you want fewer than 43)

| Merge | Saves | Tradeoff |
|-------|------:|----------|
| Drop `listener_availability_settings`; keep slots + profile columns | 1 | Slightly fatter profile |
| Store privacy + notification prefs as JSONB on profiles | 4 | Harder to enforce bool columns / migrate |
| Skip `promo_redemptions` (log only on `session_payments`) | 1 | Weaker promo abuse control |

**Recommended production set: keep all 43.** Legal/help pages are static HTML (see `docs/static-web/`), not DB tables.

---

## Tier reference (seed / business rules, not a table)

| Tier | Min sessions | Min rating | Hourly rate |
|------|-------------:|-----------:|------------:|
| starter | 0 | 0 | $15 |
| rising | 10 | 4.0 | $20 |
| trusted | 25 | 4.3 | $25 |
| expert | 50 | 4.5 | $32 |
| elite | 100 | 4.7 | $40 |

`rate_per_minute ≈ hourly_rate / 60` (store computed value on listener for filters).

---

## API ↔ tables map (short)

| API area | Primary tables |
|----------|----------------|
| Auth 0–7, 1b, 2b–2c | `users`, `refresh_tokens`, `auth_identities` *(proposed)*, `password_reset_tokens` |
| Catalog 74–75 | `comfort_areas` (`icon_emoji` / `icon_url`), `languages` (`flag_emoji` / `flag_url`) — portal-managed; one languages table for all speaking-language UIs |
| Ventor profile / home | `ventor_profiles`, `mood_checkins`, `ventor_favorites`, `sessions` |
| Listener profile / setup | `listener_profiles`, identity, tag junctions, training |
| Availability | settings + `listener_availability_slots` |
| Discovery | `listener_profiles` + junctions + favorites + privacy |
| Book / accept / call | `session_requests`, `sessions`, `session_payments` |
| Ratings / reports | `session_ratings`, `session_listener_feedback`, `session_reports` |
| Earnings / payouts | `listener_wallets`, `wallet_ledger_entries`, `payout_methods`, `payouts` |
| Rewards / invites | `reward_offers`, `reward_trades`, `invite_codes`, `invite_events` |
| Notifications | `notifications` |
| Promo | `promo_codes`, `promo_redemptions` |
| Static legal/help | Hosted HTML under `webContentBaseUrl` — not database tables |

---

## Final count

| Metric | Value |
|--------|------:|
| **Total tables** | **43** |
| Lookup / catalog tables | 6 (`languages`, `comfort_areas`, `life_experiences`, `boundaries`, `achievements`, `training_modules`, `reward_offers`, `promo_codes` → **8** catalogs if counted) |
| Core transactional tables | `session_requests`, `sessions`, `session_payments`, `wallet_ledger_entries`, `payouts`, `reward_trades` |
| 1:1 settings / wallet | 7 |

**Total database tables to create: 43**

---

*Aligned with mobile UI models and [`docs/api-endpoints.md`](./api-endpoints.md). Adjust provider-specific payment fields when you pick Stripe/PayPal/etc.*
