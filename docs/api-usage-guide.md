# Venting Mobile — API Usage Guide

> **Companion to:** [`api-endpoints.md`](./api-endpoints.md) · [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md)  
> **Purpose:** Describe every REST API and **exactly where in the app** to call it.  
> **Audience:** Mobile engineers wiring screens to the backend.

This guide is organized by **user journey and screen**, not by raw endpoint number. For request/response shapes, see the master spec.

---

## Conventions (read once)

| Rule | Detail |
|------|--------|
| Base URL | `String.fromEnvironment('BASE_URL')` |
| Auth | Public endpoints need no token; everything else sends `Authorization: Bearer {accessToken}` |
| Errors | Match `MainAPIException` (`status: failed` + `error`) |
| Success | Prefer `{ status: "success", data: { … } }` |
| Roles | Call **ventor** APIs only as a ventor; **listener** APIs only as a listener (except shared session join/end/report) |

**When to call `#0 POST /v1/auth/check-email` *(proposed)*:** Email auth step — after user enters email, before password. Branch Create account vs Sign in. Does not authenticate.

**When to call `#7 GET /v1/auth/me`:** Splash / app shell bootstrap — decide route (onboarding vs home) and role before showing tabs. Also after `#1` / `#2` / `#1b` success.

**When to call `#1b POST /v1/auth/social` *(proposed)*:** AuthScreen — after native Google/Apple Sign-In returns an ID token. Optionally after `#0 check-email` when email is available (role mismatch UX). Full backend spec: [`social-auth-backend-requirements.md`](./social-auth-backend-requirements.md).

**When to call `#3 POST /v1/auth/refresh`:** Silently in the Dio interceptor when a Bearer call returns 401 and a refresh token exists — not from a visible screen.

---

## Part A — Shared auth & account

Use these for **both** ventor and listener unless a screen is role-specific.

| # | Endpoint | Where to use it | When to call |
|---|----------|-----------------|--------------|
| 0 *(proposed)* | `POST /v1/auth/check-email` | Email auth step (after AuthScreen → email) | User finishes email; before password — branch register vs login |
| 7 | `GET /v1/auth/me` | Splash · shell bootstrap | App launch / cold start / after `#1` or `#2` to route the user |
| 3 | `POST /v1/auth/refresh` | Dio / auth interceptor (background) | Access token expired; rotate tokens |
| 1 | `POST /v1/auth/register` | Email registration (create account) | Submit email + password + role when `#0` returns `exists: false` (or without `#0`) |
| 2 | `POST /v1/auth/login` | Email sign-in | Submit credentials when `#0` returns `exists: true` |
| 1b *(proposed)* | `POST /v1/auth/social` | AuthScreen (Google / Apple buttons) | After native sign-in; send `provider`, `id_token`, `role`; then `#7` for routing |
| 4 | `POST /v1/auth/logout` | Ventor profile settings · Listener profile settings | User taps Log out; clear local tokens after success |
| 5 | `DELETE /v1/auth/account` | Delete account confirm screen | User confirms permanent deletion |
| 6 | `POST /v1/auth/change-password` | Listener change password screen | User submits current + new password |

**Routing hints from `#0` *(proposed)*:**

- `exists == false` → Create account UI → `#1 register`
- `exists == true` → Sign-in UI → `#2 login`
- Welcome `role` ≠ account `role` → show mismatch error; do not register/login
- `registration_complete` / `listener_profile_status` on `#0` are **hints only** — final routing uses `#7` after auth

**Social auth flow (AuthScreen → `#1b`):**

1. User taps Continue with Google or Apple on AuthScreen (ventor or listener path).
2. Native SDK returns `id_token` (+ email on first Apple auth).
3. If email is available → `#0 check-email` with `{ email, role }` — block on role mismatch.
4. `#1b social` with `{ provider, id_token, role, nonce?, full_name? }`.
5. Persist tokens → `#7 me` → same routing as email auth (ventor/listener registration, under_review, home).

**Routing hints from `#7`:**

- `registration_complete == false` → continue role registration
- Listener with `listener_profile_status`: `incomplete` → registration; `under_review` / `rejected` → status screen; `approved` → listener home

---

## Part B — Ventor flows

