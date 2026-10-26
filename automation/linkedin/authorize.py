"""One-time (and every ~60 days) LinkedIn authorization.

Run locally:  python3 automation/linkedin/authorize.py
Needs LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET in the environment and `gh` logged in.
Run it from your clone of this repo; set GITHUB_REPO=owner/name to target a different one.
Opens your browser, catches the redirect on localhost:8765, then stores the token as GitHub secrets.
The token is never printed or written to disk.
"""
import datetime as dt
import http.server
import json
import os
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

REPO = os.environ.get("GITHUB_REPO")  # default: the repo of the current directory
REDIRECT = "http://localhost:8765/callback"
SCOPES = "openid profile w_member_social"


def main():
    cid = os.environ.get("LINKEDIN_CLIENT_ID")
    secret = os.environ.get("LINKEDIN_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET first (see docs/linkedin-app-setup.md).")

    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] != state:
                result["error"] = "state mismatch"
            elif "error" in q:
                result["error"] = q.get("error_description", q["error"])[0]
            else:
                result["code"] = q.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = "Authorized. You can close this tab." if "code" in result else f"Failed: {result.get('error')}"
            self.wfile.write(f"<h2>{msg}</h2>".encode())

        def log_message(self, *a):
            pass

    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT, "state": state, "scope": SCOPES})
    server = http.server.HTTPServer(("localhost", 8765), Handler)
    print("Opening LinkedIn in your browser… (if it doesn't open, visit this URL)\n" + auth_url)
    webbrowser.open(auth_url)
    while not result:
        server.handle_request()
    if "error" in result:
        sys.exit(f"Authorization failed: {result['error']}")

    data = urllib.parse.urlencode({"grant_type": "authorization_code", "code": result["code"],
                                   "redirect_uri": REDIRECT, "client_id": cid, "client_secret": secret}).encode()
    with urllib.request.urlopen("https://www.linkedin.com/oauth/v2/accessToken", data=data) as r:
        tok = json.load(r)
    token, expires_in = tok["access_token"], int(tok["expires_in"])

    req = urllib.request.Request("https://api.linkedin.com/v2/userinfo",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        me = json.load(r)
    person_urn = f"urn:li:person:{me['sub']}"
    expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=expires_in)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def gh(*args, stdin=None):
        subprocess.run(["gh", *args, *(["-R", REPO] if REPO else [])], input=stdin, text=True, check=True, capture_output=True)

    gh("secret", "set", "LINKEDIN_ACCESS_TOKEN", stdin=token)
    gh("secret", "set", "LINKEDIN_PERSON_URN", stdin=person_urn)
    gh("variable", "set", "LINKEDIN_TOKEN_EXPIRES_AT", "--body", expires_at)
    print(f"✓ Authorized as {me.get('name', person_urn)}")
    print(f"✓ Token stored in GitHub secrets for {REPO or 'this repo'}; expires {expires_at}")


if __name__ == "__main__":
    main()
