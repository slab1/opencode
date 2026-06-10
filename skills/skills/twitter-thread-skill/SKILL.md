---
name: twitter-thread-skill
description: "Create and post multi-part threads on X/Twitter: split long content, write hooks, structure parts, add CTAs."
version: 2.0.0
author: OpenCode Platform Manager
license: MIT
compatibility: opencode>=1.0.0
metadata:
  platforms: [twitter, x]
  category: content-creation
  hermes:
    tags: [twitter, thread, content-creation, social-media]
---

# Twitter Thread Skill

Split a long-form content piece into a multi-tweet thread with optimal formatting, hook-per-tweet, continuation signals, and a strong call-to-action.

---

## Secret Safety (MANDATORY)

- **Never** paste API keys, bearer tokens, or OAuth secrets into an AI session.
- **Never** read `~/.xurl`, `tokens/*`, or `backend.json` contents back into conversation.
- Use `xurl auth status` to verify auth (never `cat ~/.xurl`).
- The user configures credentials manually via `setup-wizard.sh`.
- In agent sessions, use `--dry-run` to preview before posting.

---

## Prerequisites

| Requirement | Check Command | Notes |
|------------|---------------|-------|
| `post.sh` available | `which ~/.config/opencode/platforms/post.sh` | Core posting script |
| Backend or adapter | `post.sh --list-adapters` or check `backend.json` | One must be configured |
| `content-gen.py` (optional) | `python3 ~/.config/opencode/platforms/content-gen.py --help` | AI caption/thread generation |
| `xurl` CLI (optional, X direct) | `xurl --help` | Official X API CLI |

---

## One-Time Setup

### Option A: Via Platform Manager (recommended)

```bash
# Run the setup wizard
bash ~/.config/opencode/platforms/setup-wizard.sh

# Choose "X/Twitter" and configure your backend
# Verify it works:
bash ~/.config/opencode/platforms/post.sh --text "Test" --platforms twitter --dry-run
```

### Option B: Via xurl CLI (direct X API)

See the full setup in Hermes' xurl SKILL.md at `~/.hermes/skills/social-media/xurl/SKILL.md`.

```bash
# Register an X app at developer.twitter.com
# Then:
xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
xurl auth oauth2 --app my-app YOUR_USERNAME
xurl auth default my-app
xurl auth status  # Verify
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Post a thread (via adapter) | `post.sh --adapter twitter --text "T1\n\n---\n\nT2\n\n---\n\nT3" --platforms twitter` |
| Preview thread | Add `--dry-run` to any post command |
| Generate thread content | `content-gen.py caption --topic "..." --platform twitter` |
| Schedule a thread | `calendar.py add --text "..." --platforms twitter --schedule "2026-06-11 09:00"` |
| Process due threads | `calendar.py process` |
| Check posting history | `tail -20 platforms/posts.jsonl` |

---

## Thread Structure

Every great thread follows this skeleton:

```
Tweet 1  (HOOK)    → Bold claim, question, or surprising stat. 🧵 1/5
Tweet 2  (CONTEXT) → Set up the problem or background. 2/5
Tweet 3  (VALUE)   → Deliver the core insight or solution. 3/5
Tweet 4  (PROOF)   → Evidence, data, example, or case study. 4/5
Tweet 5  (CTA)     → Call to action + link. 5/5
```

### Character Limits

| Aspect | Limit | Notes |
|--------|-------|-------|
| Per tweet | 280 chars | Hard limit; content-gen.py respects this |
| Images per tweet | 4 | Use `--media` multiple times |
| Poll options | 4 | 25 chars max per option, 7 days max duration |
| Thread length | No limit | But engagement drops after 10-15 tweets |

---

## Detailed Procedures

### Step 1: Analyze source content

Extract from your blog post, article, or idea:

- **Main hook** (1 sentence, under 100 chars) — this is Tweet 1
- **3-5 key takeaways** — each becomes a tweet
- **1 surprising stat or quote** — use in Tweet 4 (Proof)
- **1 clear CTA** — last tweet (link, follow, subscribe)

### Step 2: Generate thread content

```bash
# Let AI generate the thread
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "How AI is transforming social media management in 2026" \
  --platform twitter \
  --tone "informative"

# Or write manually with the template above
```

### Step 3: Post the thread

#### Via Platform Manager (recommended)

```bash
# Preview first (always!)
bash ~/.config/opencode/platforms/post.sh \
  --text "Tweet 1\n\n---\n\nTweet 2\n\n---\n\nTweet 3" \
  --platforms twitter \
  --dry-run

