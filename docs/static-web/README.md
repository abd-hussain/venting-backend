# Venting static web content (6 pages)

Served by the backend at **one** `webContentBaseUrl` for all app flavors
(dev + prod). Source: this folder. Live paths: `/legal/…`, `/help/…`.

**Base URL:** `https://venting-3a5ebaed4621.herokuapp.com`

| Locale | Path | Full URL |
|--------|------|----------|
| EN | `legal/en/terms.html` | `https://venting-3a5ebaed4621.herokuapp.com/legal/en/terms.html` |
| AR | `legal/ar/terms.html` | `https://venting-3a5ebaed4621.herokuapp.com/legal/ar/terms.html` |
| EN | `legal/en/privacy.html` | `https://venting-3a5ebaed4621.herokuapp.com/legal/en/privacy.html` |
| AR | `legal/ar/privacy.html` | `https://venting-3a5ebaed4621.herokuapp.com/legal/ar/privacy.html` |
| EN | `help/en/index.html` | `https://venting-3a5ebaed4621.herokuapp.com/help/en/index.html` |
| AR | `help/ar/index.html` | `https://venting-3a5ebaed4621.herokuapp.com/help/ar/index.html` |

Help tiles append fragments on the same page, e.g.  
`https://venting-3a5ebaed4621.herokuapp.com/help/en/index.html#getting-started`

## Editing

Edit HTML here, push/deploy the backend — **no separate static host** and **no
mobile app release**.
