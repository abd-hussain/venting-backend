# Venting Mobile — API Endpoints Spec

> **Status:** Proposed from a full UI/screen audit.  
> **Live HTTP calls in the app today:** `0` (Dio client exists; screens use mocks + `TODO` placeholders).  
> **Purpose:** Single reference for backend + mobile to implement the same contract.

---

## How to read this doc (fast)

| Column | Meaning |
|--------|---------|
| **#** | Endpoint index |
| **Method + Path** | HTTP verb and relative path (append to `BASE_URL`) |
| **Auth** | `Public` or `Bearer` |
| **Args** | Path / query / body |
| **Response** | Success JSON shape (200/201) |

**Conventions (all endpoints):**

| Item | Value |
|------|--------|
| Base URL | `String.fromEnvironment('BASE_URL')` |
| Content-Type | `application/json; charset=UTF-8` |
| Auth header | `Authorization: Bearer {accessToken}` |
| Common headers | `skel-platform`, `skel-os-version`, `skel-app-version`, `skel-installation-id`, `skel-network-type`, `skel-phone-version`, `accept-language` / `skel-accept-language`, `user-agent` |
| Dates | ISO-8601 UTC (`2026-08-14T12:00:00Z`) |
| Money | `number` (USD), 2 decimal places |
| IDs | `string` |

**Standard error (matches `MainAPIException`):**

```json
{
  "status": "failed",
  "error": {
    "type": "auth",
    "code": 100,
    "message": "Invalid credentials",
    "localized_message": { "en": "...", "ar": "..." }
  }
}
```

**Standard success envelope (recommended):**

```json
{
  "status": "success",
  "data": { }
}
```

List responses may include:

```json
{ "status": "success", "data": { "items": [], "total": 0, "page": 1, "page_size": 20 } }
```

---

## Quick index

| Domain | Count | Master list # |
|--------|------:|---------------|
| Auth & account | 9 | 0–7, 1b |
| Ventor profile / home / wellness | 14 | 8–21 |
| Listener profile / onboarding / dashboard | 15 | 22–36 |
| Listener availability | 3 | 37–39 |
| Discovery & sessions | 13 | 40–52 |
| Call feedback & reports | 3 | 53–55 |
| Listener earnings & payouts | 7 | 56–62 |
| Ventor rewards & invites | 5 | 63–67 |
| Notifications | 3 | 68–70 |
| Training | 2 | 71–72 |
| Promo | 1 | 73 |
| Catalog / categories | 2 | 74–75 |
| **Total** | **77** | |

---

## 1. Auth & account

### 0. `POST /v1/auth/check-email` *(proposed)*

> **Status:** Proposed — not implemented on backend or mobile yet.  
> **Purpose:** Email-first discovery — branch **Create account** vs **Sign in** before password submit. Does **not** authenticate.

| | |
|--|--|
| **Auth** | Public |
| **Screen** | Email auth step (after AuthScreen → “Continue with email”) |
| **When** | User finishes entering a valid email (on blur / Continue), **before** password submit |
| **Body** | `email` (string, required). Optional `role` (`ventor` \| `listener`) — role chosen on Welcome; used to detect mismatch when account exists |
| **Response** | `{ exists, email, role?, registration_complete?, listener_profile_status? }` |

**Request examples:**

```json
{ "email": "user@example.com" }
```

```json
{ "email": "user@example.com", "role": "ventor" }
```

**Success — new email (register path):**

```json
{
  "status": "success",
  "data": {
    "exists": false,
    "email": "new@example.com",
    "role": null,
    "registration_complete": null,
    "listener_profile_status": null
  }
}
```

**Success — existing listener, profile incomplete:**

```json
{
  "status": "success",
  "data": {
    "exists": true,
    "email": "l@example.com",
    "role": "listener",
    "registration_complete": false,
    "listener_profile_status": "incomplete"
  }
}
```

**Response fields (`data`):**

| Field | Type | When present | Meaning |
|-------|------|--------------|---------|
| `exists` | boolean | always | `false` = no account (or treated as unknown — see security) |
| `email` | string | always | Normalized email echoed back |
| `role` | `ventor` \| `listener` \| null | `exists == true` | Account role |
| `registration_complete` | boolean \| null | `exists == true` | Same meaning as `#7` |
| `listener_profile_status` | `incomplete` \| `under_review` \| `approved` \| `rejected` \| null | `exists == true` and `role == listener` | Same enum as `#7` |

**Mobile branching:**

| `exists` | Action | Next API |
|----------|--------|----------|
| `false` | Show **Create account** UI (password rules) | `#1 register` with Welcome `role` |
| `true` | Show **Sign in** UI | `#2 login` with account `role` |
| `true` + Welcome `role` ≠ account `role` | Block; explain role mismatch | — |
| After `#1` or `#2` success | Route user | `#7 GET /v1/auth/me` (source of truth) |

**Errors (standard envelope):**

| HTTP | `type` | `code` | When |
|------|--------|--------|------|
| 400 | `validation` | 110 | Missing / invalid email |
| 400 | `validation` | 111 | Invalid `role` |
| 409 | `auth` | 112 | Email exists but `role` in body ≠ account role |
| 403 | `auth` | 113 | Account deleted / disabled / banned |
| 429 | `rate_limit` | 429 | Too many checks (IP / installation id) |

**Security (required):**

- Rate limit (e.g. 10–20/min per IP and per `skel-installation-id`)
- Normalize email: trim + lowercase server-side
- No password, tokens, `id`, display name, or avatar in response
- Soft-deleted accounts: treat as `exists: false` **or** 403 — pick one and document
- Pure read; no session created

**Out of scope:** login/register replacement, OTP, password validation. Social auth is a separate endpoint — see [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md).

**Acceptance criteria:**

- [ ] Public `POST /v1/auth/check-email` with `{ email, role? }`
- [ ] Standard `{ status, data }` success envelope
- [ ] Mobile can branch register vs login without calling `#1`/`#2` until password submit
- [ ] After auth, `#7` remains routing authority

