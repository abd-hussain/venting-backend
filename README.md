# Venting Backend

FastAPI backend for the **Venting** mobile app — a two-sided product where:

- **Ventors** seek emotional support (home, discovery, sessions, mood journey, rewards, invites)
- **Listeners** offer paid listening sessions (onboarding, availability, dashboard, earnings, training)

This API is the contract the Flutter app will call once mocks are replaced. Today the mobile client has a Dio stack and `MainAPIException` parsing, but **0 live HTTP endpoints** wired to screens — this repo implements that contract.

---

## Specs (source of truth)

Keep these open while implementing. Do not invent paths, fields, or tables that contradict them.

| Document | What it defines | Use it when… |
|----------|-----------------|--------------|
| [**docs/api-endpoints.md**](docs/api-endpoints.md) | **73** HTTP endpoints, auth mode, request/response shapes, envelopes, efficiency rules | Adding or changing any route, schema, or status code |
| [**docs/database-schema.md**](docs/database-schema.md) | **43** PostgreSQL tables, enums, indexes, ER relationships, API↔table map | Adding models, migrations, queries, or money/ledger logic |

### How we use them day to day

1. Pick an endpoint from the **master checklist** in `api-endpoints.md` (e.g. `#2 POST /v1/auth/login`).
2. Find the matching **tables** in the API↔tables map at the bottom of `database-schema.md`.
3. Implement in a domain package under `app/api/v1/<domain>/` (`router` → `service` → `models`/`db`).
4. Return the **standard success envelope** or raise **`MainAPIException`**-shaped errors (both docs + mobile client expect this).
5. Prefer aggregates, `PATCH` partial updates, pagination, and idempotent writes as listed in the API efficiency guidelines.

If mobile UI and these docs disagree, **update the docs first**, then the backend — the Flutter app was designed against this contract.

---

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI + Uvicorn |
| Language | Python 3.11+ (local venv may be newer) |
| Database | PostgreSQL 15+ (per schema doc) |
| Auth | Bearer access token + refresh tokens |
| Deploy | `Procfile` → `uvicorn app.main:app` |

---

## Quick start

```bash
cd venting_backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install "fastapi[all]"        # quote extras on zsh

uvicorn app.main:app --reload
```

- API docs (Swagger): http://127.0.0.1:8000/docs  
- Health probe: `GET /`  
- Versioned API prefix: `/v1`  
- Demo error shape: `GET /demo/error`

---

## Response contract

Matches Flutter `MainAPIException` / recommended success envelope in the API spec.

**Success**

```json
{ "status": "success", "data": { } }
```

**Error**

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

In code:

```python
from app.core.responses import success_response
from app.core.errors import invalid_credentials

return success_response({"access_token": "..."})
raise invalid_credentials()
```

Shared conventions from the API spec:

- `Content-Type: application/json; charset=UTF-8`
- Auth: `Authorization: Bearer {accessToken}`
- Dates: ISO-8601 UTC
- Money: USD `number`, 2 decimal places (DB: `NUMERIC(12,2)`)
- IDs: strings in JSON (DB: UUID PKs)

---

## Project layout

```
venting_backend/
├── app/
│   ├── main.py                 # create_app() — wiring only
│   ├── api/
│   │   ├── deps.py             # shared Depends (auth, db, settings)
│   │   └── v1/
│   │       ├── router.py       # mounts domain routers under /v1
│   │       ├── health.py
│   │       └── auth/           # template domain package
│   │           ├── router.py   # HTTP only
│   │           ├── schemas.py  # request/response models
│   │           └── service.py  # business logic
│   ├── core/                   # config, envelopes, MainAPIException, handlers
│   ├── schemas/envelope.py     # shared success/error models only
│   ├── db/                     # engine / sessions
│   ├── models/                 # ORM (map to docs/database-schema.md)
│   └── services/               # shared infra (email, storage, …)
├── docs/
│   ├── api-endpoints.md        # ← HTTP contract (73 endpoints)
│   └── database-schema.md      # ← data model (43 tables)
├── static/
├── Procfile
└── README.md
```

Cursor rules in `.cursor/rules/` encode the same architecture and API conventions for agents.

---

## Domains (API ↔ code ↔ DB)

Implement one domain package at a time. Register each router in `app/api/v1/router.py`.

| Domain | API sections (endpoints) | Primary tables (schema doc) | Suggested package |
|--------|--------------------------|-----------------------------|-------------------|
| Auth & account | 1–7 | `users`, `refresh_tokens` | `api/v1/auth/` |
| Ventors | 8–21, rewards/invites 63–67 | `ventor_profiles`, mood, favorites, achievements, settings | `api/v1/ventors/` |
| Listeners | 22–36, availability 37–39 | `listener_profiles`, identity, tags, settings | `api/v1/listeners/` |
| Sessions / discovery | 40–55 | `session_requests`, `sessions`, payments, ratings, reports | `api/v1/sessions/` |
| Earnings & payouts | 56–62 | wallets, ledger, `payout_methods`, `payouts` | `api/v1/earnings/` |
| Notifications | 68–70 | `notifications` | `api/v1/notifications/` |
| Training | 71–72 | `training_modules`, progress | `api/v1/training/` |
| Promo | 73 | `promo_codes`, `promo_redemptions` | `api/v1/promo/` |

Lookups (`languages`, `comfort_areas`, …) are seeded catalogs — see schema doc §3.

---

## Suggested implementation order

Aligned with mobile flows and foreign-key dependencies:

1. **Auth** — register / login / refresh / me (`users`, `refresh_tokens`)
2. **Profiles** — ventor + listener register & `me` (+ lookups seed)
3. **Availability & discovery** — slots + `GET /v1/listeners`
4. **Sessions** — request → accept/decline → join/end → pay
5. **Feedback & reports** — ratings, listener feedback, reports
6. **Earnings & payouts** — wallet ledger (append-only), payouts
7. **Rewards, invites, notifications, training, promo**

For each endpoint: **spec → tables → model → service → router → envelope**.

---

## Layering rules

| Layer | Responsibility |
|-------|----------------|
| `router.py` | Validate input, call service, `success_response` / raise `MainAPIException` |
| `service.py` | Business rules; no FastAPI `Request`/`Response` |
| `models/` | Persistence matching `database-schema.md` |
| `core/` | Cross-cutting only (config, errors, handlers) |

Do not put domain schemas in `app/schemas/` — only shared envelopes live there.

---

## Configuration

Settings live in `app/core/config.py` (`pydantic-settings`). Use a local `.env` (gitignored), for example:

```env
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/v1
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/venting
# JWT_SECRET=change-me
```

---

## Related repos

| Repo | Role |
|------|------|
| `venting_mobile_app` | Flutter client; parses `MainAPIException`; screens still mostly mocked |
| `venting_backend` (this) | HTTP API + PostgreSQL |

Mobile API base URL: `String.fromEnvironment('BASE_URL')` pointing at this service.

---

## Status

| Area | State |
|------|--------|
| Project scaffold + response envelopes | Done |
| Domain routers beyond health / auth stub | In progress |
| DB models & migrations (43 tables) | Not started — follow `docs/database-schema.md` |
| Endpoint coverage vs 73 | Track against master checklist in `docs/api-endpoints.md` |
