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
| Auth & account | 11 | 0–7, 1b, 2b–2c |
| Ventor profile / home / wellness | 14 | 8–21 |
| Listener profile / onboarding / dashboard | 16 | 22–36 |
| Listener availability | 3 | 37–39 |
| Discovery & sessions | 13 | 40–52 |
| Call feedback & reports | 3 | 53–55 |
| Listener earnings & payouts | 7 | 56–62 |
| Ventor rewards & invites | 5 | 63–67 |
| Notifications | 3 | 68–70 |
| Training | 2 | 71–72 |
| Promo | 1 | 73 |
| Catalog / categories | 2 | 74–75 |
| **Total** | **79** | |

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

### 2b. `POST /v1/auth/forgot-password` *(proposed)*

> **Status:** Proposed — mobile wires this from Forgot Password confirmation.  
> **Purpose:** Start a **secure password reset**. Sends an email with a one-time link to a branded reset page.  
> **Does not** authenticate the user or reveal whether the email exists.

| | |
|--|--|
| **Auth** | Public |
| **Screen** | Forgot password confirmation (after wrong credentials on email login) |
| **When** | User confirms email and taps Continue |
| **Body** | `email` (string, required), `role` (`ventor` \| `listener`, required), optional `locale` (`en` \| `ar`) |
| **Response** | Always `{ email, sent: true }` on HTTP 200 when request is well-formed (anti-enumeration) |

#### Request

```json
{
  "email": "user@example.com",
  "role": "ventor",
  "locale": "en"
}
```

#### Success

```json
{
  "status": "success",
  "data": {
    "email": "user@example.com",
    "sent": true
  }
}
```

#### Security rules (required)

- Generate a **cryptographically random** token (≥ 32 bytes), store only a **hash** (e.g. SHA-256) in `password_reset_tokens`.
- Token TTL: **60 minutes**, single-use. Invalidate previous unused tokens for the same user on new request.
- Email link: `{webContentBaseUrl}/auth/{locale}/reset-password.html?token={rawToken}`  
  Shared host: `https://venting-3a5ebaed4621.herokuapp.com`
- Rate-limit by IP + email (e.g. 5 / hour).
- Do **not** return different errors for unknown emails (always same success shape).
- Reset emails are for **email/password accounts only** (skip send quietly for social-only accounts, still return success).

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 400 | validation | 210 | Invalid email / role / locale |
| 429 | rate_limit | 211 | Too many requests |
| 500 | server | 500 | Unexpected failure |

#### Acceptance

- [ ] Public endpoint; no Bearer required
- [ ] Email contains branded HTML (Venting dark/purple) + clear CTA button
- [ ] Link opens locale-matched static reset page with token query param
- [ ] Mobile shows success after Continue without leaking account existence

---

### 2c. `POST /v1/auth/reset-password` *(proposed)*

> **Status:** Proposed — called by the **static reset-password web page** (not by the mobile app).  
> **Purpose:** Set a new password using a valid one-time token from the email link.

| | |
|--|--|
| **Auth** | Public (token in body) |
| **Caller** | Reset password HTML page (`/auth/{locale}/reset-password.html`) |
| **Body** | `token` (string), `password` (string) |
| **Password rules** | Same as register: min 8, 1 uppercase, 1 number |

#### Request

```json
{
  "token": "raw-token-from-email-link",
  "password": "NewPass1"
}
```

#### Success

```json
{
  "status": "success",
  "data": {
    "email": "user@example.com",
    "reset": true
  }
}
```

#### Security rules

- Look up by **hash(token)**; reject if missing, expired, or already used.
- Mark token used in the same DB transaction as password update.
- Invalidate all refresh sessions for that user after reset (force re-login).
- Do not leak whether token was invalid vs expired in a way that aids attacks — use generic “invalid or expired link”.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 400 | validation | 220 | Weak password / missing fields |
| 400 | auth | 221 | Invalid or expired token |
| 429 | rate_limit | 222 | Too many attempts |
| 500 | server | 500 | Unexpected failure |

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
| **Auth** | `Authorization: Bearer {access_token}` |
| **Screen** | Shared destructive confirm sheet (ventor + listener settings) |
| **Body** | optional `refresh_token` (to revoke that session server-side) |
| **Response** | `{ "status": "success", "data": { "ok": true } }` |

Mobile: on success clear local session and go to welcome.

---

### 5. `DELETE /v1/auth/account`

| | |
|--|--|
| **Auth** | `Authorization: Bearer {access_token}` |
| **Screen** | Shared destructive confirm sheet (ventor + listener settings) |
| **Body** | optional `password` |
| **Response** | `{ "status": "success", "data": { "ok": true } }` |

Mobile: on success clear local session and go to welcome.

---

### 6. `POST /v1/auth/change-password`

| | |
|--|--|
| **Auth** | `Authorization: Bearer {access_token}` — JWT access token only; **do not** send `refresh_token` in header or body |
| **Screen** | Shared change password (ventor + listener settings) |
| **Body** | `current_password`, `new_password` |
| **Response** | `{ "status": "success", "data": { "ok": true } }` |

**Mobile contract:**

- Read `access_token` from secure storage (`SavedConstants.accessToken`) and send as `Authorization: Bearer {access_token}` on every request (repository header + Dio interceptor).
- `401` on this endpoint means wrong `current_password` or invalid/missing access token — **must not** trigger `#3` token refresh (unlike `#7` / profile APIs).
- `refresh_token` is only used by `#3 POST /v1/auth/refresh`, never for change-password.

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

