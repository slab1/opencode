---
name: content-repurposing-skill
description: "Transform one piece of source content into platform-optimized posts for 11 social networks with proper formatting, tone, and scheduling."
version: 2.0.0
author: OpenCode Platform Manager
license: MIT
compatibility: opencode>=1.0.0
metadata:
  platforms: [twitter, linkedin, instagram, facebook, tiktok, youtube, threads, bluesky, mastodon, pinterest, gbp]
  category: content-creation
  hermes:
    tags: [repurposing, multi-platform, content-strategy, social-media]
---

# Content Repurposing Skill

Take **one** piece of source content (blog post, video script, podcast transcript) and automatically generate platform-optimized posts for **all 11 social networks** — each adapted to that platform's format, tone, and audience expectations.

---

## Secret Safety (MANDATORY)

- **Never** read API tokens, backend credentials, or `accounts.json` into an AI session.
- **Never** paste OAuth tokens or client secrets into the chat.
- All credentials are stored in `~/.config/opencode/platforms/tokens/` with `chmod 600`.
- Use `setup-wizard.sh` for all credential configuration.
- Always use `--dry-run` before posting anything.

---

## Prerequisites

| Requirement | Check Command | Notes |
|------------|---------------|-------|
| `content-gen.py` | `python3 ~/.config/opencode/platforms/content-gen.py --help` | Caption, hashtag, and repurposing generation |
| `media-optimizer.py` | `python3 ~/.config/opencode/platforms/media-optimizer.py --help` | Resize media for all 11 platforms |
| `post.sh` | `bash ~/.config/opencode/platforms/post.sh --help` | Cross-platform posting |
| `calendar.py` | `python3 ~/.config/opencode/platforms/calendar.py --help` | Staggered scheduling |
| Backend or adapter | `post.sh --list-adapters` | At least one configured |

---

## One-Time Setup

```bash
# Configure at least one backend or adapter
bash ~/.config/opencode/platforms/setup-wizard.sh

# Verify posting works
bash ~/.config/opencode/platforms/post.sh --text "Test" --platforms twitter --dry-run

# Start AI models (for automated caption generation)
bash ~/.config/opencode/platforms/setup-free-models.sh
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Generate captions per platform | `content-gen.py caption --topic "..." --platform <name>` |
| Generate hashtags | `content-gen.py hashtags --topic "..." --platform <name> --count N` |
| Resize media for all platforms | `media-optimizer.py source.jpg --platforms all` |
| Preview a post | `post.sh --text "..." --platforms <names> --dry-run` |
| Schedule staggered posts | `calendar.py add --text "..." --platforms <name> --schedule "..."` |
| Process scheduled posts | `calendar.py process` |
| View analytics | `analytics.py report` |

---

## Platform Format Reference

| Platform | Max Length | Best Tone | Hashtag Style | Best Time (ET) | Content Type |
|----------|-----------|-----------|---------------|----------------|--------------|
| **X/Twitter** | 280 chars | Punchy, bold, controversial | 2-3 inline | 8-9am | Text + image |
| **LinkedIn** | 3000 chars | Professional, story-driven | 3-5 at end | 7-8am Tue-Thu | Text + doc |
| **Instagram** | 2200 chars | Inspiring, emotional | 10-15 in caption | 11am | Image + caption |
| **Facebook** | 63K chars | Conversational, personal | 5-10 in comment | 1pm | Text + link |
| **TikTok** | 150 chars (desc) | Energetic, trend-aware | 3-5 in desc | 7pm | Short video |
| **YouTube** | 5000 chars (desc) | Educational, detailed | 3-5 in desc | 3pm | Long video |
| **Threads** | 500 chars | Casual, chatty | 2-3 inline | 12pm | Text + image |
| **Bluesky** | 300 chars | Direct, authentic | 1-2 inline | 9am | Text |
| **Mastodon** | 500 chars | Friendly, community | 1-3 at end | 10am | Text + image |
| **Pinterest** | 500 chars | How-to, aspirational | 5-10 in desc | 8pm Fri | Vertical image |
| **GBP (Google)** | 1500 chars | Local, helpful | 0-2 natural | 10am | Text + photo |

---

## Detailed Procedures

### Step 1: Analyze source content

Extract from your source material (blog post, script, transcript):

```bash
# Single source → multi-platform strategy
SOURCE="How AI is changing social media management"

