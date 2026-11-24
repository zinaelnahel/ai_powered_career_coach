# Autopilot — phase 1
Free discovery prototype, no paid APIs. Uses public Greenhouse postings and deterministic keyword matching (not AI). No application is submitted. No CV or personal details are needed.

Run locally with Python 3.12:
Set AUTOPILOT_CONFIG to JSON such as:
```json
{"roles":["Python Developer"],"skills":["Python","SQL"],"locations":["Berlin","Remote"],"greenhouse_boards":["example"],"minimum_score":60}
```
Replace example with real employer board identifiers. Run python -m autopilot.discovery. Results are written to autopilot-results.json; do not commit this file. Run python -m unittest discover -s autopilot/tests for tests.

Cloud: after review and merge, configure repository secret AUTOPILOT_CONFIG and variable AUTOPILOT_ENABLED=true. The workflow runs every four hours on public repositories using standard hosted runners. It currently only reports the count; results are ephemeral on the runner. No personal data should be entered in configuration. Disable the variable to pause. Verify GitHub terms and free usage before enabling; schedules may be delayed or disabled. No paid runners or services are configured.

Remaining: private persistent storage, authenticated dashboard, CV tailoring, approved application adapters, submission verification, notifications and end-to-end testing. Do not enable unattended submissions until these are implemented and verified.