### 8. Ventor registration (step-based)

> **Replaces** the old one-shot `POST /v1/ventors/register`. Each wizard step saves independently so the user can **Skip** and finish later.

| Step | Endpoint | When |
|------|----------|------|
| Resume | `GET /v1/ventors/register/progress` | On registration screen open |
| 1 Profile | `PATCH /v1/ventors/register/steps/profile` | Continue from profile step |
| 2 Languages | `PATCH /v1/ventors/register/steps/languages` | Continue from language step |
| 3 Interests | `PATCH /v1/ventors/register/steps/interests` | Continue from interests step |
| 4 Notifications | `POST /v1/ventors/register/complete` | After notifications permission |

#### 8a. `GET /v1/ventors/register/progress`

| | |
|--|--|
| **Auth** | Bearer (`registration_complete = false`) |
| **Response** | `{ registration_complete, next_step, completed_steps[], saved: { profile?, languages?, interests? } }` |

`next_step`: `profile` \| `languages` \| `interests` \| `notifications`  
`completed_steps`: subset of `profile`, `languages`, `interests`  
`saved.profile`: `{ nickname, gender, avatar_url?, avatar_preset_index? }`  
`saved.languages`: `{ language_ids[] }`  
`saved.interests`: `{ interest_ids[], other_interest_text? }`

Each step `PATCH` returns the **same progress envelope** as `#8a`.

#### 8b. `PATCH /v1/ventors/register/steps/profile`

| Field | Required | Notes |
|-------|----------|-------|
| `nickname` | yes | 1–20 chars |
| `gender` | yes | `male` \| `female` \| `prefer_not_to_say` |
| `avatar` | no | Multipart file when gallery photo chosen |
| `avatar_preset_index` | no | 0-based preset when no gallery photo |

JSON or multipart (multipart when uploading `avatar`).

#### 8c. `PATCH /v1/ventors/register/steps/languages`

| Field | Required | Notes |
|-------|----------|-------|
| `language_ids` | yes | JSON array, ≥1 from `#75` |

#### 8d. `PATCH /v1/ventors/register/steps/interests`

| Field | Required | Notes |
|-------|----------|-------|
| `interest_ids` | yes | JSON array, ≥1 from `#74` |
| `other_interest_text` | conditional | When an `allows_custom_text` id is selected |

#### 8e. `POST /v1/ventors/register/complete`

Finalizes ventor registration. JSON body.

| Field | Required | Notes |
|-------|----------|-------|
| `notifications_enabled` | yes | `true` when OS notification permission was granted (or provisional on iOS); `false` when denied |
| `fcm_token` | no | Include when the app has a non-empty FCM device token; omit the field entirely when unavailable. Registration must succeed without it |

**FCM storage:** When `fcm_token` is present, the server upserts into `user_push_tokens` for the authenticated user.

