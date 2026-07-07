# Bluesky Adapter

Posts content to Bluesky via the AT Protocol.

## Capabilities
- Text posts (300 char limit)
- Image uploads via blob.bsky.social
- Dry-run mode

## Setup
1. Create an app password at bsky.app → Settings → App Passwords
2. Save credentials:
   ```bash
   echo "your-handle.bsky.social" > ~/.config/opencode/platforms/tokens/bluesky_handle.token
   echo "your-app-password" > ~/.config/opencode/platforms/tokens/bluesky_password.token
   chmod 600 ~/.config/opencode/platforms/tokens/bluesky_*.token
   ```

## Dependencies
```bash
pip install atproto
```

## Testing
```bash
python3 -c "from adapters import post_to_platform; print(post_to_platform('bluesky', text='Test from OpenCode!', dry_run=True))"
```