# Post when ready (remove --dry-run)
bash ~/.config/opencode/platforms/post.sh \
  --text "Tweet 1\n\n---\n\nTweet 2\n\n---\n\nTweet 3" \
  --platforms twitter
```

#### Via xurl CLI (direct)

```bash
xurl post "Tweet 1"
xurl reply TWEET_1_ID "Tweet 2"
xurl reply TWEET_2_ID "Tweet 3"
```

### Step 4: Add media

```bash
# Single image per tweet is best for engagement
bash ~/.config/opencode/platforms/post.sh \
  --text "Thread with visuals\n\n---\n\nSecond tweet with image" \
  --media tweet1.png,tweet2.png \
  --platforms twitter \
  --dry-run
```

### Step 5: Monitor engagement

```bash
python3 ~/.config/opencode/platforms/analytics.py fetch --platform twitter
python3 ~/.config/opencode/platforms/analytics.py report
```

---

## Common Workflows

### Blog post announcement thread

```bash
THREAD="I just published 'The Future of Social Media Management' 🧵 1/5

The problem: managing 11 platforms manually takes 15+ hours/week. 2/5

The solution: AI-powered cross-posting with per-platform optimization. 3/5

In my first month, I saved 40 hours and got 3x more engagement. 4/5

Read the full post here: https://example.com/blog/future-smm 5/5"

bash ~/.config/opencode/platforms/post.sh \
  --text "$THREAD" \
  --platforms twitter \
  --first-comment "What tools do you use? 👇" \
  --dry-run
```

### Launch announcement

```bash
THREAD="Big news: we're launching today! 🚀 1/3

After 6 months of building, our Platform Manager is live. 2/3

11 platforms, one command, zero Buffer subscriptions. https://example.com 3/3"

bash ~/.config/opencode/platforms/post.sh \
  --text "$THREAD" \
  --media launch-banner.png \
  --platforms twitter \
  --hashtags "buildinpublic,launch,indiehacker" \
  --dry-run
```

---

## Best Practices

| Practice | Why |
|----------|-----|
| ✅ Hook in first 50 chars | That's what shows in the timeline |
| ✅ One idea per tweet | Easier to read, retweet, quote |
| ✅ Continuation markers (1/5...) | Readers know there's more |
| ✅ Visuals in at least 1 tweet | 3x more engagement |
| ✅ CTA in last tweet | Drive the action |
| ❌ Walls of text | Nobody reads them |
| ❌ No hook | Nobody clicks through |
| ❌ Posting without preview | Mistakes get seen by everyone |
| ❌ Threads over 15 tweets | Engagement drops sharply |

---

## Error Handling

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tweet over 280 chars | Content too long | Split further; use `content-gen.py` with platform constraint |
| 401 Unauthorized | Auth token expired | Re-run `setup-wizard.sh` or `xurl auth oauth2` |
| 403 Forbidden | Missing API scope | Check X API plan; enroll in Basic/Pro |
| Rate limited (429) | Too many posts/min | Wait 15 min; use `--schedule` to stagger |
| Media rejected | Wrong format/size | Use `media-optimizer.py` first |
| Adapter not found | Adapter not installed | Run `post.sh --list-adapters` to see available adapters |
| Backend not configured | No `backend.json` | Run `setup-wizard.sh` |

---

## Agent Workflow

When an AI agent uses this skill:

1. **Verify prerequisites** — Check `post.sh` exists and backend/adapter is configured
2. **Ask user for topic** — Get the source content or idea
3. **Generate or outline thread** — Use content-gen.py or manual template
4. **Preview with `--dry-run`** — Show the user the full thread before posting
5. **Confirm** — Ask user explicit yes/no before any posting
6. **Post** — Execute without `--dry-run`
7. **Log** — The post is automatically logged to `posts.jsonl`
8. **Follow up** — Offer to schedule the next thread or analyze engagement

**Never post without explicit user confirmation.**

---

## Troubleshooting

| Problem | Likely Root | Quick Fix |
|---------|-------------|-----------|
| `post.sh` command not found | Path not in $PATH | Use full path: `bash ~/.config/opencode/platforms/post.sh` |
| `--text` is ignored | Text too long for shell | Use a file and `--stdin` instead |
| Thread order wrong | `---` separator missing | Each `\n\n---\n\n` is a new tweet |
| Emoji rendering broken | Terminal encoding | Test with `--dry-run` first |
| Analytics show 0 impressions | Just posted | Give it 5-10 min; X API has delay |
