# FX Journal Dashboard

Self-hosted reproduction of the fxjournalstats embed panels, built from your own
Notion **TRADES DB**. Renders with Chart.js, hosted free on GitHub Pages, refreshed
on a schedule by a GitHub Action that reads the Notion API.

## Panels

Embed each in Notion with a query param:

| Panel | URL |
|-------|-----|
| Calendar  | `https://<user>.github.io/<repo>/?panel=calendar` |
| Time      | `https://<user>.github.io/<repo>/?panel=time` |
| Risk      | `https://<user>.github.io/<repo>/?panel=risk` |
| Discipline| `https://<user>.github.io/<repo>/?panel=discipline` |

## How data flows

```
Notion TRADES DB  --(Notion API, token kept as repo secret)-->  GitHub Action
        ^                                                              |
        | you log trades                                               v
   (source of truth)                                  data.json committed to repo
                                                                       |
                                                                       v
                                            GitHub Pages serves index.html + data.json
                                                                       |
                                                                       v
                                                  Notion embed blocks render the panels
```

The Notion token is **never** shipped to the browser — only the Action uses it.

## Setup

1. Create a repo and push these files.
2. Repo **Settings → Secrets and variables → Actions** → add:
   - `NOTION_TOKEN` — your Notion integration token
   - `NOTION_DB_ID` — the trades database id
3. Repo **Settings → Pages** → Source: `Deploy from a branch`, branch `main`, folder `/ (root)`.
4. **Actions** tab → run *Refresh data from Notion* once (workflow_dispatch).
5. Paste the panel URLs above as embeds in Notion.

## Local preview

```bash
NOTION_TOKEN=... NOTION_DB_ID=... python scripts/fetch_data.py
python -m http.server 8765
# open http://localhost:8765/?panel=calendar
```

## Notes / metric definitions

- **Consistency Score** = % of profitable trading days.
- **Recovery Factor** = net P/L ÷ |max drawdown|.
- **Risk/Reward** = avg win ÷ |avg loss|.
- **Drawdown** = running equity minus running peak (trade order).
- Tag charts sum P/L over every trade carrying each tag.
- Empty/placeholder rows (no Date or no Profit/Loss) are skipped.