**Response:** Ventor profile (#9). Sets `users.registration_complete = true`.

#### Mobile flow

1. Open registration → `#8a` → hydrate UI + jump to `next_step`.  
2. Each **Continue** → save that step (`#8b`–`#8d`).  
3. **Skip** → home without calling the current step (prior saved steps remain).  
4. Notifications step → `#8e` → ventor home.

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

### 22. Listener registration (step-based)

> **Replaces** the old one-shot `POST /v1/listeners/register`. Each wizard step saves independently so the user can **Skip for now** and finish later.

| Step | Endpoint | Content-Type |
|------|----------|----------------|
| Resume | `GET /v1/listeners/register/progress` | JSON |
| 1 Profile | `PATCH /v1/listeners/register/steps/profile` | multipart (`avatar`) |
| 2 Identity | `PATCH /v1/listeners/register/steps/identity` | multipart (`identity_document`, `selfie`) |
| 3 About you | `PATCH /v1/listeners/register/steps/about` | JSON |
| 4 Experiences | `PATCH /v1/listeners/register/steps/experiences` | JSON |
| 5 Comfort areas | `PATCH /v1/listeners/register/steps/comfort-areas` | JSON |
| 6 Boundaries | `PATCH /v1/listeners/register/steps/boundaries` | JSON |
| 7 Voice intro | `PATCH /v1/listeners/register/steps/voice-intro` | multipart (`voice_intro`) |
| 8 Availability | `PATCH /v1/listeners/register/steps/availability` | JSON |
| 9 Notifications | `POST /v1/listeners/register/complete` | JSON |

#### 22a. `GET /v1/listeners/register/progress`

| | |
|--|--|
| **Auth** | Bearer (`registration_complete = false`) |
| **Response** | `{ registration_complete, profile_status?, next_step, completed_steps[], saved: { profile?, identity?, about?, … } }` |

`next_step`: `profile` \| `identity` \| `about` \| `experiences` \| `comfort-areas` \| `boundaries` \| `voice-intro` \| `availability` \| `notifications`  
`saved.*` returns previously saved field values and media URLs for resume.  
Each step `PATCH` returns the **same progress envelope** as `#22a`.

#### Step payloads (save on Continue)

| Step | Fields |
|------|--------|
| **profile** | `avatar` (file), `full_name`, `phone` (E.164), `phone_country` |
| **identity** | `identity_document` (file), `selfie` (file) — **not** `document_front` / `document_back` |
| **about** | `date_of_birth`, `country_iso`, `city`, `language_ids[]` |
| **experiences** | `life_experience_ids[]` (catalog only, `#76`), `relationship_status` (client enum), `family_role_ids[]` (client enums), optional `custom_experiences[]` |
| **comfort-areas** | `comfort_area_ids[]`, optional `custom_comfort_area_text` |
| **boundaries** | `boundary_ids[]` (≥1), optional `custom_boundary_text` |
| **voice-intro** | `voice_intro` (file), `voice_intro_seconds` |
| **availability** | `accept_instant_calls`, `session_minutes` (int), `availability` object (`#37` shape) |

**Do not send:** `agreed_to_terms`, `notifications_enabled`, `document_front`, `document_back`.

Multipart steps: omit file parts when the user did not change an already-uploaded asset (server keeps existing URLs).

#### 22j. `POST /v1/listeners/register/complete`

Finalizes listener registration after all step saves. JSON body.

| Field | Required | Notes |
|-------|----------|-------|
| `fcm_token` | no | Include when the app has a non-empty FCM device token; omit the field entirely when unavailable. Registration must succeed without it |

**FCM storage:** When `fcm_token` is present, the server upserts into `user_push_tokens` for the authenticated user.

**Response:** `{ listener_id, profile_status: "under_review" }`. Requires all prior steps complete. Sets `users.registration_complete = true`.

#### Mobile flow

1. Open registration → `#22a` → hydrate draft + jump to `next_step`.  
2. Each **Continue** → `PATCH …/steps/{step}` for that step.  
3. **Skip for now** → home; saved steps remain on server.  
4. Step 9 → `#22j` → under-review screen.

---

### 23. `POST /v1/listeners/me/identity-verification`

> **Purpose:** Resubmit KYC / identity documents **after an admin rejects** the listener’s previous verification.  
> **Not for first-time registration** — first upload is part of `#22` step `identity`.

| | |
|--|--|
| **Auth** | Bearer (listener) |
| **When** | Listener `profile_status` (or identity verification status) is **`rejected`** and the user taps resubmit / re-verify |
| **Screen** | KYC rejected / resubmit identity screen (not the initial registration step 2 submit) |
| **Body** | multipart: `identity_document`, `selfie` (same naming as `#22`; no front/back) |
| **Response** | `{ status: "pending" }` — returns to admin review queue |

#### Rules

- Call **only** when prior KYC was **rejected by admin** (or an explicit re-verify flow after rejection).
- Do **not** call during first registration — identity files belong on `#22` step `identity`.
- On success: set verification status back to **pending** / `under_review`; clear or archive the rejected attempt as needed.
- Listener does **not** redo full `#22` registration for a KYC-only rejection.

#### Acceptance

- [ ] Rejected listeners can resubmit docs without re-entering profile / experiences / voice / availability
- [ ] First-time onboarding never requires `#23`
- [ ] Successful resubmit puts the case back in the admin review queue
- [ ] Field names match `#22` (`identity_document` + `selfie`)

---

### 24. `GET /v1/listeners/me`

| | |
|--|--|
| **Auth** | Bearer (listener) |
| **Screen** | Listener profile tab + settings |
| **Response** | `{ id, full_name, email, phone, phone_country, avatar_url, about_me, country, country_iso, city, language_ids, life_experiences, comfort_areas, boundaries, voice_intro_url, voice_intro_seconds, rating, review_count, session_count, is_online, profile_status, rate_per_minute, rating_breakdown? }` |

**`life_experiences` shape (GET):** object (preferred) or array:

```json
{
  "life_experience_ids": ["job_loss", "grief_loss"],
  "relationship_status": "widowed",
  "family_role_ids": ["single_parent"],
  "custom_experiences": ["Raised twins abroad"]
}
```

Legacy array form is still accepted (`["job_loss", "widowed", …]` or `[{ "id": "job_loss" }, …]`).

**`comfort_areas` / `boundaries` (GET):** object with `*_ids` + optional `custom_*_text`, or legacy id array.

**Media URL note:** `avatar_url` and `voice_intro_url` are often **relative** paths (e.g. `/static/uploads/avatars/{user_id}.jpg`). Mobile must prefix with API `baseUrl` before `Image.network` / audio playback. See [Media URLs](#media-urls-static-uploads) below.

---

### 25. `PATCH /v1/listeners/me`

| | |
|--|--|
| **Auth** | Bearer |
| **Screens** | Edit about / city / phone / experiences / comfort areas / boundaries / country / languages |
| **Content-Type** | `application/json` only |
| **Body** | Partial JSON fields from #24 (except computed `rating` / `review_count` / `session_count`). **Do not** send multipart here. |
| **Response** | Updated profile (#24) |

#### Allowed JSON fields

| Field | Type | Notes |
|-------|------|-------|
| `about_me` | string \| null | Bio text |
| `phone` | string | E.164 |
| `phone_country` | string | ISO-3166 alpha-2 (e.g. `JO`) |
| `country` | string \| null | Display country name |
| `country_iso` | string | ISO-3166 alpha-2 |
| `city` | string | Max 30 chars |
| `language_ids` | string[] | Replaces spoken languages |
| `life_experience_ids` | string[] | Catalog experience tag ids from `#76` only (`job_loss`, `grief_loss`, …) |
| `relationship_status` | string \| null | Client enum: `single` \| `in_relationship` \| `married` \| `divorced` \| `widowed` |
| `family_role_ids` | string[] | Client enums: `parent`, `single_parent`, `caregiver` |
| `custom_experiences` | string[] | Free-text experiences (plain labels). Send `[]` to clear all custom rows. |
| `comfort_area_ids` | string[] | Comfort area ids from `#74` |
| `custom_comfort_area_text` | string \| null | Required when `other` comfort area is selected |
| `boundary_ids` | string[] | Boundary ids from `#77` |
| `custom_boundary_text` | string \| null | Required when `other` boundary is selected |

> **Experiences PATCH:** Same split as registration step **experiences** (`#22`):
> - `life_experience_ids` — ids from `#76 GET /v1/catalog/life-experiences` only
> - `relationship_status` + `family_role_ids` — client-local enums (see `#76` rules); **do not** put these in `life_experience_ids`
> - `custom_experiences` — user-typed labels; API assigns `custom_*` slugs server-side
>
> Backend must **replace** all experience rows for the listener (delete then insert). Do **not** accept `custom_*` slugs from the client.

> **Avatar is not on this endpoint.** Use **#25b** `POST /v1/listeners/me/avatar` for photo upload (same pattern as **#26** voice intro).

---

### 25b. `POST /v1/listeners/me/avatar`

| | |
|--|--|
| **Auth** | Bearer (listener) |
| **Screen** | Listener profile tab — edit photo on header |
| **Content-Type** | `multipart/form-data` |
| **Body** | `avatar` (file) — `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`; max 5 MB |
| **Response** | Updated profile (#24) — includes new `avatar_url` |

#### Backend implementation reference

Mirror **#26** voice intro, but for images:

1. Accept `avatar: UploadFile = File(...)` on `POST /v1/listeners/me/avatar`.
2. Save under `uploads/avatars/` with filename `{listener_user_id}{suffix}`.
3. Store relative URL on profile, e.g. `/static/uploads/avatars/{user_id}.jpg`.
4. Return full `ListenerProfileResponse` wrapped in `{ status, data }`.

> **Do not** accept avatar multipart on `PATCH /v1/listeners/me` — that route is JSON-only (FastAPI `ListenerProfileUpdate` body).

#### Mobile implementation reference

- Repository: `POST v1/listeners/me/avatar` with `FormData` field `avatar`.
- Usecase: `UpdateListenerAvatarUsecase` → refresh profile via `GET /v1/listeners/me`.
- Resolve `avatar_url` with `resolveApiAssetUrl(url, baseUrl: appConfig.baseUrl)` in `listenerProfileFromApi()`.

---

### 26. `POST /v1/listeners/me/voice-intro`

| | |
|--|--|
| **Auth** | Bearer |
| **Screen** | Edit voice intro sheet |
| **Content-Type** | `multipart/form-data` |
| **Body** | `audio` (file, m4a/aac/mp3/wav/caf); optional `voice_intro_seconds` (int) |
| **Response** | `{ voice_intro_url, voice_intro_seconds }` |

**Media URL note:** `voice_intro_url` is relative like avatar; mobile prefixes with `baseUrl` before playback.

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
| **Response** | `{ profile_visible, show_online_status, visible_in_all_countries, visible_countries, allow_search_indexing }` |

**Fields**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `profile_visible` | bool | `true` | When `false`, listener is hidden from in-app discovery and browse |
| `show_online_status` | bool | `true` | Show online indicator to ventors |
| `visible_in_all_countries` | bool | `true` | When `false`, only `visible_countries` apply |
| `visible_countries` | string[] | `[]` | ISO 3166-1 alpha-2 codes; required (non-empty) when `visible_in_all_countries` is `false` |
| `allow_search_indexing` | bool | `true` | Allow public search-engine indexing of profile |

Profile information (languages, comfort areas, experience, boundaries) is **always shown** on the listener profile when `profile_visible` is `true` — not configurable via this endpoint.

**Example**

```json
{
  "status": "success",
  "data": {
    "profile_visible": true,
    "show_online_status": true,
    "visible_in_all_countries": true,
    "visible_countries": [],
    "allow_search_indexing": true
  }
}
```

---

### 34. `PUT /v1/listeners/me/privacy`

| | |
|--|--|
| **Auth** | Bearer |
| **Body** | Same fields as #33 (`visible_countries` = ISO codes[]) |
| **Response** | Updated privacy object |

**Validation**

- `400` if `visible_in_all_countries` is `false` and `visible_countries` is empty
- When `profile_visible` is `false`, `show_online_status` and country targeting are ignored server-side (listener hidden from app)

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
> - `#76` `GET /v1/catalog/life-experiences`
> - `#77` `GET /v1/catalog/boundaries`
> (Never use the mega dump.)

### 74. `GET /v1/catalog/categories` *(proposed)*

> **Status:** Proposed — ventor & listener registration topic picker from portal-managed `comfort_areas`.  
> **Purpose:** Return active interest / comfort categories for **both** ventor interests and listener comfort areas.  
> **DB source:** `comfort_areas` (ids used as `interest_ids` on ventor registration step `interests` and `comfort_area_ids` on listener registration step `comfort-areas`).  
> **Icons:** `icon_emoji` (like language `flag_emoji`) plus optional `icon_url` (CDN). Mobile does **not** map Material `icon_key`s.

| | |
|--|--|
| **Auth** | Public (Bearer accepted if present). Catalog is not secret. |
| **Screen** | Ventor registration → interests step; Listener registration → comfort areas step (step 5) |
| **When** | When step opens (and on error retry) |
| **Query** | Optional `locale` only — see below |
| **Response** | `{ items: Category[] }` |

#### Query parameters

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `locale` | `en` \| `ar` | no | from `Accept-Language` / `skel-accept-language` | Optional hint; response still includes **both** `name_en` and `name_ar` so the client can switch language without re-fetch. |

> **Mobile does not send `audience`.** Ventor and listener registration show the **same** active category list from this endpoint.

#### `Category` object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable slug PK — same value sent later in `#8` `interest_ids` |
| `name_en` | string | yes | English label |
| `name_ar` | string | yes | Arabic label |
| `icon_emoji` | string | yes | Unicode emoji for the leading icon (e.g. `❤️`) — mirrors `flag_emoji` on languages |
| `icon_url` | string \| null | no | Optional CDN image URL; mobile **prefers `icon_url` when non-empty**, else shows `icon_emoji` |
| `sort_order` | number | yes | Ascending; lower first |
| `allows_custom_text` | boolean | yes | `true` → show free-text field (e.g. `other`) |
| `topic_group` | string \| null | no | Optional grouping for admin / filters |

#### Success example

```http
GET /v1/catalog/categories
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
        "icon_emoji": "❤️",
        "icon_url": null,
        "sort_order": 10,
        "allows_custom_text": false,
        "topic_group": "relationships"
      },
      {
        "id": "marriage",
        "name_en": "Marriage",
        "name_ar": "الزواج",
        "icon_emoji": "💍",
        "icon_url": null,
        "sort_order": 20,
        "allows_custom_text": false,
        "topic_group": "relationships"
      },
      {
        "id": "parenting",
        "name_en": "Parenting",
        "name_ar": "الأبوة والأمومة",
        "icon_emoji": "👨‍👩‍👧",
        "icon_url": null,
        "sort_order": 30,
        "allows_custom_text": false,
        "topic_group": "family"
      },
      {
        "id": "career_work",
        "name_en": "Career & work",
        "name_ar": "المهنة والعمل",
        "icon_emoji": "💼",
        "icon_url": null,
        "sort_order": 40,
        "allows_custom_text": false,
        "topic_group": "work"
      },
      {
        "id": "stress_anxiety",
        "name_en": "Stress & anxiety",
        "name_ar": "التوتر والقلق",
        "icon_emoji": "😰",
        "icon_url": null,
        "sort_order": 50,
        "allows_custom_text": false,
        "topic_group": "mental"
      },
      {
        "id": "loneliness",
        "name_en": "Loneliness",
        "name_ar": "الوحدة",
        "icon_emoji": "😔",
        "icon_url": null,
        "sort_order": 60,
        "allows_custom_text": false,
        "topic_group": "mental"
      },
      {
        "id": "student_life",
        "name_en": "Student life",
        "name_ar": "حياة الطالب",
        "icon_emoji": "🎓",
        "icon_url": null,
        "sort_order": 70,
        "allows_custom_text": false,
        "topic_group": "life"
      },
      {
        "id": "financial_stress",
        "name_en": "Financial stress",
        "name_ar": "الضغط المالي",
        "icon_emoji": "💰",
        "icon_url": null,
        "sort_order": 80,
        "allows_custom_text": false,
        "topic_group": "money"
      },
      {
        "id": "health_wellness",
        "name_en": "Health & wellness",
        "name_ar": "الصحة والعافية",
        "icon_emoji": "🩺",
        "icon_url": null,
        "sort_order": 90,
        "allows_custom_text": false,
        "topic_group": "health"
      },
      {
        "id": "other",
        "name_en": "Other",
        "name_ar": "أخرى",
        "icon_emoji": "➕",
        "icon_url": null,
        "sort_order": 1000,
        "allows_custom_text": true,
        "topic_group": null
      }
    ]
  }
}
```

#### Seed notes

| `id` | `icon_emoji` (example) | `allows_custom_text` |
|------|------------------------|----------------------|
| `relationships` | ❤️ | `false` |
| `marriage` | 💍 | `false` |
| `parenting` | 👨‍👩‍👧 | `false` |
| `career_work` | 💼 | `false` |
| `stress_anxiety` | 😰 | `false` |
| `loneliness` | 😔 | `false` |
| `student_life` | 🎓 | `false` |
| `financial_stress` | 💰 | `false` |
| `health_wellness` | 🩺 | `false` |
| `other` | ➕ | `true` |

Mobile must **not** hardcode category labels or icons. Prefer `icon_url` when set; otherwise show `icon_emoji`; if both missing → generic placeholder.

#### Mobile usage

1. Open ventor interests step **or** listener comfort-areas step.
2. `GET /v1/catalog/categories` (no query params required).
3. Show shimmer list rows until response arrives.
4. Render `items` sorted by `sort_order`.
5. Localized label: `locale == ar ? name_ar : name_en`.
6. Leading icon: `icon_url` (network image) if non-empty, else `icon_emoji` (same pattern as language `flag_url` / `flag_emoji`).
7. If item has `allows_custom_text == true` and is selected → show free-text field; require non-empty trim before Continue/Finish.
8. Ventor Finish → `#8` with `interest_ids` (+ optional `other_interest_text`). Listener Continue → include selected ids in `#22` `comfort_area_ids`.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 500 | server | 500 | Unexpected failure |
| 503 | server | 503 | Catalog unavailable |

Empty active catalog → still `200` with `"items": []` (mobile shows empty + retry). Do **not** 404.

#### Rules

- Only return rows with `is_active = true`.
- IDs are immutable once shipped — changing an `id` breaks existing `ventor_interests` / `interest_ids`.
- Add/remove/reorder/edit emoji / upload icons via admin CMS (`/v1/admin/catalog/comfort-areas`); this public GET is read-only.
- Active rows should have a non-empty `icon_emoji` (and optionally `icon_url`).
- Cache-friendly: `Cache-Control: public, max-age=300` recommended (optional).

#### Acceptance criteria

- [ ] `GET /v1/catalog/categories` returns active rows with `icon_emoji`
- [ ] Standard `{ status, data: { items } }` envelope
- [ ] Both `name_en` and `name_ar` present
- [ ] `other` has `allows_custom_text: true`
- [ ] Inactive rows omitted
- [ ] Same `id` values accepted by `#8` `interest_ids`
- [ ] Portal can create/update categories, set `icon_emoji`, and optionally upload/replace `icon_url`
#### Link to register

| Step | API |
|------|-----|
| Load list | `#74 GET /v1/catalog/categories` |
| Submit profile + interests | `#8d PATCH /v1/ventors/register/steps/interests` with `interest_ids: ["relationships", "career_work", …]` |
| Submit listener comfort areas | `#22f PATCH /v1/listeners/register/steps/comfort-areas` with `comfort_area_ids: ["stress_anxiety", …]` |

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

### 76. `GET /v1/catalog/life-experiences` *(proposed)*

> **Status:** Proposed — listener registration life-experience chips.  
> **Purpose:** Return active life-experience tags from `life_experiences`.  
> **DB source:** `life_experiences` (`id`, `name_en`, `name_ar`, `sort_order`, `is_active`).  
> **Managed by:** Admin portal catalogs → Life experiences (`A51`).

| | |
|--|--|
| **Auth** | Public (Bearer accepted if present) |
| **Screen** | Listener registration → **Share your life experiences** (step 4) |
| **When** | Step open / retry after error |
| **Query** | `locale` optional (`en` \| `ar`) — hint only; response always includes both names |
| **Response** | `{ items: LifeExperience[] }` |

#### `LifeExperience` object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable slug PK — sent later in `#22` `life_experience_ids` |
| `name_en` | string | yes | English label |
| `name_ar` | string | yes | Arabic label |
| `sort_order` | number | yes | Ascending |

#### Success example

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "career_change",
        "name_en": "Career Change",
        "name_ar": "تغيير المسار المهني",
        "sort_order": 10
      },
      {
        "id": "job_loss",
        "name_en": "Jobless",
        "name_ar": "بلا عمل",
        "sort_order": 20
      },
      {
        "id": "grief_loss",
        "name_en": "Grief/Loss",
        "name_ar": "الفقدان / الحزن",
        "sort_order": 30
      },
      {
        "id": "anxiety_stress",
        "name_en": "Anxiety/Stress",
        "name_ar": "القلق / التوتر",
        "sort_order": 40
      },
      {
        "id": "financial_stress",
        "name_en": "Financial Stress",
        "name_ar": "ضغط مالي",
        "sort_order": 50
      },
      {
        "id": "life_stages",
        "name_en": "Life Stages",
        "name_ar": "مراحل الحياة",
        "sort_order": 60
      },
      {
        "id": "health_challenge",
        "name_en": "Health Challenge",
        "name_ar": "تحدٍ صحي",
        "sort_order": 70
      }
    ]
  }
}
```

#### Mobile usage

1. Open listener registration step 4.
2. `GET /v1/catalog/life-experiences`.
3. Show shimmer chips until response arrives.
4. Render `items` sorted by `sort_order`; label = `ar ? name_ar : name_en`.
5. Multi-select + optional custom free-text experiences (client-side) → `#22` `life_experience_ids` / `custom_experiences`.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 500 / 503 | server | … | Failure |