# Extract:
# - Main thesis (1 sentence)
# - 3-5 key takeaways
# - 1 surprising statistic or quote
# - Target audience
# - Primary CTA
```

### Step 2: Generate per-platform content

```bash
# Twitter/X — short and punchy
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "$SOURCE" --platform twitter

# LinkedIn — professional story
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "$SOURCE" --platform linkedin --tone "thought-leadership"

# Instagram — visual + emotional
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "$SOURCE" --platform instagram --tone "inspiring"

# Facebook — conversational
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "$SOURCE" --platform facebook --tone "conversational"

# Hashtags for each platform
python3 ~/.config/opencode/platforms/content-gen.py hashtags \
  --topic "$SOURCE" --platform instagram --count 15
python3 ~/.config/opencode/platforms/content-gen.py hashtags \
  --topic "$SOURCE" --platform twitter --count 3
python3 ~/.config/opencode/platforms/content-gen.py hashtags \
  --topic "$SOURCE" --platform linkedin --count 5
```

### Step 3: Resize media for each platform

```bash
# Single source image → all platform dimensions
python3 ~/.config/opencode/platforms/media-optimizer.py source-image.jpg \
  --platforms all \
  --output-dir ./optimized

# Specific platforms only
python3 ~/.config/opencode/platforms/media-optimizer.py source-image.jpg \
  --platforms twitter,linkedin,instagram \
  --output-dir ./optimized
```

### Step 4: Schedule staggered posts

```bash
# Strategy: spread over 2-3 days for maximum reach
# Day 1
python3 ~/.config/opencode/platforms/calendar.py add \
  --text "Twitter version..." \
  --media ./optimized/source_twitter.jpg \
  --platforms twitter \
  --schedule "2026-06-11 08:00" \
  --title "Twitter: $SOURCE"

python3 ~/.config/opencode/platforms/calendar.py add \
  --text "LinkedIn version..." \
  --media ./optimized/source_linkedin.jpg \
  --platforms linkedin \
  --schedule "2026-06-11 10:00" \
  --title "LinkedIn: $SOURCE"

# Day 2
python3 ~/.config/opencode/platforms/calendar.py add \
  --text "Instagram version..." \
  --media ./optimized/source_instagram_square.png \
  --platforms instagram \
  --schedule "2026-06-12 11:00" \
  --hashtags "aitools,socialmedia" \
  --title "Instagram: $SOURCE"

python3 ~/.config/opencode/platforms/calendar.py add \
  --text "Facebook version..." \
  --platforms facebook \
  --schedule "2026-06-12 13:00" \
  --title "Facebook: $SOURCE"

# Day 3
python3 ~/.config/opencode/platforms/calendar.py add \
  --text "Threads version..." \
  --platforms threads,bluesky,mastodon \
  --schedule "2026-06-13 09:00" \
  --title "Threads/Bluesky/Mastodon: $SOURCE"
```

### Step 5: Process and monitor

```bash
# Process all due posts
python3 ~/.config/opencode/platforms/calendar.py process

# After 24h, check performance
python3 ~/.config/opencode/platforms/analytics.py fetch
python3 ~/.config/opencode/platforms/analytics.py report
python3 ~/.config/opencode/platforms/analytics.py learn
```

---

## Common Workflows

### Blog post → 11 platforms

```
1. Write blog post (single source)
2. Extract tl;dr, 3 takeaways, 1 stat
3. Generate per-platform captions
4. Resize featured image
5. Schedule across 2-3 days:
   - Day 1: Twitter + LinkedIn + Threads
   - Day 2: Instagram + Facebook + Bluesky + Mastodon
   - Day 3: Pinterest + YouTube (if video) + TikTok (if short)
6. Monitor and update "best time" model
```

### Weekly batch processing

```bash
# Monday morning: process this week's content
WEEK_CONTENT="Week 23 newsletter: AI tools roundup"

# Run in batch
for platform in twitter linkedin instagram facebook threads bluesky mastodon; do
  python3 ~/.config/opencode/platforms/content-gen.py caption \
    --topic "$WEEK_CONTENT" --platform "$platform" \
    --output "captions/$platform.txt"
