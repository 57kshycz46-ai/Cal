# Homework → Fantastical calendar sync

Pulls pending assignments from a Notion "Homework" database and publishes
them as a public `.ics` feed via GitHub Pages, refreshed hourly by a
GitHub Action. Subscribe to the feed URL from Fantastical (or any calendar
app) to keep it live-updating without any paid service.

## One-time setup

1. **Create a Notion integration**
   - Go to https://www.notion.so/my-integrations → **New integration**
   - Give it a name (e.g. "Homework Calendar Sync"), associate it with
     your workspace, save.
   - Copy the **Internal Integration Secret** — this is your `NOTION_TOKEN`.

2. **Share the Homework database with the integration**
   - Open the Homework database in Notion → `...` menu (top right) →
     **Connections** → add the integration you just created.

3. **Push these files to a new public GitHub repo**, keeping this exact
   folder structure:
   ```
   generate_ics.py
   requirements.txt
   README.md
   .github/workflows/sync-homework-calendar.yml
   ```

4. **Add repo secrets** — Settings → Secrets and variables → Actions →
   New repository secret:
   - `NOTION_TOKEN` = the integration secret from step 1
   - `NOTION_DATABASE_ID` = the Homework database ID

5. **Enable GitHub Pages** — Settings → Pages → Source: "Deploy from a
   branch" → Branch: `main`, Folder: `/docs` → Save.

6. **Run the workflow once manually** — Actions tab → "Sync Homework
   Calendar" → Run workflow. This generates `docs/homework.ics` for the
   first time so Pages has something to serve.

7. **Subscribe in Fantastical** — Settings → Calendars & Lists → `+` →
   Add Subscription → paste:
   `https://<your-github-username>.github.io/<repo-name>/homework.ics`

From then on, the Action re-runs every hour, regenerates the feed from
whatever is currently in Notion, and commits it back to the repo — no
manual steps needed. This is a **one-way** feed (Notion → Fantastical);
editing/checking off events in Fantastical doesn't write back to Notion.
