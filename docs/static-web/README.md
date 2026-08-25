# Venting static web content

One base URL for **dev and prod** (Heroku):

`https://venting-3a5ebaed4621.herokuapp.com`

## Legal & help (6 pages)

| Page | Full URL |
|------|----------|
| Terms EN | …/legal/en/terms.html |
| Terms AR | …/legal/ar/terms.html |
| Privacy EN | …/legal/en/privacy.html |
| Privacy AR | …/legal/ar/privacy.html |
| Help EN | …/help/en/index.html |
| Help AR | …/help/ar/index.html |

## Password reset (email link → browser)

| Page | Path |
|------|------|
| Reset EN | `/auth/en/reset-password.html?token={rawToken}` |
| Reset AR | `/auth/ar/reset-password.html?token={rawToken}` |

Flow:

1. Mobile `#2b POST /v1/auth/forgot-password` with `{ email, role, locale }`
2. Backend emails a one-time link to the locale page above
3. Page calls `#2c POST /v1/auth/reset-password` with `{ token, password }`

See [`api-endpoints.md`](../api-endpoints.md) §§2b–2c and email requirements below.

### Email requirements (backend)

- Subject (EN): `Reset your Venting password`
- Subject (AR): `إعادة تعيين كلمة مرور Venting`
- HTML body: dark Venting branding (`#0A0614` / accent `#8A3CFE`), clear CTA button “Reset password” / “إعادة التعيين”
- CTA href: `{base}/auth/{locale}/reset-password.html?token={rawToken}`
- Mention 60-minute expiry; do not include the raw password
- From address: something like `noreply@venting.app`

### Security

- Store only `token_hash` in `password_reset_tokens`
- Single-use + TTL 60m
- Same success response whether or not the email exists