Empty → `200` + `items: []`. Do **not** 404.

#### Rules

- Only `is_active = true` rows.
- IDs immutable once shipped (breaks `listener_life_experiences`).
- Relationship status / family role remain **client-local** enums — not this catalog.
- `Cache-Control: public, max-age=300` recommended.

#### Acceptance

- [ ] Public `GET /v1/catalog/life-experiences` returns active rows only
- [ ] Standard `{ status, data: { items } }` envelope
- [ ] Both `name_en` and `name_ar` + `sort_order`
- [ ] Same `id`s accepted by `#22` `life_experience_ids`

---

### 77. `GET /v1/catalog/boundaries` *(proposed)*

> **Status:** Proposed — listener registration boundary picker.  
> **Purpose:** Return active boundary tags from `boundaries`.  
> **DB source:** `boundaries` (`id`, `name_en`, `name_ar`, `icon_emoji`, optional `icon_url`, `sort_order`, `is_active`).  
> **Managed by:** Admin portal catalogs → Boundaries (`A52`).

| | |
|--|--|
| **Auth** | Public (Bearer accepted if present) |
| **Screen** | Listener registration → **Select your Boundaries** (step 6) |
| **When** | Step open / retry after error |
| **Query** | Optional `locale` (`en` \| `ar`) — hint only; response includes both names |
| **Response** | `{ items: Boundary[] }` — see legacy note below |

