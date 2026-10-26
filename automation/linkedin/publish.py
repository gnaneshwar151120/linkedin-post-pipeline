"""Publish approved posts whose slot has arrived. Run by .github/workflows/linkedin-publish.yml.

- approved + publish_at <= now (within GRACE)  -> post, move folder to published/, record url
- approved but the slot passed > GRACE ago      -> roll to the next free Tue/Thu 9:00 ET slot
- failure                                       -> attempts += 1; on the 2nd failure status=failed + GitHub issue
Prints one line per action; writes ISSUE lines to $ISSUES_FILE for the workflow to open issues.
"""
import datetime as dt
import os
import shutil
from pathlib import Path

from linkedin_api import LinkedInError, from_env, post_url
from posts import ET, PUBLISHED, drafts, fmt, next_slot

GRACE = dt.timedelta(hours=2)
MAX_ATTEMPTS = 2


def issue(title, body):
    with open(os.environ.get("ISSUES_FILE", "/dev/null"), "a") as f:
        f.write(f"{title}\t{body.replace(chr(10), ' ')}\n")


def main():
    now = dt.datetime.now(ET)
    posts = drafts()
    taken = {p.publish_at for p in posts if p.publish_at}
    due = [p for p in posts if p.status == "approved" and p.publish_at and p.publish_at <= now]
    if not due:
        print("nothing due")
        return
    client = None
    for p in due:
        if now - p.publish_at > GRACE:
            new = next_slot(now, taken)
            taken.add(new)
            print(f"rescheduled {p.folder.name}: {fmt(p.publish_at)} -> {fmt(new)} (slot missed)")
            p.meta["publish_at"] = fmt(new)
            p.save()
            continue
        client = client or from_env()
        try:
            urn = client.create_post(p.body, p.media, alt=p.meta.get("alt", ""))
        except LinkedInError as e:
            attempts = int(p.meta.get("attempts") or 0) + 1
            p.meta["attempts"] = str(attempts)
            p.meta["error"] = str(e)[:300].replace("\n", " ")
            if attempts >= MAX_ATTEMPTS:
                p.meta["status"] = "failed"
                issue(f"LinkedIn post failed: {p.folder.name}",
                      f"Post `{p.folder.name}` failed {attempts} times. Last error: {e}. "
                      "Fix it, set status back to approved and a new publish_at.")
            print(f"FAILED {p.folder.name} (attempt {attempts}): {e}")
            p.save()
            continue
        p.meta.update(status="published", url=post_url(urn), published_at=now.strftime("%Y-%m-%d %H:%M"))
        p.meta.pop("error", None)
        p.save()
        dest = PUBLISHED / p.folder.name
        PUBLISHED.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p.folder), str(dest))
        print(f"published {p.folder.name}: {post_url(urn)}")


if __name__ == "__main__":
    main()