### B1. First-time ventor setup

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 75 *(proposed)* | `GET /v1/catalog/languages` | Ventor registration → **language step** | On step open — load speaking languages from **`languages`** table (`flag_url`, native + English names). Same catalog as listener languages — no second table. |
| 74 *(proposed)* | `GET /v1/catalog/categories?audience=ventor` | Ventor registration → **interests step** | On step open — load categories (`id`, localized name, **`icon_url`**). Do **not** hardcode labels or icons. |
| 8 | `POST /v1/ventors/register` | Ventor registration (nickname, gender, avatar, languages, interests) | Final submit — `language_ids` + `interest_ids` + optional `other_interest_text` when “Other” is selected |

> **Never call** `GET /v1/catalog` (combined dump). Use `#74` / `#75` only.

**Ventor onboarding steps:**

1. Profile (nickname / gender / avatar)  
2. `#75` speaking language(s) from `languages` — ≥1 required; flags are CDN URLs managed in the portal  
3. `#74` interest categories from `comfort_areas` — icons are CDN URLs managed in the portal  
4. `#8` submit all (creates ventor profile; sets `registration_complete`)

**Languages flow:**

1. Step opens → `#75` load languages (portal-managed `languages` rows).
2. User multi-selects (≥1); search filters client-side for v1.
3. Continue → keep `language_ids` for `#8`.

**Interests flow:**

1. Step opens → `#74` load categories.
2. User selects one or more.
3. If a selected category has `allows_custom_text` (e.g. `other`) → show free-text field; require non-empty trim.
4. Leading image per row = `icon_url` from backend.
5. Finish → `#8` with:
   - profile fields (nickname, gender, avatar / preset)
   - `language_ids`
   - `interest_ids`
   - `other_interest_text` **only when** Other (or another custom-text category) is selected

**`#8` “Other” interest contract:**

| Selected | Body |
|----------|------|
| `interest_ids` includes `other` | Must include `other_interest_text` (trimmed, non-empty) |
| No custom-text category | Omit `other_interest_text` |

### B2. Ventor home & wellness

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| **11** | `GET /v1/ventors/me/home` | **Ventor dashboard / home tab** | On tab open / pull-to-refresh — **prefer this single call** for greeting, streak, mood today, upcoming + recent sessions |
| 12 | `POST /v1/ventors/me/mood-checkins` | Mood check-in sheet | User picks a mood (and optional note) and saves |
| 13 | `GET /v1/ventors/me/mood-journey` | Ventor profile — mood journey card | When profile (or that card) is shown; query `days` (default 7) |

### B3. Ventor profile, favorites, achievements

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 9 | `GET /v1/ventors/me` | Ventor profile tab | Load profile header, stats, interests |
| 10 | `PATCH /v1/ventors/me` | Edit ventor profile sheet | Save nickname / avatar / quote |
| 14 | `GET /v1/ventors/me/favorites` | Profile — “My listeners” | Load favorite listeners list |
| 15 | `POST /v1/ventors/me/favorites/{listenerId}` | Listener profile / find card heart | User favorites a listener |
| 16 | `DELETE /v1/ventors/me/favorites/{listenerId}` | Same UI (unfavorite) | User removes favorite |
| 17 | `GET /v1/ventors/me/achievements` | Achievements bottom sheet | Sheet opens |

### B4. Ventor settings

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 18 | `GET /v1/ventors/me/privacy` | Ventor privacy settings | Screen open |
| 19 | `PUT /v1/ventors/me/privacy` | Same | User toggles privacy flags and saves |
| 20 | `GET /v1/ventors/me/notification-preferences` | Ventor notification preferences | Screen open |
| 21 | `PUT /v1/ventors/me/notification-preferences` | Same | User changes reminder / push / email prefs |

### B5. Find listeners & book sessions

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 40 | `GET /v1/listeners` | Ventor sessions tab — **Find** | Search, filter chips, pagination (`q`, topic, price, languages, genders, rating, favorites, online_only) |
| 28 | `GET /v1/listeners/{listenerId}` | Ventor listener profile screen | Open a specific listener’s public card |
| 41 | `POST /v1/sessions/instant-match` | “Surprise me” / instant match | User wants an auto-matched listener |
| 73 | `POST /v1/promo/validate` | Before connecting — checkout | User enters a promo code; validate before pay |
| 42 | `POST /v1/sessions` | Before connecting → pay & book | Confirm booking (instant / nearest / scheduled, voice/video, voice change, promo, reward offer) |