> **Legacy shape (current Heroku):** `{ status, data: Boundary[] }` (array directly under `data`). Mobile accepts **both** `{ data: { items } }` and `{ data: [...] }`. New backends should use the standard `{ data: { items } }` envelope.

#### `Boundary` object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable slug PK — sent later in `#22` `boundary_ids` |
| `name_en` | string | yes | English label |
| `name_ar` | string | yes | Arabic label |
| `icon_emoji` | string | yes | Unicode emoji for the leading icon (e.g. `🛡️`) — same pattern as `#74` categories |
| `icon_url` | string \| null | no | Optional CDN image URL; mobile **prefers `icon_url` when non-empty**, else shows `icon_emoji`. Legacy field name `image_url` is accepted. |
| `sort_order` | number | yes | Ascending |
| `allows_custom_text` | boolean | no | default `false` — `true` for optional “Other” row with free text |

#### Success example

```http
GET /v1/catalog/boundaries
Accept-Language: en
```

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "suicide_self_harm",
        "name_en": "Suicide / Self-harm",
        "name_ar": "الانتحار / إيذاء النفس",
        "icon_emoji": "🛡️",
        "icon_url": null,
        "sort_order": 10,
        "allows_custom_text": false
      },
      {
        "id": "domestic_violence",
        "name_en": "Domestic violence",
        "name_ar": "العنف الأسري",
        "icon_emoji": "🏠",
        "icon_url": null,
        "sort_order": 20,
        "allows_custom_text": false
      },
      {
        "id": "sexual_topics",
        "name_en": "Sexual topics",
        "name_ar": "مواضيع جنسية",
        "icon_emoji": "👁️",
        "icon_url": null,
        "sort_order": 30,
        "allows_custom_text": false
      },
      {
        "id": "addiction",
        "name_en": "Addiction",
        "name_ar": "الإدمان",
        "icon_emoji": "💊",
        "icon_url": null,
        "sort_order": 40,
        "allows_custom_text": false
      },
      {
        "id": "politics",
        "name_en": "Politics",
        "name_ar": "السياسة",
        "icon_emoji": "🏛️",
        "icon_url": null,
        "sort_order": 50,
        "allows_custom_text": false
      },
      {
        "id": "religion",
        "name_en": "Religion",
        "name_ar": "الدين",
        "icon_emoji": "📖",
        "icon_url": null,
        "sort_order": 60,
        "allows_custom_text": false
      },
      {
        "id": "illegal_activities",
        "name_en": "Illegal activities",
        "name_ar": "أنشطة غير قانونية",
        "icon_emoji": "🚫",
        "icon_url": null,
        "sort_order": 70,
        "allows_custom_text": false
      }
    ]
  }
}
```

#### Seed notes

| `id` | `icon_emoji` |
|------|--------------|
| `suicide_self_harm` | 🛡️ |
| `domestic_violence` | 🏠 |
| `sexual_topics` | 👁️ |
| `addiction` | 💊 |
| `politics` | 🏛️ |
| `religion` | 📖 |
| `illegal_activities` | 🚫 |

Mobile must **not** hardcode boundary labels or icons. Prefer `icon_url` when set; otherwise show `icon_emoji`.

#### Mobile usage

1. Open listener registration step 6.
2. `GET /v1/catalog/boundaries`.
3. Show shimmer list rows until response arrives.
4. Render `items` sorted by `sort_order`; label = `ar ? name_ar : name_en`.
5. Multi-select optional (0+ boundaries) → `#22` `boundary_ids`.
6. If `allows_custom_text` item selected → require non-empty custom text before Continue.

