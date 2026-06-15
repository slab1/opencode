# Platform Manager — Setup Checklist

## Status: 1/11 platforms configured ✅

Twitter is fully configured. Follow the steps below to connect the remaining
platforms and the scheduling backend.

---

## 1. BulkPublish Backend (Required for Posting)

BulkPublish is the cloud backend that routes posts to platforms.
- **Sign up:** https://app.bulkpublish.com (free, 100 req/day)
- **Get API key:** Settings → API Keys
- **Save it:**
  ```bash
  echo "bp_your_api_key_here" > ~/.config/opencode/platforms/tokens/bulkpublish_api.key
  chmod 600 ~/.config/opencode/platforms/tokens/bulkpublish_api.key
  ```
- **Enable MCP:** Set `BULKPUBLISH_API_KEY` env var and enable the bulkpublish MCP in `opencode.jsonc`

---

## 2. Platform Credentials

For each platform, create a developer app and save credentials:

### Facebook
1. Go to https://developers.facebook.com
2. Create a Business app → get **App ID** + **App Secret**
3. Get your **Page ID** from your Facebook Page
4. Save: `tokens/facebook_client_id.token`, `tokens/facebook_client_secret.token`

### Instagram
1. Go to https://developers.facebook.com
2. Use the same Facebook app, add Instagram API
3. Convert your Instagram to a **Business/Creator account**
4. Get your **Instagram Business Account ID** via Graph API
5. Save: `tokens/instagram_client_id.token`, `tokens/instagram_client_secret.token`

### TikTok
1. Go to https://developers.tiktok.com
2. Create a new app → get **Client Key** + **Client Secret**
3. Get **Open ID** from the user authorization flow
4. Save: `tokens/tiktok_client_key.token`, `tokens/tiktok_client_secret.token`

### YouTube
1. Go to https://console.cloud.google.com
2. Create a project → enable YouTube Data API v3
3. Create OAuth 2.0 credentials → get **Client ID** + **Client Secret**
4. Generate a **Refresh Token** via OAuth playground
5. Save: `tokens/youtube_client_id.token`, `tokens/youtube_client_secret.token`

### LinkedIn
1. Go to https://www.linkedin.com/developers
2. Create a new app → get **Client ID** + **Client Secret**
3. Get your **Organization URN** from your LinkedIn Page
4. Save: `tokens/linkedin_client_id.token`, `tokens/linkedin_client_secret.token`

### Pinterest
1. Go to https://developers.pinterest.com
2. Create a Business app → get **App ID** + **App Secret**
3. Generate a **Refresh Token** via OAuth
4. Save: `tokens/pinterest_app_id.token`, `tokens/pinterest_app_secret.token`

### Threads
1. Go to https://developers.facebook.com
2. Add Threads API to your Facebook app → get **App ID** + **App Secret**
3. Save: `tokens/threads_client_id.token`, `tokens/threads_client_secret.token`

### Bluesky (Simplest)
1. Create account on bsky.app
2. Go to **Settings → App Passwords → Add App Password**
3. Save handle + app password:
   ```bash
   echo "your.handle.bsky.social" > ~/.config/opencode/platforms/tokens/bluesky_handle.token
   echo "xxxx-xxxx-xxxx-xxxx" > ~/.config/opencode/platforms/tokens/bluesky_app_password.token
   chmod 600 ~/.config/opencode/platforms/tokens/bluesky_*
   ```

### Mastodon
1. Create account on any Mastodon instance (e.g., mastodon.social)
2. Go to **Settings → Development → New Application**
3. Create app → copy Access Token
4. Save: `tokens/mastodon_access_token.token`

### Google Business Profile
1. Go to https://console.cloud.google.com
2. Enable Google My Business API → create OAuth credentials
3. Get **Client ID** + **Client Secret** + **Refresh Token**
4. Save: `tokens/gbp_client_id.token`, `tokens/gbp_client_secret.token`

---

## 3. After Getting Credentials

For each platform, update `accounts.json` from `"status": "pending"` to `"status": "configured"`
and add the credential file paths (follow the Twitter entry as a template).

Then run:
```bash
# Test a dry-run post
~/.config/opencode/platforms/post.sh --text "Hello world!" --platforms twitter --dry-run

# Or come back here and ask the AI: "Add my [platform] credentials"
```