---

### 1. `POST /v1/auth/register`

| | |
|--|--|
| **Auth** | Public |
| **Screen** | Email registration → ventor/listener registration |
| **Body** | `email` (string), `password` (string), `role` (`ventor` \| `listener`) |
| **Response** | `access_token`, `refresh_token`, `user` `{ id, email, role, is_new: true }` |

Password rules (UI): min 8, 1 uppercase, 1 number.

---

### 2. `POST /v1/auth/login`

| | |
|--|--|
| **Auth** | Public |
| **Screen** | Email registration (sign-in path) |
| **Body** | `email`, `password`, `role` (`ventor` \| `listener`) |
| **Response** | `access_token`, `refresh_token`, `user` `{ id, email, role, registration_complete }` |

---

### 1b. `POST /v1/auth/social` *(proposed)*

> **Status:** Proposed — not implemented on backend or mobile yet.  
> **Full spec:** [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md)

| | |
|--|--|
| **Auth** | Public |
| **Screen** | AuthScreen → “Continue with Google” / “Continue with Apple” |
| **When** | After native Google/Apple Sign-In; mobile may call `#0 check-email` first when email is available |
| **Body** | `provider` (`google` \| `apple`), `id_token` (string), `role` (`ventor` \| `listener`), optional `nonce` (Apple), optional `full_name` |
| **Response** | Same session envelope as `#1` / `#2`: `access_token`, `refresh_token`, `user` `{ id, email, role, is_new, registration_complete }` |

**Request example:**

```json
{
  "provider": "google",
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "role": "ventor"
}
```

**Success example:**

```json
{
  "status": "success",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "role": "ventor",
      "is_new": true,
      "registration_complete": false
    }
  }
}
```

**Errors (see full doc for codes 120–127):** invalid token, role mismatch (409), account disabled (403), rate limit (429).

**After success:** mobile calls `#7 GET /v1/auth/me` for routing (same as email auth).

---

### 3. `POST /v1/auth/refresh`

| | |
|--|--|
| **Auth** | Public (refresh token) |
| **Body** | `refresh_token` |
| **Response** | `access_token`, `refresh_token` |

---

### 4. `POST /v1/auth/logout`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor / Listener profile settings |
| **Body** | optional `refresh_token` |
| **Response** | `{ "ok": true }` |

---

### 5. `DELETE /v1/auth/account`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Delete account confirm |
| **Body** | optional `password` |
| **Response** | `{ "ok": true }` |

---

### 6. `POST /v1/auth/change-password`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener change password |
| **Body** | `current_password`, `new_password` |
| **Response** | `{ "ok": true }` |

---

### 7. `GET /v1/auth/me`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Splash / shell bootstrap |
| **Args** | — |
| **Response** | `{ id, email, role, display_name, avatar_url, registration_complete, listener_profile_status? }` |

`listener_profile_status`: `under_review` \| `approved` \| `rejected` \| `incomplete`

---

## 2. Ventor profile / home / wellness