done

# Schedule all at once
python3 ~/.config/opencode/platforms/calendar.py add \
  --text "$(cat captions/twitter.txt)" \
  --platforms twitter --schedule "2026-06-16 08:00" \
  --title "Twitter: Week 23"
# ... repeat for each platform with staggered times
```

---

## Repurposing Matrix (Cheat Sheet)

| Platform | Adapt This | Keep This | Remove This |
|----------|-----------|-----------|-------------|
| X/Twitter | First 50 chars = hook | Core stat/quote | Fluff words |
| LinkedIn | Lead with story, not news | Key insight | Shortened links |
| Instagram | Make visual-first | Emotional hook | Long paragraphs |
| Facebook | Add personal experience | Core message | Industry jargon |
| TikTok | Shorten to 60s script | Call to action | Text walls |
| YouTube | Expand with detail | Educational value | Intro fluff |
| Threads | Casual opening | Authentic voice | Formal tone |
| Bluesky | Direct statement | Unique take | Hashtag spam |
| Mastodon | Community angle | Helpful tip | Clickbait |
| Pinterest | Title as text overlay | Aspirational angle | Dates/timestamps |
| Google Biz | Local context | Core benefit | Links to other platforms |

---

## Best Practices

| Practice | Why |
|----------|-----|
| ✅ Adapt tone per platform | Each has distinct culture |
| ✅ Stagger posts 2-3 days | Avoids content fatigue |
| ✅ Resize images per platform | Wrong size = cropped badly |
| ✅ Custom hashtags per platform | IG needs 15, Twitter needs 2 |
| ✅ Different hooks per platform | What works on LinkedIn fails on TikTok |
| ❌ Cross-post same text everywhere | Looks lazy, hurts reach |
| ❌ Post everything at once | Platform algorithms penalize |
| ❌ Ignore character limits | Text gets truncated |
| ❌ Same image for all platforms | Gets cropped/distorted |

---

## Error Handling

| Symptom | Cause | Fix |
|---------|-------|-----|
| Post truncated on platform | Over character limit | Check format table above; shorten text |
| Image cropped badly | Wrong aspect ratio | Use `media-optimizer.py` with correct platform |
| Hashtags not working | Platform-specific issue | Instagram: max 30; LinkedIn: max 5 |
| Engagement lower than expected | Wrong tone for platform | Adjust tone per matrix above |
| Scheduling conflict | Two posts same time | Stagger by at least 2 hours |
| Adapter not found | Not installed yet | Create adapter in `platforms/adapters/` |
| analytics.py learn has no data | Not enough posts yet | Post at least 10 items across 3+ platforms |

---

## Troubleshooting

| Problem | Likely Root | Quick Fix |
|---------|-------------|-----------|
| AI captions sound samey | No per-platform prompt adaptation | Add `--tone` flag matching the platform |
| Wrong audience reaction | Platform audience mismatch | Check matrix above; adjust hook |
| Calendar not processing | `post.sh` path issue | Run `calendar.py process` directly |
| Too many hashtags | Excess hashtags on Twitter | Limit to 2-3 per caption |
| Missing media file | Wrong output dir | Check `media-optimizer.py --output-dir` |
| Duplicate posts | Re-running same script | Check `posts.jsonl` for existing post IDs |

---

## Agent Workflow

When an AI agent uses this skill:

1. **Get source content** — Ask user for the blog post, video, or topic
2. **Analyze** — Extract hook, 3 takeaways, 1 stat, audience, CTA
3. **Check platforms** — Which platforms does the user want? All 11 or a subset?
4. **Generate per-platform content** — Run content-gen.py for each selected platform
5. **Resize media** — Run media-optimizer.py for selected platforms
6. **Build schedule** — Stagger across 2-3 days at optimal times per platform
7. **Preview** — Show user the full schedule with `--dry-run` on each
8. **Confirm** — Get explicit yes/no before scheduling or posting
9. **Execute** — Run calendar.py add for each post
10. **Monitor** — Offer analytics setup for tracking engagement

**Never repurpose content without explicit user approval of each platform variant.**
