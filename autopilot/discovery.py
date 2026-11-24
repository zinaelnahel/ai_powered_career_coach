"""Free, read-only job discovery and ranking. No paid API or submission."""
import json
import os
import re
from urllib.request import urlopen
from urllib.parse import quote, urlsplit
from pathlib import Path

def tokens(s):
    return set(re.findall(r"[a-z0-9+#]+", s.lower()))

def rank(job, roles, skills):
    title = tokens(job["title"])
    body = tokens(job["title"] + " " + job.get("description", ""))
    role = max((len(title & tokens(r)) / max(1, len(tokens(r))) for r in roles), default=0)
    skill = len(body & tokens(" ".join(skills))) / max(1, len(tokens(" ".join(skills))))
    return round(100 * (.7 * role + .3 * skill))

def fetch(url):
    with urlopen(url, timeout=20) as response:
        return json.load(response)

def discover(boards):
    for board in boards:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", board):
            raise ValueError("Invalid board identifier")
        data = fetch("https://boards-api.greenhouse.io/v1/boards/" + quote(board) + "/jobs?content=true")
        for item in data.get("jobs", []):
            url = item.get("absolute_url", "")
            if urlsplit(url).scheme != "https":
                continue
            yield dict(id=f"greenhouse:{board}:{item['id']}", title=item["title"],
                       location=item.get("location", {}).get("name", ""),
                       url=url, description=item.get("content", ""))

def run(config):
    roles = config["roles"]
    skills = config.get("skills", [])
    locations = config.get("locations", [])
    results = {}
    for board in config["greenhouse_boards"][:20]:
        try:
            for job in discover([board]):
                if locations and not any(x.casefold() in job["location"].casefold() for x in locations):
                    continue
                score = rank(job, roles, skills)
                if score >= config.get("minimum_score", 60):
                    job.pop("description", None)
                    results[job["id"]] = dict(job, score=score, status="review_required")
        except (OSError, ValueError, KeyError):
            print("A job source failed; continuing.")
    return sorted(results.values(), key=lambda j: -j["score"])[:50]

if __name__ == "__main__":
    raw = os.environ.get("AUTOPILOT_CONFIG")
    if not raw:
        raise SystemExit("Configure AUTOPILOT_CONFIG before running.")
    result = run(json.loads(raw))
    Path("autopilot-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Found {len(result)} reviewable matches. No applications submitted.")
