# Venting static web content (6 pages)

Source of truth for Terms, Privacy, and Help HTML. Host these files at the
**site root** of `webContentBaseUrl` (no API required).

| Locale | Path | App usage |
|--------|------|-----------|
| EN | `legal/en/terms.html` | Terms WebView |
| AR | `legal/ar/terms.html` | Terms WebView |
| EN | `legal/en/privacy.html` | Privacy WebView |
| AR | `legal/ar/privacy.html` | Privacy WebView |
| EN | `help/en/index.html` | Help & Support (+ `#anchors`) |
| AR | `help/ar/index.html` | Help & Support (+ `#anchors`) |

## Flavors

| Flavor | `webContentBaseUrl` | Example Terms EN |
|--------|---------------------|------------------|
| Dev | `https://dev.venting.app` | `https://dev.venting.app/legal/en/terms.html` |
| Prod | `https://venting.app` | `https://venting.app/legal/en/terms.html` |

## Deploy

Copy the `legal/` and `help/` folders from this directory to your static host
(nginx, CDN, object storage website). Keep paths exactly as above.

Help tiles open the same HTML with fragments, e.g. `help/en/index.html#getting-started`.

## Editing

Edit the HTML here, redeploy static files — **no mobile app release** and **no
backend API** for legal/help links.
