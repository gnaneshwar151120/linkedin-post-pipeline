# LinkedIn Developer App Setup

One-time setup so the GitHub Actions in this repo can publish approved posts through the official API. About 15 minutes.

## 1. Create a minimal LinkedIn Page

LinkedIn requires every developer app to be linked to a Page. This Page is only an owner for the app; you never
need to post on it.

1. linkedin.com → **For Business** (top right) → **Create a Company Page** → **Company**
2. Name, e.g. `<Your Name> – Projects`; any free URL slug; industry `IT Services and IT Consulting`;
   size `0-1 employees`; type `Self-employed`
3. Tick the verification box → **Create page**

## 2. Create the developer app

1. Go to https://www.linkedin.com/developers/apps → **Create app**
2. **App name:** e.g. `post-pipeline`
3. **LinkedIn Page:** pick the Page from step 1
4. **App logo:** any square image (required)
5. Accept the terms → **Create app**

## 3. Verify the app with the Page

1. In the app → **Settings** tab → **Verify** → **Generate URL**
2. Open that URL while logged in as yourself (you're the Page admin) → **Verify**

## 4. Add products

**Products** tab → **Request access** on both:

- **Share on LinkedIn**: allows posting (`w_member_social`)
- **Sign In with LinkedIn using OpenID Connect**: lets the script read your member ID (`openid`, `profile`)

Both are self-serve and are usually approved instantly.

## 5. Add the redirect URL and copy the credentials

1. **Auth** tab → **OAuth 2.0 settings** → **Authorized redirect URLs** → add
   `http://localhost:8765/callback` → **Update**
2. On the same tab, copy the **Client ID** and **Primary Client Secret**

## 6. Save the credentials in your shell profile, never in the repo

Run in your terminal:

```bash
echo 'export LINKEDIN_CLIENT_ID="paste_client_id"' >> ~/.zshrc
echo 'export LINKEDIN_CLIENT_SECRET="paste_client_secret"' >> ~/.zshrc
source ~/.zshrc
```

Then, from your clone of this repo (with `gh auth login` done):

```bash
python3 automation/linkedin/authorize.py
```

It opens your browser once and stores the token as GitHub secrets. Then run the **LinkedIn smoke test** workflow
from the Actions tab to check every format.