### 8. `POST /v1/ventors/register`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor registration (profile + interests) |
| **Body** | `nickname` (≤20), `gender` (`male` \| `female` \| `prefer_not_to_say`), `avatar` (multipart file **or** `avatar_preset_index`), `language_ids` (string[], ≥1), `interest_ids` (string[]) |
| **Response** | Ventor profile object (see #9) |

---

### 9. `GET /v1/ventors/me`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Ventor profile tab |
| **Response** | `{ id, nickname, email, avatar_url, gender, quote?, is_anonymous, stats: { sessions_count, points, streak_days }, language_ids, interest_ids }` |

---

### 10. `PATCH /v1/ventors/me`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Edit ventor profile sheet |
| **Body** | partial: `nickname?`, `avatar?` (multipart), `quote?` |
| **Response** | Updated profile (#9) |

---

### 11. `GET /v1/ventors/me/home`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor dashboard (aggregate — **prefer this over many small calls**) |
| **Response** | `{ display_name, mood_checkin_today?, streak: { current_days, target_days: 7, reward_offer_id, discount_percent }, upcoming_session?, recent_sessions: [{ id, listener_name, listener_avatar_url, when_label, duration_minutes, is_favorite }] }` |

---

### 12. `POST /v1/ventors/me/mood-checkins`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Mood check-in sheet |
| **Body** | `mood` (`great` \| `okay` \| `anxious` \| `sad` \| `angry`), `note` (string, optional) |
| **Response** | `{ id, mood, note, at, streak: { current_days, reward_unlocked? } }` |

---

### 13. `GET /v1/ventors/me/mood-journey`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor profile mood journey card |
| **Query** | `days` (default 7) |
| **Response** | `{ points: [{ day_index, mood }] }` — mood `0` sad → `1` happy |

---

### 14. `GET /v1/ventors/me/favorites`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | My listeners section |
| **Response** | `{ items: [{ id, name, rating, avatar_url }] }` |

---

### 15. `POST /v1/ventors/me/favorites/{listenerId}`

| | |
|--|--|
| **Auth** | Bearer |
| **Args** | path `listenerId` |
| **Response** | `{ "ok": true }` |

---

### 16. `DELETE /v1/ventors/me/favorites/{listenerId}`

| | |
|--|--|
| **Auth** | Bearer |
| **Args** | path `listenerId` |
| **Response** | `{ "ok": true }` |

---

### 17. `GET /v1/ventors/me/achievements`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Achievements bottom sheet |
| **Response** | `{ items: [{ id, title_key, subtitle_key, description_key, unlocked, unlocked_at? }] }` |

---

### 18. `GET /v1/ventors/me/privacy`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor privacy settings |
| **Response** | `{ show_mood_journey, show_achievements, show_stats, show_favorite_listeners, allow_listener_discovery }` |

---

### 19. `PUT /v1/ventors/me/privacy`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | Same fields as #18 (all bool) |
| **Response** | Updated privacy object |

---

### 20. `GET /v1/ventors/me/notification-preferences`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Ventor notification preferences |
| **Response** | `{ push_enabled, session_reminder_30_min, session_reminder_15_min, session_reminder_10_min, session_reminder_5_min, rewards_updates, promotions_updates, email_enabled }` |

---

### 21. `PUT /v1/ventors/me/notification-preferences`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | Same fields as #20 |
| **Response** | Updated preferences |

---

## 3. Listener profile / onboarding / dashboard

### 22. `POST /v1/listeners/register`

| | |
|--|--|
| **Auth** | Bearer (or Public if register creates account in one shot) |
| **Screen** | Listener registration steps 1–9 (multipart / JSON) |
| **Body** | See table below |
| **Response** | `{ listener_id, profile_status: "under_review" }` |

| Field | From step | Type |
|-------|-----------|------|
| `full_name`, `phone`, `phone_country`, `avatar`, `agreed_to_terms` | 1 | string / file / bool |
| `identity_document` (front/back), `selfie` | 2 | multipart |
| `date_of_birth`, `country_iso`, `city`, `language_ids` | 3 | date / string / string[] |
| `life_experience_ids`, `custom_experiences?` | 4 | string[] |
| `comfort_area_ids` | 5 | string[] |
| `boundary_ids` | 6 | string[] |
| `voice_intro` | 7 | audio multipart |
| `availability` (see #37 shape), `accept_instant_calls`, `session_minutes` | 8 | object |
| `notifications_enabled` | 9 | bool |

**Efficiency note:** Prefer one submit at end (`POST`) + optional `PATCH /v1/listeners/me/registration/{step}` for resume. If you split by step, keep the same field names.

---

### 23. `POST /v1/listeners/me/identity-verification`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Registration step 2 / re-verify |
| **Body** | multipart: `document_front`, `document_back?`, `selfie` |
| **Response** | `{ status: "pending" \| "approved" \| "rejected" }` |

---

### 24. `GET /v1/listeners/me`

| | |
|--|--|
| **Auth** | Bearer (listener) |
| **Screen** | Listener profile tab + settings |
| **Response** | `{ id, full_name, email, phone, phone_country, avatar_url, about_me, country, country_iso, city, language_ids, life_experiences, comfort_areas, boundaries, voice_intro_url, voice_intro_seconds, rating, review_count, session_count, is_online, profile_status, rate_per_minute }` |

---

### 25. `PATCH /v1/listeners/me`

| | |
|--|--|
| **Auth** | Bearer |
| **Screens** | Edit about / city / phone / experiences / comfort areas / boundaries / country / languages |
| **Body** | Partial fields from #24 (except computed rating/counts) |
| **Response** | Updated profile (#24) |

---

### 26. `POST /v1/listeners/me/voice-intro`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Edit voice intro sheet |
| **Body** | multipart `audio` (m4a/aac) |
| **Response** | `{ voice_intro_url, voice_intro_seconds }` |

---

### 27. `GET /v1/listeners/me/reviews`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Profile reviews bottom sheet |
| **Query** | `page`, `page_size` |
| **Response** | `{ rating, review_count, items: [{ id, reviewer_name, rating, comment, created_at }] }` |

---

### 28. `GET /v1/listeners/{listenerId}`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Ventor listener profile screen |
| **Response** | Public listener card: `VentorFindListener` fields — `id, name, avatar_url, rating, review_count, session_count, topics, languages, gender, rate_per_minute, bio, help_with, voice_preview_seconds, is_online, is_verified, rating_breakdown, country, city, country_iso, life_experiences, boundaries, availability, is_favorite` |

---

### 29. `GET /v1/listeners/me/setup-progress`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener dashboard setup |
| **Response** | `{ profile_approved, progress_percent, steps: [{ id, status }] }` |

`id`: `identity_verified` \| `profile_info` \| `availability` \| `training` \| `first_session_tutorial`  
`status`: `done` \| `in_progress` \| `locked`

---

### 30. `POST /v1/listeners/me/setup/first-session-tutorial`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | First-session tutorial ack |
| **Body** | `{ "acknowledged": true }` |
| **Response** | Updated setup progress (#29) |

---

### 31. `PATCH /v1/listeners/me/online-status`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener dashboard availability toggle |
| **Body** | `{ "is_online": true }` |
| **Response** | `{ "is_online": true }` |

---

### 32. `GET /v1/listeners/me/dashboard`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener dashboard (aggregate) |
| **Response** | `{ display_name, setup_progress, impact: { sessions_today, minutes_today, chart: [{ label, value }] }, next_upcoming_session?, is_online, reminder? }` |

---

### 33. `GET /v1/listeners/me/privacy`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Privacy & visibility |
| **Response** | `{ show_online_status, show_languages, show_comfort_areas, show_experience_and_ratings, show_boundaries, visible_in_all_countries, visible_countries, allow_search_indexing }` |

---

### 34. `PUT /v1/listeners/me/privacy`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | Same fields as #33 (`visible_countries` = ISO codes[]) |
| **Response** | Updated privacy object |

---

### 35. `GET /v1/listeners/me/notification-preferences`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener notification preferences |
| **Response** | `{ push_enabled, new_session_requests, session_reminder_15_min, session_reminder_10_min, session_reminder_5_min, reviews_feedback, tips_earnings, promotions_updates, email_enabled }` |

---

### 36. `PUT /v1/listeners/me/notification-preferences`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | Same fields as #35 |
| **Response** | Updated preferences |

---

## 4. Listener availability

### 37. `GET /v1/listeners/me/availability`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Availability tab |
| **Response** | `{ accept_instant_calls, session_length_minutes, break_length_minutes, language_ids, time_zone_id, days: [{ day: "mon", slots: [{ start: "09:00", end: "12:00" }] }] }` |

---

### 38. `PUT /v1/listeners/me/availability`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Persist session length / break / languages / instant / full week |
| **Body** | Full availability object (#37) |
| **Response** | Updated availability |

---

### 39. `PUT /v1/listeners/me/availability/days/{day}`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Day schedule bottom sheet |
| **Args** | path `day` = `mon`…`sun` |
| **Body** | `{ slots: [{ start, end }] }` |
| **Response** | Updated day |

---

## 5. Discovery & sessions

### 40. `GET /v1/listeners`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Ventor sessions tab — Find |
| **Query** | `q` (search), `topic`, `min_price`, `max_price`, `languages` (csv), `genders` (csv), `min_rating`, `favorites` (`any` \| `only` \| `exclude`), `online_only`, `page`, `page_size` |
| **Response** | `{ items: [ListenerPublic (#28)], total }` |

---

### 41. `POST /v1/sessions/instant-match`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | “Surprise me” / instant match |
| **Body** | optional filters: `topic?`, `language?`, `duration_minutes?` |
| **Response** | `{ listener: ListenerPublic, suggested_duration_minutes }` |

---

### 42. `POST /v1/sessions`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Before connecting → pay & book |
| **Body** | `{ listener_id, duration_minutes, time_mode: "instant" \| "nearest" \| "scheduled", scheduled_at?, call_mode: "voice" \| "video", speech_language, voice_change_enabled, promo_code?, reward_offer_id? }` |
| **Response** | `VentorBookedSession` + `payment: { amount_paid, currency, voice_change_fee, discount_amount }` |

---

### 43. `GET /v1/ventors/me/sessions`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Booked sessions list + home upcoming |
| **Query** | `status` (`upcoming` \| `live` \| `completed` \| `cancelled`), `page` |
| **Response** | `{ items: [{ id, listener_id, listener_name, listener_avatar_url, duration_minutes, status, call_mode, speech_language, amount_paid, voice_change_enabled, scheduled_at, is_instant, refunded_to_balance? }] }` |

---

### 44. `GET /v1/ventors/me/sessions/{sessionId}`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Booked session details |
| **Response** | Full booked session + listener summary |

---

### 45. `POST /v1/ventors/me/sessions/{sessionId}/cancel`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Cancel booked session |
| **Body** | optional `reason` |
| **Response** | `{ session, refunded_to_balance }` — UI expects **full** `amount_paid` refund |

---

### 46. `GET /v1/listeners/me/sessions`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Listener sessions tab |
| **Query** | `filter` = `upcoming` \| `missed` \| `history` |
| **Response** | `{ items: [{ id, scheduled_at, duration_minutes, ventor_name, ventor_avatar_url, message, chosen_reason, tags, speech_language, is_waiting, can_join_now, is_instant, is_video_call, ventor_rating, status_label?, session_cost?, is_missed, history_outcome?: "accepted" \| "declined" }] }` |

---

### 47. `GET /v1/listeners/me/session-stats`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Sessions stats card |
| **Response** | `{ accepted_count, declined_count, missed_count }` |

---

### 48. `GET /v1/listeners/me/session-requests`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Pending requests |
| **Response** | `{ items: [{ id, ventor_name, ventor_avatar_url, message, chosen_reason, scheduled_at, duration_minutes, tags, received_at, speech_language, is_instant, is_video_call, ventor_rating }] }` |

---

### 49. `POST /v1/listeners/me/session-requests/{requestId}/accept`

| | |
|--|--|
| **Auth** | Bearer |
| **Notes** | Instant: first accept wins |
| **Response** | `{ session_id, status: "accepted" \| "already_taken" }` |

---

### 50. `POST /v1/listeners/me/session-requests/{requestId}/decline`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | optional `reason` |
| **Response** | `{ "ok": true }` |

---

### 51. `POST /v1/sessions/{sessionId}/join`

| | |
|--|--|
| **Auth** | Bearer (either role) |
| **Screen** | Enter call |
| **Response** | `{ call_token, channel_id, expires_at, ice_servers? }` — VoIP provider payload |

---

### 52. `POST /v1/sessions/{sessionId}/end`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | optional `{ ended_by: "ventor" \| "listener", duration_seconds }` |
| **Response** | `{ session_id, status: "completed" }` |

---

## 6. Call feedback & reports

### 53. `POST /v1/sessions/{sessionId}/rating`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Ventor call rating |
| **Body** | `{ stars: 1–5, review?, tip_amount?: 2 \| 5 \| 10 \| null, report?: { reason, details? } }` |
| **Response** | `{ "ok": true, tip_charged? }` |

Ventor report reasons: `inappropriate_behavior`, `harassment`, `hate_speech`, `safety_concern`, `not_listening`, `technical_issue`, `other`

---

### 54. `POST /v1/sessions/{sessionId}/feedback`

| | |
|--|--|
| **Auth** | Bearer (listener) |
| **Screen** | Listener call rating |
| **Body** | `{ stars: 1–5, felt_heard: bool, talk_again: bool }` |
| **Response** | `{ "ok": true }` |

---

### 55. `POST /v1/sessions/{sessionId}/reports`

| | |
|--|--|
| **Auth** | Bearer (listener or ventor) |
| **Screen** | Call report sheets |
| **Body** | `{ reason, details?, reported_role: "ventor" \| "listener" }` |
| **Response** | `{ "ok": true, report_id }` |

Listener reasons: `inappropriate_behavior`, `harassment`, `hate_speech`, `safety_concern`, `technical_issue`, `other`

---

## 7. Listener earnings & payouts

### 56. `GET /v1/listeners/me/earnings`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Earnings tab summary |
| **Response** | `{ total_earnings, trend_percent, sessions, hours, rating, current_tier: { id, hourly_rate }, tiers: [{ id, min_sessions, min_rating, hourly_rate }] }` |

Tier ids: `starter` ($15) → `rising` ($20) → `trusted` ($25) → `expert` ($32) → `elite` ($40)

---

### 57. `GET /v1/listeners/me/earnings/chart`

| | |
|--|--|
| **Auth** | Bearer |
| **Query** | `from`, `to` (dates) |
| **Response** | `{ points: [{ label, amount }] }` |

---

### 58. `GET /v1/listeners/me/payout-balances`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Payment & payouts |
| **Response** | `{ available, pending, lifetime }` |

---

### 59. `GET /v1/listeners/me/payout-methods`

| | |
|--|--|
| **Auth** | Bearer |
| **Response** | `{ default_method?, methods: [{ id, type: "bank" \| "paypal", account_holder_name?, bank_name?, iban_or_account?, swift_code?, paypal_email?, label }] }` |

---

### 60. `PUT /v1/listeners/me/payout-methods`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Add/edit bank account |
| **Body** | `{ account_holder_name, bank_name, iban_or_account_number, swift_code? }` or PayPal fields |
| **Response** | Updated method |

---

### 61. `GET /v1/listeners/me/payouts`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Payout history |
| **Response** | `{ items: [{ id, amount, date, status: "completed" \| "pending" \| "failed", method_label, reference? }] }` |

---

### 62. `POST /v1/listeners/me/payouts`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Request payout |
| **Body** | `{ amount, payout_method_id }` |
| **Response** | Created payout history item |

---

## 8. Ventor rewards & invites

### 63. `GET /v1/ventors/me/rewards`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Rewards tab |
| **Response** | `{ points, completed_sessions, active_offer_id?, welcome_gift_claimed, offers: [{ id, kind: "percent_off" \| "free_minutes" \| "priority_match", points_cost, percent_off?, free_minutes?, audience: { min_tier?, max_tier? }, is_welcome_gift }], earn_rules: { points_per_session, points_per_friend_register, points_per_invite_first_session, points_per_friend_booking } }` |

---

### 64. `POST /v1/ventors/me/rewards/redeem`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | `{ offer_id }` |
| **Response** | `{ points_remaining, trade: { id, offer_id, points_spent, traded_at }, active_offer_id }` |

---

### 65. `GET /v1/ventors/me/rewards/trades`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Trade history |
| **Response** | `{ items: [{ id, offer_id, points_spent, traded_at, is_welcome_gift }] }` |

---

### 66. `GET /v1/ventors/me/invites`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Invite friends / history |
| **Response** | `{ invite_code, invite_link, total_invited, invite_points_earned, items: [{ id, name, status: "pending" \| "joined" \| "first_session" \| "booked_call", points_earned }] }` |

---

### 67. `POST /v1/ventors/me/invites/refresh-code` *(optional)*

| | |
|--|--|
| **Auth** | Bearer |
| **Response** | `{ invite_code, invite_link }` |

---

## 9. Notifications

### 68. `GET /v1/listeners/me/notifications`

| | |
|--|--|
| **Auth** | Bearer |
| **Query** | `unread_only` (bool) |
| **Response** | `{ items: [{ id, type: "session_request" \| "session_reminder" \| "review" \| "payout" \| "system", title, body, created_at, is_read }] }` |

---

### 69. `POST /v1/listeners/me/notifications/read-all`

| | |
|--|--|
| **Auth** | Bearer |
| **Response** | `{ "ok": true, updated_count }` |

---

### 70. `DELETE /v1/listeners/me/notifications/{notificationId}`

| | |
|--|--|
| **Auth** | Bearer |
| **Response** | `{ "ok": true }` |

---

## 10. Training

### 71. `GET /v1/listeners/me/training`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Training bottom sheet |
| **Response** | `{ modules: [{ id, title, status: "completed" \| "in_progress" \| "not_started", content_url }], all_completed }` |

Module ids used in UI: `art_of_listening`, `empathy`, `boundaries`, `difficult_situations`, `crisis_awareness`

---

### 72. `POST /v1/listeners/me/training/{moduleId}/complete`

| | |
|--|--|
| **Auth** | Bearer |
| **Response** | Updated training (#71) + setup progress if training finished |

---

## 11. Promo

### 73. `POST /v1/promo/validate`

| | |
|--|--|
| **Auth** | Bearer (ventor) |
| **Screen** | Before connecting checkout |
| **Body** | `{ code, listener_id, duration_minutes, subtotal }` |
| **Response** | `{ valid, discount_amount, label, percent_off?, fixed_amount? }` |

Demo codes in UI today: `SAVE10`, `VENT5`, `WELCOME15` (replace with real catalog).

---

## 12. Catalog / categories *(proposed)*

> Shared lookup lists for registration and filters. Seeded in DB (`comfort_areas`, `languages`, …).  
> Mobile **must not** hardcode category labels long-term — fetch from here.

> **Do not use** `GET /v1/catalog` (combined dump of languages + comfort areas + life experiences + boundaries).  
> That route is **not part of this contract** — remove it from the backend if it still exists.  
> Mobile and other clients must call the focused endpoints only:
> - `#74` `GET /v1/catalog/categories`
> - `#75` `GET /v1/catalog/languages`
> (Listener registration may later add focused endpoints for life experiences / boundaries — never the mega dump.)

### 74. `GET /v1/catalog/categories` *(proposed)*

> **Status:** Proposed — ventor registration interests from portal-managed `comfort_areas`.  
> **Purpose:** Return active interest / comfort categories for ventor (and optionally listener) registration.  
> **DB source:** `comfort_areas` (ids also used as `interest_ids` on `#8 POST /v1/ventors/register`).  
> **Icons:** `icon_url` (CDN) uploaded in admin portal — mobile does not map Material icon keys.

| | |
|--|--|
| **Auth** | Public (Bearer accepted if present). Catalog is not secret. |
| **Screen** | Ventor registration → interests step (`VentorRegistrationInterestsStep`) |
| **When** | When interests step opens (and on pull-to-retry / error retry) |
| **Query** | See below |
| **Response** | `{ items: Category[] }` |

#### Query parameters

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `audience` | `ventor` \| `listener` \| `all` | no | `all` | Filter by who may select the category. Ventor interests step sends `audience=ventor`. |
| `locale` | `en` \| `ar` | no | from `Accept-Language` / `skel-accept-language` | Optional hint; response still includes **both** `name_en` and `name_ar` so the client can switch language without re-fetch. |

#### `Category` object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable slug PK — same value sent later in `#8` `interest_ids` |
| `name_en` | string | yes | English label |
| `name_ar` | string | yes | Arabic label |
| `icon_url` | string | yes | Absolute HTTPS URL of the category icon/image (CDN). Mobile renders this image — **not** a Material `icon_key`. |
| `sort_order` | number | yes | Ascending; lower first |
| `allows_custom_text` | boolean | yes | `true` → show free-text field (e.g. `other`) |
| `topic_group` | string \| null | no | Optional grouping for admin / filters |

#### Success example

```http
GET /v1/catalog/categories?audience=ventor
Accept-Language: en
```

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "relationships",
        "name_en": "Relationships",
        "name_ar": "العلاقات",
        "icon_url": "https://cdn.venting.app/catalog/comfort/relationships.png",
        "sort_order": 10,
        "allows_custom_text": false,
        "topic_group": "relationships"
      },
      {
        "id": "marriage",
        "name_en": "Marriage",
        "name_ar": "الزواج",
        "icon_url": "https://cdn.venting.app/catalog/comfort/marriage.png",
        "sort_order": 20,
        "allows_custom_text": false,
        "topic_group": "relationships"
      },
      {
        "id": "parenting",
        "name_en": "Parenting",
        "name_ar": "الأبوة والأمومة",
        "icon_url": "https://cdn.venting.app/catalog/comfort/parenting.png",
        "sort_order": 30,
        "allows_custom_text": false,
        "topic_group": "family"
      },
      {
        "id": "career_work",
        "name_en": "Career & work",
        "name_ar": "المهنة والعمل",
        "icon_url": "https://cdn.venting.app/catalog/comfort/career_work.png",
        "sort_order": 40,
        "allows_custom_text": false,
        "topic_group": "work"
      },
      {
        "id": "stress_anxiety",
        "name_en": "Stress & anxiety",
        "name_ar": "التوتر والقلق",
        "icon_url": "https://cdn.venting.app/catalog/comfort/stress_anxiety.png",
        "sort_order": 50,
        "allows_custom_text": false,
        "topic_group": "mental"
      },
      {
        "id": "loneliness",
        "name_en": "Loneliness",
        "name_ar": "الوحدة",
        "icon_url": "https://cdn.venting.app/catalog/comfort/loneliness.png",
        "sort_order": 60,
        "allows_custom_text": false,
        "topic_group": "mental"
      },
      {
        "id": "student_life",
        "name_en": "Student life",
        "name_ar": "حياة الطالب",
        "icon_url": "https://cdn.venting.app/catalog/comfort/student_life.png",
        "sort_order": 70,
        "allows_custom_text": false,
        "topic_group": "life"
      },
      {
        "id": "financial_stress",
        "name_en": "Financial stress",
        "name_ar": "الضغط المالي",
        "icon_url": "https://cdn.venting.app/catalog/comfort/financial_stress.png",
        "sort_order": 80,
        "allows_custom_text": false,
        "topic_group": "money"
      },
      {
        "id": "health_wellness",
        "name_en": "Health & wellness",
        "name_ar": "الصحة والعافية",
        "icon_url": "https://cdn.venting.app/catalog/comfort/health_wellness.png",
        "sort_order": 90,
        "allows_custom_text": false,
        "topic_group": "health"
      },
      {
        "id": "other",
        "name_en": "Other",
        "name_ar": "أخرى",
        "icon_url": "https://cdn.venting.app/catalog/comfort/other.png",
        "sort_order": 1000,
        "allows_custom_text": true,
        "topic_group": null
      }
    ]
  }
}
```

#### Seed notes

| `id` | `allows_custom_text` | Notes |
|------|----------------------|-------|
| `relationships` … `health_wellness` | `false` | Icons uploaded in portal → stored as `icon_url` |
| `other` | `true` | Free-text required on mobile when selected |

Mobile must **not** hardcode category labels or icons. Missing/broken `icon_url` → show a generic placeholder image/icon.

#### Mobile usage

1. Open Ventor registration interests step.
2. `GET /v1/catalog/categories?audience=ventor`.
3. Render `items` sorted by `sort_order`.
4. Localized label: `locale == ar ? name_ar : name_en`.
5. Leading image: load `icon_url` (cached network image).
6. If item has `allows_custom_text == true` and is selected → show free-text field; require non-empty trim before Finish.
7. On Finish → collect selected `id`s (+ optional custom text for `other`) → send as `interest_ids` (and optional `other_interest_text`) on `#8 POST /v1/ventors/register`.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 400 | validation | 740 | Invalid `audience` |
| 500 | server | 500 | Unexpected failure |
| 503 | server | 503 | Catalog unavailable |

Empty active catalog → still `200` with `"items": []` (mobile shows empty + retry). Do **not** 404.

#### Rules

- Only return rows with `is_active = true`.
- IDs are immutable once shipped — changing an `id` breaks existing `ventor_interests` / `interest_ids`.
- Add/remove/reorder/upload icons via admin CMS (`/v1/admin/catalog/comfort-areas`); this public GET is read-only.
- `icon_url` must be a public absolute HTTPS URL (CDN). Portal uploads the asset, then stores the resulting URL on the row.
- Cache-friendly: `Cache-Control: public, max-age=300` recommended (optional).

#### Acceptance criteria

- [ ] `GET /v1/catalog/categories?audience=ventor` returns active rows with `icon_url`
- [ ] Standard `{ status, data: { items } }` envelope
- [ ] Both `name_en` and `name_ar` present
- [ ] `other` has `allows_custom_text: true`
- [ ] Inactive rows omitted
- [ ] Same `id` values accepted by `#8` `interest_ids`
- [ ] Portal can create/update categories and upload/replace `icon_url`

#### Link to register

| Step | API |
|------|-----|
| Load chips | `#74 GET /v1/catalog/categories?audience=ventor` |
| Submit profile + interests | `#8 POST /v1/ventors/register` with `interest_ids: ["relationships", "career_work", …]` |

Optional body extension on `#8` when `other` selected:

```json
{
  "nickname": "QuietFox",
  "gender": "prefer_not_to_say",
  "avatar_preset_index": 2,
  "language_ids": ["en", "ar"],
  "interest_ids": ["stress_anxiety", "other"],
  "other_interest_text": "Grief after moving cities"
}
```

---

### 75. `GET /v1/catalog/languages` *(proposed)*

> **Status:** Proposed — ventor (and listener) speaking-language picker.  
> **Purpose:** Return active spoken languages from the **single** `languages` table.  
> **DB source:** `languages` only — there is **no** separate speaking-languages catalog.  
> **Managed by:** Admin portal `/catalogs` → Languages (`A48`/`A49`).

| | |
|--|--|
| **Auth** | Public (Bearer accepted if present) |
| **Screen** | Ventor registration → **Choose your Language** step (also listener language pickers / filters) |
| **When** | Step open / search retry |
| **Query** | `q` (optional search string — filters `name_en`, `name_native`, `name_ar`) |
| **Response** | `{ items: Language[] }` |

#### `Language` object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable code PK — e.g. `en`, `ar`, `hi` — sent as `language_ids` on `#8` / listener profile |
| `name_en` | string | yes | English display name (`English`) |
| `name_native` | string | yes | Native script name (`العربية`, `हिन्दी`) |
| `name_ar` | string | yes | Arabic translation of the language name |
| `flag_url` | string | yes | Absolute HTTPS URL of flag image (CDN). Mobile shows this in the circular avatar. |
| `flag_emoji` | string \| null | no | Optional emoji fallback only; mobile **prefers `flag_url`** |
| `sort_order` | number | yes | Ascending |

#### Success example

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "en",
        "name_en": "English",
        "name_native": "English",
        "name_ar": "الإنجليزية",
        "flag_url": "https://cdn.venting.app/catalog/flags/en.png",
        "flag_emoji": "🇺🇸",
        "sort_order": 10
      },
      {
        "id": "hi",
        "name_en": "Hindi",
        "name_native": "हिन्दी",
        "name_ar": "الهندية",
        "flag_url": "https://cdn.venting.app/catalog/flags/hi.png",
        "flag_emoji": "🇮🇳",
        "sort_order": 20
      },
      {
        "id": "es",
        "name_en": "Spanish",
        "name_native": "Español",
        "name_ar": "الإسبانية",
        "flag_url": "https://cdn.venting.app/catalog/flags/es.png",
        "flag_emoji": "🇪🇸",
        "sort_order": 30
      },
      {
        "id": "ar",
        "name_en": "Arabic",
        "name_native": "العربية",
        "name_ar": "العربية",
        "flag_url": "https://cdn.venting.app/catalog/flags/ar.png",
        "flag_emoji": "🇸🇦",
        "sort_order": 40
      },
      {
        "id": "bn",
        "name_en": "Bengali",
        "name_native": "বাংলা",
        "name_ar": "البنغالية",
        "flag_url": "https://cdn.venting.app/catalog/flags/bn.png",
        "flag_emoji": "🇧🇩",
        "sort_order": 50
      },
      {
        "id": "tr",
        "name_en": "Turkish",
        "name_native": "Türkçe",
        "name_ar": "التركية",
        "flag_url": "https://cdn.venting.app/catalog/flags/tr.png",
        "flag_emoji": "🇹🇷",
        "sort_order": 60
      }
    ]
  }
}
```

#### Mobile list row

Display: `[flag circle from flag_url]  {name_native} ({name_en})  [checkbox]`  
Selected: purple border on tile + filled purple checkbox.  
Multi-select allowed; **at least one** required before Continue.

Same endpoint powers listener language selection — do not invent a second languages API/table.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 400 | validation | 750 | Invalid query |
| 500 / 503 | server | … | Failure |

Empty → `200` + `items: []`.

#### Acceptance

- [ ] Public `GET /v1/catalog/languages` reads **only** from `languages`
- [ ] Each active item has a non-empty `flag_url` (HTTPS CDN)
- [ ] Seed includes en, hi, es, ar, bn, tr (minimum)
- [ ] `#8` accepts `language_ids` subset of active language ids → writes `ventor_languages`
- [ ] Portal can upsert languages and upload/replace flag images
- [ ] Search `q` filters server-side **or** mobile filters client-side (either OK for v1; prefer client filter for small lists)