#### Errors

| HTTP | type | code | When |
|------|------|------|------|
| 500 / 503 | server | … | Failure |

Empty → `200` + `items: []`. Do **not** 404.

#### Acceptance

- [ ] Public `GET /v1/catalog/boundaries` returns active rows only
- [ ] Standard `{ status, data: { items } }` envelope (or legacy array under `data` during migration)
- [ ] Both `name_en` and `name_ar` + non-empty `icon_emoji` per row
- [ ] Same `id`s accepted by `#22` `boundary_ids`

---

## Media URLs (static uploads)

Uploaded listener media (`avatar_url`, `voice_intro_url`, registration identity docs, etc.) is stored on disk and exposed as **relative** paths:

```
/static/uploads/avatars/{user_id}.jpg
/static/uploads/voice/{user_id}.m4a
```

| Client | Rule |
|--------|------|
| **Mobile** | Prefix with `AppConfig.baseUrl` when the value does not start with `http://` or `https://`. Helper: `lib/utils/api_asset_url.dart` → `resolveApiAssetUrl()`. Applied in `listenerProfileFromApi()` for `avatar_url` and `voice_intro_url`. |
| **Backend** | Continue returning relative paths in API JSON; static files are served from the app host under `/static/...`. |
| **Portal / admin** | Same prefix rule if rendering uploads in the browser. |

