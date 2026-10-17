"""Emails the Library's maintainer about a submission, through Resend.

Run by .github/workflows/notify.yml for two events:

- pull_request_target (opened, reopened): "New Library submission: <title>"
- workflow_run of check.yml (completed): "Library check passed/failed: <title>"

It reads only the event and GitHub's API, and never checks out or runs the
submitted code. Needs RESEND_API_KEY and NOTIFY_EMAIL (Actions secrets); without
them it says so and exits cleanly. DRY_RUN=1 prints the email instead of sending.
"""

from __future__ import annotations

import html
import json
import os
import sys
import urllib.request
from typing import Any

SENDER = "linuxlive Library <onboarding@resend.dev>"
UA = "linuxlive-library-notify"


def api(path: str) -> Any:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.load(res)


def pull_for_run(repo: str, run: dict) -> dict | None:
    """The pull request a check run belongs to: the one whose head is the very
    commit the run checked. GitHub often leaves the run's pull_requests list
    empty (always for forks), and a branch like add-<slug> is reused for every
    update, so the commit is the only unambiguous key."""
    sha = run.get("head_sha")
    for listed in run.get("pull_requests") or []:
        pr = api(f"/repos/{repo}/pulls/{listed['number']}")
        if pr["head"]["sha"] == sha:
            return pr
    owner = (run.get("head_repository") or {}).get("owner", {}).get("login")
    branch = run.get("head_branch")
    if not owner or not branch:
        return None
    for pr in api(f"/repos/{repo}/pulls?state=all&head={owner}:{branch}&per_page=20"):
        if pr["head"]["sha"] == sha:
            return pr
    return None


def distros_in(repo: str, number: int) -> list[str]:
    files = api(f"/repos/{repo}/pulls/{number}/files?per_page=100")
    slugs = {f["filename"].split("/")[1] for f in files if f["filename"].startswith("distros/") and f["filename"].count("/") >= 2}
    return sorted(slugs)


def compose(event_name: str, event: dict, repo: str) -> dict | None:
    """The email for this event, or None when there is nothing to say."""
    if event_name == "pull_request_target":
        pr = event["pull_request"]
        verb = "Reopened" if event.get("action") == "reopened" else "New"
        subject = f"{verb} Library submission: {pr['title']}"
        lead = f"{pr['user']['login']} opened a pull request in the Library. Its check is building and boot-testing it now; another email follows when it finishes."
        result = None
    elif event_name == "workflow_run":
        run = event["workflow_run"]
        if run.get("event") != "pull_request":
            return None
        conclusion = run.get("conclusion")
        if conclusion not in ("success", "failure", "timed_out"):
            return None  # cancelled (a newer push replaces it), skipped, and so on
        pr = pull_for_run(repo, run)
        if not pr:
            return None
        passed = conclusion == "success"
        subject = f"Library check {'passed' if passed else 'failed'}: {pr['title']}"
        lead = ("It built and passed its boot tests, so it is ready for your review."
                if passed else "Its check failed. The author may push a fix; the run shows what went wrong.")
        result = (passed, run["html_url"])
    else:
        return None

    number = pr["number"]
    slugs = distros_in(repo, number)
    body = (pr.get("body") or "").strip()
    if len(body) > 600:
        body = body[:600].rstrip() + "…"
    e = html.escape
    rows = [
        ("Pull request", f'<a href="{e(pr["html_url"])}">#{number}: {e(pr["title"])}</a>'),
        ("Author", f'<a href="https://github.com/{e(pr["user"]["login"])}">{e(pr["user"]["login"])}</a>'),
        ("Distro folder", e(", ".join(f"distros/{s}/" for s in slugs) or "none")),
    ]
    if result:
        rows.append(("Check", f'<a href="{e(result[1])}">{"passed" if result[0] else "failed"}</a>'))
    html_body = (
        f"<p>{e(lead)}</p>"
        + "<table cellpadding=\"4\">"
        + "".join(f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in rows)
        + "</table>"
        + (f"<p><strong>Description</strong></p><blockquote>{e(body).replace(chr(10), '<br>')}</blockquote>" if body else "")
        + f'<p><a href="{e(pr["html_url"])}/files">Review the files</a></p>'
    )
    text_body = "\n".join([lead, "", *(f"{k}: {html.unescape(_strip(v))}" for k, v in rows), "", pr["html_url"]])
    return {"subject": subject, "html": html_body, "text": text_body}


def _strip(fragment: str) -> str:
    out, inside = [], False
    for ch in fragment:
        if ch == "<":
            inside = True
        elif ch == ">":
            inside = False
        elif not inside:
            out.append(ch)
    return "".join(out)


def send(mail: dict, to: str, key: str) -> None:
    payload = json.dumps({"from": SENDER, "to": [to], "subject": mail["subject"], "html": mail["html"], "text": mail["text"]}).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        print(f"sent: {mail['subject']} ({json.load(res).get('id')})")


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        event = json.load(f)
    repo = os.environ.get("GITHUB_REPOSITORY", "Eric-Ness/linuxlive-library")
    mail = compose(event_name, event, repo)
    if not mail:
        print("nothing to send for this event")
        return 0
    if os.environ.get("DRY_RUN") == "1":
        print(json.dumps(mail, indent=2))
        return 0
    key, to = os.environ.get("RESEND_API_KEY"), os.environ.get("NOTIFY_EMAIL")
    if not key or not to:
        print("RESEND_API_KEY or NOTIFY_EMAIL is not set; no email sent")
        return 0
    send(mail, to, key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