---
## Efficiency guidelines (for implementers)

1. **Prefer aggregates** — `#11` ventor home and `#30` listener dashboard load one screen in one round-trip.
2. **Prefer `PATCH` partial updates** — listener/ventor profile edits should not require full object.
3. **One discovery list** — `#40` carries filters; avoid separate endpoints per filter chip.
4. **Multipart only when needed** — avatar, ID docs, voice intro, registration photo.
5. **Pagination** — lists (`sessions`, `listeners`, `reviews`, `notifications`, `payouts`) should support `page` + `page_size`.
6. **Idempotent writes** — accept/decline/redeem/cancel should be safe to retry (`409` / clear status when already handled).

---

## Static / non-API URLs (not counted)

| URL | Use | 
|-----|-----|
| `{termsUrl}` | Terms WebView |
| `{privacyUrl}` | Privacy WebView |
| `{helpCenterBaseUrl}/…` | Help articles |
| `mailto:support@venting.app` | Support email |
| WhatsApp `wa.me` | Support / share |

---

## Endpoint count

| Category | Count |
|----------|------:|
| Auth & account | 8 |
| Ventor profile / home / wellness | 14 |
| Listener profile / onboarding / dashboard | 15 |
| Listener availability | 3 |
| Discovery & sessions | 13 |
| Call feedback & reports | 3 |
| Earnings & payouts | 7 |
| Rewards & invites | 5 |
| Notifications | 3 |
| Training | 2 |
| Promo | 1 |
| Catalog / categories | 2 |
| **Total unique API endpoints** | **77** |