Catalog CDN assets (`flag_url`, category `icon_url`) are **absolute HTTPS** URLs — no prefix needed.

---

## Efficiency guidelines (for implementers)

1. **Prefer aggregates** — `#11` ventor home and `#32` listener dashboard load one screen in one round-trip.
2. **Prefer `PATCH` partial updates** — listener/ventor profile text fields via JSON `#25` / `#10`; do not re-send the whole profile for one field.
3. **Dedicated multipart routes for binaries** — listener avatar → `#25b`; listener voice → `#26`; ventor avatar → `#10` (multipart). Never JSON-encode file bytes.
4. **One discovery list** — `#40` carries filters; avoid separate endpoints per filter chip.
5. **Multipart only when needed** — avatar, ID docs, voice intro, registration photo.
6. **Pagination** — lists (`sessions`, `listeners`, `reviews`, `notifications`, `payouts`) should support `page` + `page_size`.
7. **Idempotent writes** — accept/decline/redeem/cancel should be safe to retry (`409` / clear status when already handled).

---

## Static / non-API URLs (not counted)

| URL | Use | 
|-----|-----|
| Static HTML (see below) | Terms / Privacy / Help (EN + AR) — opened in WebView |
| `mailto:support@venting.app` | Support email |
| WhatsApp `wa.me` | Support / share |

