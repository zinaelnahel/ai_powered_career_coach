# Career Dojo: implementation walkthrough

A short guide to explaining the build. For setup, deployment and limitations, see [README](README.md).

## 1. Follow one request

```text
React form -> same-origin API -> Flask validation
  demo: illustrative rules
  live: server-side OpenAI call -> parsed and validated output
React result -> browser memory, when enabled
```

`frontend/main.jsx` owns navigation and the shared request/error handling. `app.py` serves the frontend and implements the provider client. Credentials stay on the server. Ordinary calls request JSON-object output; research calls require web search and retain retrieved-source metadata. Validation checks structure and selected evidence, not universal factual truth.

## 2. Interview and CV review

**Interview:** React sends the current transcript to `/api/interview`. Flask checks alternating turns and the requested 3/5/8-question count. Each response is either one next question or a validated feedback report. Early finishes are labelled partial. Drafts and completed transcripts can be reopened. `content_quality.grounded_interview` keeps explicit proposed methods from being credited as past experience through targeted qualification and source spans.

**CV:** `/api/extract` reads PDF/DOCX/TXT into memory, enforces limits and normalizes extracted text. `/api/review` generates advice and exact CV bullet bases. `review_grounding.py` and source-excerpt checks reject unsupported replacements and added outcomes. The model sees text, so it cannot assess the original visual layout. `Dictation.jsx` uses browser speech recognition for interview text, with typing as the fallback.

## 3. Trace the Career Lab handoffs

`frontend/CareerLab.jsx` connects four tools:

| Route | Main checks and handoff |
| --- | --- |
| `/api/jobs` | Retrieved detail URLs, geography, closed pages and final-application deduplication; sourced ATS pages can be recovered when omitted from the generated shortlist. |
| `/api/fit` | Exact CV evidence, English-level consistency and partial skill coverage. K6 performance evidence alone cannot establish broader functional API testing. |
| `/api/roadmap` | Sequential weeks, valid hours, topic-specific small exercises, observable completion checks and curated documentation links. |
| `/api/company-prep` | First-party identity, qualified employer/country context, substantive values and transparent culture-page retrieval results. |

A selected job carries source text and its URL into fit analysis, with completeness confirmation. Results save the analyzed input snapshot; edits hide the old score and learning-plan action. A fit result transfers its narrower gaps into a roadmap. Company preparation passes verified identity and CV-based practice questions into interview setup, not unverified benefits. CV context for rehearsal stays out of company web research.

`job_links.py` uses bounded HTTPS fetching and public-address checks. It retains the original source and final application target. `job_locations.py` requires explicit workplace evidence; a company office or the word Remote does not establish eligibility.

## 4. Explain the quality modules

- `content_quality.py`: plain citation text, interview proposal status, English evidence and narrow/partial fit categories. Corrected categories do not silently recalculate a model score.
- `learning_scope.py`: bounded mobile, API, mocking, resilience and language exercises, including setup time and honest tooling-blocker fallbacks. `career_features.learning_resources` prioritizes the learning objective over incidental keywords.
- `company_facts.py`: retrieved first-party identity quotations, expiring dated references and culture-page checks. Button/navigation labels are not values; supporting sources are separated from background research.
- `coaching.py`: exact-source STAR fields. If generated fields fail the evidence guard, explicit responsibility/action sentences are recovered, drafting instructions are excluded and unsupported results stay blank. The user must review the story before saving.

These are focused safeguards around a fallible model. They do not replace checking the original CV, offer or employer source.

## 5. State, theme and rewards

`frontend/memory.js` coordinates browser saves, tab-specific workspace state, shared history, preference changes and deletion. It uses browser locks where available to avoid overwriting another tab's changes. Saved work has no automatic cross-device synchronization or server session database.

`DojoOverview.jsx` derives practice points and rewards from saved activity. Reversing a milestone or deleting an activity reverses its contribution. Demo activity counts as practice, not validated skill. `CareerMemory.jsx` handles goals, reviewed stories and data controls.

`DojoArt.jsx`, `DojoIcons.jsx` and `CharacterGuide.jsx` share the theme: Splinter as mentor; Leonardo for interviews, Raphael for CV review, Donatello for Career Lab and Michelangelo for My journey. `About.jsx` includes Zina El Nahel, LinkedIn, privacy details and the project notice.

## 6. Build, test, deploy

1. `scripts/build.mjs` bundles React/CSS/fonts into `public/static`; Flask serves `static/index.html`.
2. Backend tests cover validation, evidence, source filtering, fit consistency, story recovery and workload/resource alignment.
3. Isolated Chrome suites check complete workflows, stale results, downloads, reloads, tab independence and sampled accessibility.
4. Deploy the tested source through Vercel with server-side environment variables; perform targeted production checks afterward.

The external audits drive regression examples, not a claim of exhaustive coverage. Real mobile devices, real dictation, assistive technology, broad security review and systematic AI-quality evaluation remain explicit coverage limits.
