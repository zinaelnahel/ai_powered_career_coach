# Career Dojo

An AI career-practice project by **Zina El Nahel**. Built with React, Bootstrap and Flask, with a Ninja Turtles-inspired dojo theme.

[Open the app](https://ai-powered-career-coach-dojo.vercel.app) ? [LinkedIn](https://www.linkedin.com/in/zina-el-nahel) ? [Implementation walkthrough](APP_WALKTHROUGH.md)

## What it does

- **Mock interviews:** 3, 5 or 8 questions, contextual follow-ups, optional browser dictation and complete/partial-session feedback.
- **CV review:** paste text or upload PDF, DOCX or TXT; receive evidence-based advice and exact source excerpts.
- **Career Lab:** find jobs, compare CV evidence with an offer, build a learning plan and research a company.
- **My journey:** save reviewed STAR stories, revisit feedback, track practice milestones and export/delete saved data.
- **Demo mode:** explore without an API key. Outputs are labelled illustrative and rewards measure practice, not employability.

## Run locally

Requires Python 3.12+; Node.js 22+ is needed to rebuild the frontend.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npm run build
Copy-Item .env.example .env  # Only if .env does not already exist.
python app.py
```

Open **http://127.0.0.1:5000**. Compiled frontend assets are included, so Node is optional when only running the existing build. Optional workspace conveniences in `.vendor` and `.tools` are not required for a fresh installation.

Edit `.env` for live AI; never commit it or put credentials in frontend code.

| Setting | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Server-side key for live AI and web research; leave empty for demo use. |
| `OPENAI_MODEL` | Model configured for generation; default is shown in `.env.example`. |
| `APP_PASSWORD` | Optional shared access password; not per-user accounts. |
| `HOST`, `PORT` | Local server address; defaults to `127.0.0.1:5000`. |

For frontend development, run `npm run dev` alongside Flask. Restart Flask after backend changes.

## Structure

| Location | Responsibility |
| --- | --- |
| `frontend/` | React rooms, shared dojo artwork, browser memory and styles. |
| `app.py` | Flask, uploads, interview/CV routes, provider client and request validation. |
| `career_features.py` | Job discovery, fit analysis, roadmaps and company preparation. |
| `job_links.py`, `job_locations.py` | Bounded public-HTTPS source checks, workplace evidence and application-URL deduplication. |
| `content_quality.py`, `review_grounding.py` | Evidence consistency, partial matches, proposal status and conservative CV advice. |
| `learning_scope.py` | Bounded exercises, matching learning resources and CV-based rehearsal. |
| `company_facts.py`, `company_identities.json` | First-party identity/value checks and dated identity references. |
| `coaching.py`, `local_config.py` | Extractive STAR recovery and local configuration loading. |
| `tests/` | Backend regressions and isolated Chrome checks. |

`static/index.html` loads the esbuild output in `public/static`. There is no account database or agent framework.

## Privacy and limitations

Live analysis sends submitted text to OpenAI. Saved work is browser-specific and is removed when browser data is cleared. Job results require source links and location evidence; work authorization is not assessed. Scores are subjective guidance, not hiring predictions. Upload and testing limitations apply.

## Verify changes

```powershell
python -m unittest discover -s tests
npm run build
python tests/browser_smoke.py
python tests/browser_audit_quality.py
python tests/browser_multitab.py
python tests/browser_accessibility.py
```

Browser checks need Playwright (`python -m pip install playwright`) and installed Chrome. Each command above starts its own local test server and uses an isolated browser profile. Additional suites cover memory, dictation and feedback quality. `browser_dojo.py` expects a server already running on port 5050. Tests are targeted regression evidence, not a complete external audit.

## Deploy

Configure server environment variables in Vercel, then deploy with `npx vercel --prod` from the linked project. Vercel builds the React bundle and serves Flask. Local `.env` changes do not update production settings. Dependencies, secrets, tests and local artifacts are excluded from deployment by `.vercelignore` and `vercel.json`.

## Theme notice

Independent, noncommercial bootcamp project inspired by Teenage Mutant Ninja Turtles. Not affiliated with or endorsed by the rights holders. Illustrations drawn in SVG for this project.
