# Venting — Catalog Categories Backend Requirements

> **Status:** Proposed.  
> **Companion to:** [`api-endpoints.md`](./api-endpoints.md) §12 `#74` · [`api-usage-guide.md`](./api-usage-guide.md) B1 · [`database-schema.md`](./database-schema.md) `comfort_areas`  
> **Audience:** Backend engineers seeding and exposing ventor/listener interest categories.

---

## 1. Goal

Replace the **hardcoded** interest list in `VentorRegistrationInterestsStep` with a catalog API so product/admin can add, rename, reorder, or disable categories without an app release.

Mobile flow:

1. Ventor opens registration interests step  
2. `GET /v1/catalog/categories?audience=ventor`  
3. User selects categories  
4. `POST /v1/ventors/register` with `interest_ids` matching catalog `id`s  

---

## 2. Endpoint

### `GET /v1/catalog/categories`

| | |
|--|--|
| **Auth** | Public (Bearer optional) |
| **Query** | `audience` = `ventor` \| `listener` \| `all` (default `all`) |
| **Success** | `{ "status": "success", "data": { "items": [ Category, ... ] } }` |

### Category fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Immutable slug; PK in `comfort_areas` |
| `name_en` | string | yes | |
| `name_ar` | string | yes | |
| `icon_key` | string | yes | See icon contract in api-endpoints `#74` |
| `sort_order` | number | yes | Ascending |
| `allows_custom_text` | boolean | yes | `true` for `other` |
| `topic_group` | string \| null | no | Optional |

---

## 3. Database (`comfort_areas`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(64) PK | slug |
| `name_en` | VARCHAR(120) | |
| `name_ar` | VARCHAR(120) | |
| `icon_key` | VARCHAR(64) | |
| `sort_order` | INT | default 0 |
| `allows_custom_text` | BOOLEAN | default false |
| `audience` | VARCHAR(32) | `ventor` \| `listener` \| `all` |
| `topic_group` | VARCHAR(64) | nullable |
| `is_active` | BOOLEAN | default true |

Filter: `is_active = true` AND (`audience` matches query OR `audience = 'all'`).

---

## 4. Seed data (v1 — matches current mobile UI)

| id | name_en | icon_key | sort_order | allows_custom_text | audience |
|----|---------|----------|------------|--------------------|----------|
| relationships | Relationships | favorite | 10 | false | ventor |
| marriage | Marriage | favorite_border | 20 | false | ventor |
| parenting | Parenting | family_restroom | 30 | false | ventor |
| career_work | Career & work | work_outline | 40 | false | ventor |
| stress_anxiety | Stress & anxiety | psychology_alt | 50 | false | ventor |
| loneliness | Loneliness | person_outline | 60 | false | ventor |
| student_life | Student life | school | 70 | false | ventor |
| financial_stress | Financial stress | attach_money | 80 | false | ventor |
| health_wellness | Health & wellness | health_and_safety | 90 | false | ventor |
| other | Other | add_circle_outline | 1000 | **true** | ventor |

Provide accurate `name_ar` for each row (see example JSON in `api-endpoints.md` `#74`).

---

## 5. Register contract (`#8`)

`interest_ids` must be a subset of active catalog ids for `audience=ventor`.

```json
{
  "nickname": "QuietFox",
  "gender": "male",
  "avatar_preset_index": 1,
  "interest_ids": ["relationships", "other"],
  "other_interest_text": "Optional when other is selected"
}
```

Validation:

- Reject unknown ids → `400 validation`
- If `other` in `interest_ids` and `allows_custom_text`, require non-empty `other_interest_text` (**require trim length ≥ 2**)
- Persist into `ventor_interests (ventor_id, comfort_area_id, custom_text?)`

---

## 6. Errors

| HTTP | type | code | When |
|------|------|------|------|
| 400 | validation | 740 | Invalid `audience` |
| 500 / 503 | server | … | Failure / unavailable |

Empty catalog → `200` + `items: []`.

---

## 7. Acceptance

- [x] Seed table populated with v1 rows  
- [x] `GET /v1/catalog/categories?audience=ventor` returns active ventor rows sorted by `sort_order`  
- [x] `#8` accepts those ids as `interest_ids`  
- [x] Inactive rows never returned  
- [ ] Mobile interests step loads from API (no hardcoded list)

---

## 8. Out of scope (v1)

- Admin CRUD UI (planned under `/v1/admin/catalog/…`)  
- Image/icon URLs (use `icon_key` only)  
- Pagination (list is small; return all active)