### Master checklist (method + path)

| # | Method | Path |
|---|--------|------|
| 0 | POST | `/v1/auth/check-email` *(proposed)* |
| 1 | POST | `/v1/auth/register` |
| 2 | POST | `/v1/auth/login` |
| 1b | POST | `/v1/auth/social` *(proposed)* |
| 3 | POST | `/v1/auth/refresh` |
| 4 | POST | `/v1/auth/logout` |
| 5 | DELETE | `/v1/auth/account` |
| 6 | POST | `/v1/auth/change-password` |
| 7 | GET | `/v1/auth/me` |
| 8 | POST | `/v1/ventors/register` |
| 9 | GET | `/v1/ventors/me` |
| 10 | PATCH | `/v1/ventors/me` |
| 11 | GET | `/v1/ventors/me/home` |
| 12 | POST | `/v1/ventors/me/mood-checkins` |
| 13 | GET | `/v1/ventors/me/mood-journey` |
| 14 | GET | `/v1/ventors/me/favorites` |
| 15 | POST | `/v1/ventors/me/favorites/{listenerId}` |
| 16 | DELETE | `/v1/ventors/me/favorites/{listenerId}` |
| 17 | GET | `/v1/ventors/me/achievements` |
| 18 | GET | `/v1/ventors/me/privacy` |
| 19 | PUT | `/v1/ventors/me/privacy` |
| 20 | GET | `/v1/ventors/me/notification-preferences` |
| 21 | PUT | `/v1/ventors/me/notification-preferences` |
| 22 | POST | `/v1/listeners/register` |
| 23 | POST | `/v1/listeners/me/identity-verification` |
| 24 | GET | `/v1/listeners/me` |
| 25 | PATCH | `/v1/listeners/me` |
| 26 | POST | `/v1/listeners/me/voice-intro` |
| 27 | GET | `/v1/listeners/me/reviews` |
| 28 | GET | `/v1/listeners/{listenerId}` |
| 29 | GET | `/v1/listeners/me/setup-progress` |
| 30 | POST | `/v1/listeners/me/setup/first-session-tutorial` |
| 31 | PATCH | `/v1/listeners/me/online-status` |
| 32 | GET | `/v1/listeners/me/dashboard` |
| 33 | GET | `/v1/listeners/me/privacy` |
| 34 | PUT | `/v1/listeners/me/privacy` |
| 35 | GET | `/v1/listeners/me/notification-preferences` |
| 36 | PUT | `/v1/listeners/me/notification-preferences` |
| 37 | GET | `/v1/listeners/me/availability` |
| 38 | PUT | `/v1/listeners/me/availability` |
| 39 | PUT | `/v1/listeners/me/availability/days/{day}` |
| 40 | GET | `/v1/listeners` |
| 41 | POST | `/v1/sessions/instant-match` |
| 42 | POST | `/v1/sessions` |
| 43 | GET | `/v1/ventors/me/sessions` |
| 44 | GET | `/v1/ventors/me/sessions/{sessionId}` |
| 45 | POST | `/v1/ventors/me/sessions/{sessionId}/cancel` |
| 46 | GET | `/v1/listeners/me/sessions` |
| 47 | GET | `/v1/listeners/me/session-stats` |
| 48 | GET | `/v1/listeners/me/session-requests` |
| 49 | POST | `/v1/listeners/me/session-requests/{requestId}/accept` |
| 50 | POST | `/v1/listeners/me/session-requests/{requestId}/decline` |
| 51 | POST | `/v1/sessions/{sessionId}/join` |
| 52 | POST | `/v1/sessions/{sessionId}/end` |
| 53 | POST | `/v1/sessions/{sessionId}/rating` |
| 54 | POST | `/v1/sessions/{sessionId}/feedback` |
| 55 | POST | `/v1/sessions/{sessionId}/reports` |
| 56 | GET | `/v1/listeners/me/earnings` |
| 57 | GET | `/v1/listeners/me/earnings/chart` |
| 58 | GET | `/v1/listeners/me/payout-balances` |
| 59 | GET | `/v1/listeners/me/payout-methods` |
| 60 | PUT | `/v1/listeners/me/payout-methods` |
| 61 | GET | `/v1/listeners/me/payouts` |
| 62 | POST | `/v1/listeners/me/payouts` |
| 63 | GET | `/v1/ventors/me/rewards` |
| 64 | POST | `/v1/ventors/me/rewards/redeem` |
| 65 | GET | `/v1/ventors/me/rewards/trades` |
| 66 | GET | `/v1/ventors/me/invites` |
| 67 | POST | `/v1/ventors/me/invites/refresh-code` |
| 68 | GET | `/v1/listeners/me/notifications` |
| 69 | POST | `/v1/listeners/me/notifications/read-all` |
| 70 | DELETE | `/v1/listeners/me/notifications/{notificationId}` |
| 71 | GET | `/v1/listeners/me/training` |
| 72 | POST | `/v1/listeners/me/training/{moduleId}/complete` |
| 73 | POST | `/v1/promo/validate` |
| 74 | GET | `/v1/catalog/categories` *(proposed)* |
| 75 | GET | `/v1/catalog/languages` *(proposed)* |

---

## Final count

**Total unique API endpoints: 73**

**Live / wired in the mobile app today: 0**

---

*Generated from screen models, mock catalogs, and `TODO: … API` markers across `lib/presentation` (auth, ventor home/sessions/rewards/profile/call, listener dashboard/sessions/earnings/availability/profile/call/registration).*