### B6. Ventor sessions list & cancel

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 43 | `GET /v1/ventors/me/sessions` | Booked sessions list (+ home upcoming if not using #11 alone) | Filter by `status`: upcoming / live / completed / cancelled |
| 44 | `GET /v1/ventors/me/sessions/{sessionId}` | Booked session details | Open one session |
| 45 | `POST /v1/ventors/me/sessions/{sessionId}/cancel` | Cancel booked session | User cancels; expect full refund to balance in UI |

### B7. Call, rate, report (ventor)

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 51 | `POST /v1/sessions/{sessionId}/join` | Enter call (ventor side) | Immediately before connecting to VoIP (token + channel) |
| 52 | `POST /v1/sessions/{sessionId}/end` | Leave / hang up | Call ends; optional `ended_by` + `duration_seconds` |
| 53 | `POST /v1/sessions/{sessionId}/rating` | Ventor call rating screen | After call: stars, optional review, tip ($2/$5/$10), optional inline report |
| 55 | `POST /v1/sessions/{sessionId}/reports` | Call report sheet | Standalone report if not sent inside #53 |

### B8. Rewards & invites

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 63 | `GET /v1/ventors/me/rewards` | Rewards tab | Load points, offers, earn rules, welcome gift state |
| 64 | `POST /v1/ventors/me/rewards/redeem` | Rewards tab — redeem CTA | User trades points for an offer |
| 65 | `GET /v1/ventors/me/rewards/trades` | Trade history | Open history list |
| 66 | `GET /v1/ventors/me/invites` | Invite friends / invite history | Load code, link, invitees, points |
| 67 | `POST /v1/ventors/me/invites/refresh-code` | Invite friends (optional) | User regenerates invite code |

**Pass `reward_offer_id` on `#42`** when booking with an active redeemed offer from #63/#64.

---

## Part C — Listener flows

### C1. Listener registration & verification

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 22 | `POST /v1/listeners/register` | Listener registration steps 1–9 | Prefer **one submit at the end** (all steps); field map matches steps (profile, ID, about, experiences, comfort, boundaries, voice, availability, notifications) |
| 23 | `POST /v1/listeners/me/identity-verification` | Step 2 or re-verify | Upload document front/back + selfie; or resubmit after rejection |

### C2. Listener dashboard & setup

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| **32** | `GET /v1/listeners/me/dashboard` | **Listener dashboard tab** | On open / refresh — aggregate: setup, impact, next session, online flag, reminder |
| 29 | `GET /v1/listeners/me/setup-progress` | Dashboard setup checklist (if not enough from #32) | Show step statuses |
| 30 | `POST /v1/listeners/me/setup/first-session-tutorial` | First-session tutorial | User acknowledges tutorial |
| 31 | `PATCH /v1/listeners/me/online-status` | Dashboard online/available toggle | User goes online/offline |

### C3. Availability

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 37 | `GET /v1/listeners/me/availability` | Availability tab | Load week schedule + instant/session/break settings |
| 38 | `PUT /v1/listeners/me/availability` | Same — save all settings | Persist full object (session length, break, languages, instant, week) |
| 39 | `PUT /v1/listeners/me/availability/days/{day}` | Day schedule bottom sheet | Edit slots for one day (`mon`…`sun`) |

### C4. Listener sessions & requests

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 46 | `GET /v1/listeners/me/sessions` | Listener sessions tab | `filter`: upcoming / missed / history |
| 47 | `GET /v1/listeners/me/session-stats` | Sessions stats card | Load accepted / declined / missed counts |
| 48 | `GET /v1/listeners/me/session-requests` | Pending requests UI | List incoming requests |
| 49 | `POST /v1/listeners/me/session-requests/{requestId}/accept` | Request card — Accept | Instant: first accept wins; handle `already_taken` |
| 50 | `POST /v1/listeners/me/session-requests/{requestId}/decline` | Request card — Decline | Optional reason |

### C5. Call, feedback, report (listener)

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 51 | `POST /v1/sessions/{sessionId}/join` | Enter call (listener) | Same as ventor — get call token |
| 52 | `POST /v1/sessions/{sessionId}/end` | Hang up | Same as ventor |
| 54 | `POST /v1/sessions/{sessionId}/feedback` | Listener call rating | After call: stars + `felt_heard` + `talk_again` |
| 55 | `POST /v1/sessions/{sessionId}/reports` | Listener call report sheet | Report ventor with listener reason codes |

### C6. Listener profile & edits

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 24 | `GET /v1/listeners/me` | Listener profile tab + settings | Load full private profile |
| 25 | `PATCH /v1/listeners/me` | Edit about / city / phone / experiences / comfort / boundaries / country / languages | Save any partial edit |
| 26 | `POST /v1/listeners/me/voice-intro` | Edit voice intro sheet | Upload new m4a/aac intro |
| 27 | `GET /v1/listeners/me/reviews` | Profile reviews bottom sheet | Paginated reviews |

### C7. Listener privacy & notifications prefs

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 33 | `GET /v1/listeners/me/privacy` | Privacy & visibility | Screen open |
| 34 | `PUT /v1/listeners/me/privacy` | Same | Save visibility / country targeting |
| 35 | `GET /v1/listeners/me/notification-preferences` | Listener notification preferences | Screen open |
| 36 | `PUT /v1/listeners/me/notification-preferences` | Same | Save prefs |

### C8. Earnings & payouts

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 56 | `GET /v1/listeners/me/earnings` | Earnings tab summary | Totals, tier, sessions, hours, rating |
| 57 | `GET /v1/listeners/me/earnings/chart` | Earnings chart | Date range `from` / `to` |
| 58 | `GET /v1/listeners/me/payout-balances` | Payment & payouts | Available / pending / lifetime |
| 59 | `GET /v1/listeners/me/payout-methods` | Payment methods list | Load bank / PayPal methods |
| 60 | `PUT /v1/listeners/me/payout-methods` | Add/edit bank (or PayPal) | Save method |
| 61 | `GET /v1/listeners/me/payouts` | Payout history | List past payouts |
| 62 | `POST /v1/listeners/me/payouts` | Request payout | Submit amount + method id |

### C9. Notifications inbox

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 68 | `GET /v1/listeners/me/notifications` | Listener notifications list | Open inbox; optional `unread_only` |
| 69 | `POST /v1/listeners/me/notifications/read-all` | Mark all read action | User clears unread |
| 70 | `DELETE /v1/listeners/me/notifications/{notificationId}` | Swipe/delete one notification | User dismisses one item |

### C10. Training

| # | Endpoint | Screen / place | When |
|---|----------|----------------|------|
| 71 | `GET /v1/listeners/me/training` | Training bottom sheet | Load modules + `all_completed` |
| 72 | `POST /v1/listeners/me/training/{moduleId}/complete` | After finishing a module | Mark complete; may unlock setup progress |

Module ids: `art_of_listening`, `empathy`, `boundaries`, `difficult_situations`, `crisis_awareness`.

---

## Part D — Screen → API cheat sheet

### Splash / auth

| Screen | APIs |
|--------|------|
| Splash / bootstrap | `#7` |
| Email auth — email step *(proposed)* | `#0` → branch UI |
| Register | `#0` (optional) → `#1` → `#7` → role register `#8` or `#22` if incomplete |
| Login | `#0` (optional) → `#2` → `#7` |
| Token refresh | `#3` (interceptor) |
| Logout | `#4` |
| Delete account | `#5` |
| Change password | `#6` |

### Ventor tabs

| Screen | Primary APIs |
|--------|----------------|
| Home | `#11` (+ `#12` from mood sheet) |
| Sessions — Find | `#40`, `#41`, `#28`, `#42`, `#73` |
| Sessions — Booked | `#43`, `#44`, `#45` |
| Rewards | `#63`, `#64`, `#65`, `#66`, `#67` |
| Profile | `#9`, `#10`, `#13`, `#14`, `#15`/`#16`, `#17`, `#18`/`#19`, `#20`/`#21`, `#4`, `#5` |
| Call | `#51`, `#52`, `#53`, `#55` |

### Listener tabs

| Screen | Primary APIs |
|--------|----------------|
| Dashboard | `#32`, `#29`, `#30`, `#31`, `#71`/`#72` |
| Sessions | `#46`, `#47`, `#48`, `#49`, `#50` |
| Availability | `#37`, `#38`, `#39` |
| Earnings | `#56`, `#57`, `#58`, `#59`, `#60`, `#61`, `#62` |
| Profile | `#24`, `#25`, `#26`, `#27`, `#33`/`#34`, `#35`/`#36`, `#4`, `#5`, `#6` |
| Notifications | `#68`, `#69`, `#70` |
| Call | `#51`, `#52`, `#54`, `#55` |
| Registration | `#22`, `#23` |

---

## Part E — Recommended call order (happy paths)

### Email auth (with `#0` proposed)

1. Welcome → pick role (`ventor` \| `listener`)
2. AuthScreen → Continue with email
3. `#0` check-email → branch UI (Create account vs Sign in)
4. `#1` register **or** `#2` login (password submit)
5. `#7` auth/me → route (home / role registration / listener status)

### Ventor: cold start → book → call → rate

1. `#7` auth/me  
2. If incomplete → `#8` ventors/register  
3. Home → `#11`  
4. Find → `#40` (or `#41` surprise) → `#28` detail  
5. Checkout → `#73` (if promo) → `#42` book  
6. At call time → `#51` join → (VoIP) → `#52` end → `#53` rate  

### Listener: cold start → go online → accept → call → feedback

1. `#7` auth/me (+ profile status)  
2. If incomplete → `#22` (+ `#23` if needed)  
3. Dashboard → `#32`  
4. Availability → `#37` / `#38` / `#39` as needed  
5. Go online → `#31`  
6. Requests → `#48` → `#49` or `#50`  
7. Join → `#51` → `#52` → `#54`  

### Listener: earn & cash out

1. `#56` + `#57` for summary/chart  
2. `#58` balances → `#59` methods → `#60` if adding method  
3. `#62` request payout → `#61` history  

---

## Part F — Efficiency rules (when *not* to call)

| Prefer | Avoid |
|--------|--------|
| `#11` ventor home | Many separate calls for streak + upcoming + recent on first paint |
| `#32` listener dashboard | Separate setup + impact + next session calls for first paint |
| `#40` with query filters | One endpoint per filter chip |
| `#25` / `#10` PATCH partial | Re-uploading the whole profile for one field |
| Multipart only for files | JSON for avatars/voice/ID when binary is required |

Lists that should paginate: listeners (`#40`), sessions (`#43`/`#46`), reviews (`#27`), notifications (`#68`), payouts (`#61`).

Treat accept / decline / redeem / cancel as **idempotent**: safe to retry; handle “already done” (`already_taken`, `409`, etc.).

---

## Part G — Non-API URLs (do not invent REST for these)

| URL / action | Where |
|--------------|--------|
| Terms / Privacy WebViews | Registration & settings links |
| Help center articles | Help / support screens |
| `mailto:support@venting.app` | Contact support |
| WhatsApp `wa.me` | Support or share |

---

## Quick role matrix

| Domain | Ventor uses | Listener uses |
|--------|:-----------:|:-------------:|
| Auth `#1–7` | ✓ | ✓ |
| Ventor profile/home `#8–21` | ✓ | — |
| Listener profile/onboarding `#22–36` | `#28` only (public card) | ✓ |
| Availability `#37–39` | — | ✓ |
| Discovery & sessions `#40–52` | `#40–45`, `#51–52` | `#46–52` |
| Feedback `#53–55` | `#53`, `#55` | `#54`, `#55` |
| Earnings `#56–62` | — | ✓ |
| Rewards `#63–67` | ✓ | — |
| Notifications `#68–70` | — | ✓ (inbox as specified) |
| Training `#71–72` | — | ✓ |
| Promo `#73` | ✓ | — |

---

## Endpoint count

**73** unique REST endpoints — full contracts in [`api-endpoints.md`](./api-endpoints.md).

*Usage mapping derived from the proposed screen audit and presentation-layer TODO markers.*