### Static legal & help pages *(not REST — no server API round-trip for metadata)*

Ship **6** static files under one shared `webContentBaseUrl` for both flavors:

`https://venting-3a5ebaed4621.herokuapp.com`

Source HTML lives in [`docs/static-web/`](./static-web/README.md).

| Page | EN | AR |
|------|----|----|
| Terms of Service | `/legal/en/terms.html` | `/legal/ar/terms.html` |
| Privacy Policy | `/legal/en/privacy.html` | `/legal/ar/privacy.html` |
| Help & Support | `/help/en/index.html` | `/help/ar/index.html` |

Mobile picks locale from the app language and opens the matching URL (Help tiles append `#fragment` anchors on the same help page). **No** `GET /v1/legal/*` or `GET /v1/help/*` endpoints.

| Reset password (EN) | `/auth/en/reset-password.html?token=…` |
| Reset password (AR) | `/auth/ar/reset-password.html?token=…` |

Password reset pages are opened from the **email link** (browser / OS), not from an in-app REST metadata call. APIs: `#2b` forgot-password · `#2c` reset-password.

---

## Endpoint count

| Category | Count |
|----------|------:|
| Auth & account | 8 |
| Ventor profile / home / wellness | 14 |
| Listener profile / onboarding / dashboard | 16 |
| Listener availability | 3 |
| Discovery & sessions | 13 |
| Call feedback & reports | 3 |
| Earnings & payouts | 7 |
| Rewards & invites | 5 |
| Notifications | 3 |
| Training | 2 |
| Promo | 1 |
| Catalog / categories | 4 |
| **Total unique API endpoints** | **82** |

### Master checklist (method + path)

| # | Method | Path |
|---|--------|------|
| 0 | POST | `/v1/auth/check-email` *(proposed)* |
| 1 | POST | `/v1/auth/register` |
| 2 | POST | `/v1/auth/login` |
| 2b | POST | `/v1/auth/forgot-password` *(proposed)* |
| 2c | POST | `/v1/auth/reset-password` *(proposed)* |
| 1b | POST | `/v1/auth/social` *(proposed)* |
| 3 | POST | `/v1/auth/refresh` |
| 4 | POST | `/v1/auth/logout` |
| 5 | DELETE | `/v1/auth/account` |
| 6 | POST | `/v1/auth/change-password` |
| 7 | GET | `/v1/auth/me` |
| 8a | GET | `/v1/ventors/register/progress` |
| 8b | PATCH | `/v1/ventors/register/steps/profile` |
| 8c | PATCH | `/v1/ventors/register/steps/languages` |
| 8d | PATCH | `/v1/ventors/register/steps/interests` |
| 8e | POST | `/v1/ventors/register/complete` |
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
| 22a | GET | `/v1/listeners/register/progress` |
| 22b | PATCH | `/v1/listeners/register/steps/profile` |
| 22c | PATCH | `/v1/listeners/register/steps/identity` |
| 22d | PATCH | `/v1/listeners/register/steps/about` |
| 22e | PATCH | `/v1/listeners/register/steps/experiences` |
| 22f | PATCH | `/v1/listeners/register/steps/comfort-areas` |
| 22g | PATCH | `/v1/listeners/register/steps/boundaries` |
| 22h | PATCH | `/v1/listeners/register/steps/voice-intro` |
| 22i | PATCH | `/v1/listeners/register/steps/availability` |
| 22j | POST | `/v1/listeners/register/complete` |
| 23 | POST | `/v1/listeners/me/identity-verification` |
| 24 | GET | `/v1/listeners/me` |
| 25 | PATCH | `/v1/listeners/me` |
| 25b | POST | `/v1/listeners/me/avatar` |
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
| 76 | GET | `/v1/catalog/life-experiences` *(proposed)* |
| 77 | GET | `/v1/catalog/boundaries` *(proposed)* |

---

## Final count

**Total unique API endpoints: 92**

**Live / wired in the mobile app today: 0** (auth + catalog clients exist; backend contracts still proposed where marked). Static legal/help HTML is separate from this REST count.

---

*Generated from screen models, mock catalogs, and `TODO: … API` markers across `lib/presentation` (auth, ventor home/sessions/rewards/profile/call, listener dashboard/sessions/earnings/availability/profile/call/registration).*
