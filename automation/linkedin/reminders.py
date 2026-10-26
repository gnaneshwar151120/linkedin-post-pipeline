"""Daily checks. Run by .github/workflows/linkedin-reminders.yml.

- 6 PM ET the evening before a Tue/Thu slot: issue if that slot has no approved post
- token expiring within 7 days (repo variable LINKEDIN_TOKEN_EXPIRES_AT): issue
"""
import datetime as dt
import os

from posts import ET, SLOT_DAYS, SLOT_HOUR, drafts, fmt

TOKEN_WARN = dt.timedelta(days=7)


def issue(title, body):
    with open(os.environ.get("ISSUES_FILE", "/dev/null"), "a") as f:
        f.write(f"{title}\t{body}\n")


def check_tomorrow(now):
    tomorrow = (now + dt.timedelta(days=1)).replace(hour=SLOT_HOUR, minute=0, second=0, microsecond=0)
    if tomorrow.weekday() not in SLOT_DAYS or now.hour != 18:
        return
    posts = [p for p in drafts() if p.publish_at == tomorrow]
    approved = [p for p in posts if p.status == "approved"]
    if approved:
        print(f"tomorrow {fmt(tomorrow)}: approved ({approved[0].folder.name})")
        return
    what = f"draft `{posts[0].folder.name}` is not approved" if posts else "no post is scheduled"
    issue(f"LinkedIn: {tomorrow:%a %Y-%m-%d} post not approved",
          f"Tomorrow's {fmt(tomorrow)} ET slot: {what}. Set `status: approved` in its post.md, "
          "or the slot is skipped.")
    print(f"tomorrow {fmt(tomorrow)}: NOT approved, issue queued")


def check_token(now):
    raw = os.environ.get("LINKEDIN_TOKEN_EXPIRES_AT")
    if not raw:
        issue("LinkedIn token: expiry unknown", "Run `python3 automation/linkedin/authorize.py` locally.")
        return
    expires = dt.datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    left = expires - now
    print(f"token expires {raw} ({left.days} days)")
    if left <= TOKEN_WARN:
        issue(f"LinkedIn token expires {expires:%Y-%m-%d}",
              f"Access token expires in {max(left.days, 0)} days. Re-authorize (about 1 min): run "
              "`python3 automation/linkedin/authorize.py` in your clone of this repo.")


if __name__ == "__main__":
    now = dt.datetime.now(ET)
    check_tomorrow(now)
    check_token(now)
