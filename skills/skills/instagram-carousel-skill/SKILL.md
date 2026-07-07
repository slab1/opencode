---
name: instagram-carousel-skill
description: "Design and publish multi-slide Instagram carousel posts with AI-generated visuals, platform-optimized captions, and proper resizing."
version: 2.0.0
author: OpenCode Platform Manager
license: MIT
compatibility: opencode>=1.0.0
metadata:
  platforms: [instagram]
  category: content-creation
  hermes:
    tags: [instagram, carousel, content-creation, social-media, visual]
---

# Instagram Carousel Skill

Create scroll-stopping multi-slide Instagram carousels with AI-generated images per slide, platform-optimized captions, and proper dimension handling for feed, stories, and reels.

---

## Secret Safety (MANDATORY)

- **Never** paste Instagram access tokens or API secrets into an AI session.
- **Never** read `tokens/*` files back into conversation.
- Use `--dry-run` to preview carousel content before scheduling.
- The user configures Instagram credentials via `setup-wizard.sh` outside the agent session.
- Third-party posting limits apply — respect Instagram's 25 hashtag limit.

---

## Prerequisites

| Requirement | Check Command | Notes |
|------------|---------------|-------|
| `content-gen.py` | `python3 ~/.config/opencode/platforms/content-gen.py --help` | AI image & caption generation |
| `media-optimizer.py` | `python3 ~/.config/opencode/platforms/media-optimizer.py --help` | Resize for Instagram dimensions |
| Pillow library | `python3 -c "from PIL import Image; print('OK')"` | Required by media-optimizer.py |
| Backend or adapter | `post.sh --list-adapters` | For actual posting |
| `calendar.py` (optional) | `python3 ~/.config/opencode/platforms/calendar.py --help` | For scheduling |

---

## One-Time Setup

### AI Model Endpoint

```bash
# Start the free AI models for image generation
bash ~/.config/opencode/platforms/setup-free-models.sh

# Verify:
python3 ~/.config/opencode/platforms/content-gen.py test
# Expected: "Connection OK" or AI model available
```

### Instagram Connection

```bash
# Run the setup wizard and choose Instagram
bash ~/.config/opencode/platforms/setup-wizard.sh

# This will:
# 1. Ask for your Instagram credentials (or backend API key)
# 2. Write them to tokens/ with proper permissions
# 3. Update accounts.json

# Verify:
bash ~/.config/opencode/platforms/post.sh --text "Test" --platforms instagram --dry-run
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Generate carousel images | `content-gen.py image --prompt "..." --output slide1.png` |
| Resize for Instagram | `media-optimizer.py slide.png --platforms instagram` |
| Generate caption | `content-gen.py caption --topic "..." --platform instagram` |
| Generate hashtags | `content-gen.py hashtags --topic "..." --platform instagram --count 15` |
| Schedule carousel | `calendar.py add --text "..." --platforms instagram --media slides/ --schedule "..."` |
| Preview carousel | `post.sh --text "..." --platforms instagram --dry-run` |

---

## Carousel Structure

```
Slide 1:  COVER    → Title + hook image (brand colors, bold text overlay)
Slide 2:  PROBLEM  → Relatable pain point or question
Slide 3:  SOLUTION → Core value, process, or insight
Slide 4:  PROOF    → Data, example, before/after, or testimonial
Slide 5:  CTA      → Follow, save, share, comment, or link in bio
```

### Instagram Dimension Reference

| Format | Dimensions | Aspect Ratio | Notes |
|--------|-----------|--------------|-------|
| Feed (square) | 1080×1080 | 1:1 | Best for carousels |
| Feed (portrait) | 1080×1350 | 4:5 | Takes more screen space |
| Feed (landscape) | 1080×566 | 1.91:1 | Less common |
| Stories | 1080×1920 | 9:16 | Vertical full-screen |
| Reels | 1080×1920 | 9:16 | Same as stories |

**Recommended for carousels:** 1080×1080 square — consistent, no cropping surprises.

---

## Detailed Procedures

### Step 1: Plan your slides

```bash
# Define the 5-slide structure
SLIDES=(
  "Cover: title slide — vibrant gradient, white bold text overlay"
  "Problem: illustration of scattered social media tabs"
  "Solution: clean diagram of unified platform manager"
  "Proof: stats showing 40hr/week saved with automation"
  "CTA: 'Save this post for later' with arrow graphic"
)
```

### Step 2: Generate each slide image

```bash
mkdir -p slides

for i in "${!SLIDES[@]}"; do
  python3 ~/.config/opencode/platforms/content-gen.py image \
    --prompt "Instagram carousel slide ${SLIDES[$i]}" \
    --output "slides/slide_$((i+1)).png"
done
```

### Step 3: Resize for Instagram

```bash
for f in slides/*.png; do
  python3 ~/.config/opencode/platforms/media-optimizer.py "$f" \
    --platforms instagram \
    --output-dir ./optimized
done
```

### Step 4: Generate caption

```bash
python3 ~/.config/opencode/platforms/content-gen.py caption \
  --topic "How we built a free Buffer alternative" \
  --platform instagram \
  --tone "inspiring"
```

### Step 5: Generate hashtags

```bash
python3 ~/.config/opencode/platforms/content-gen.py hashtags \
  --topic "social media management" \
  --platform instagram \
  --count 15
```

### Step 6: Schedule or post

```bash
# Schedule for later
python3 ~/.config/opencode/platforms/calendar.py add \
  --text "Generated caption here" \
  --platforms instagram \
  --schedule "2026-06-11 12:00" \
  --media ./optimized \
  --hashtags "socialmedia,automation,productivity" \
  --title "Free Buffer Alternative Carousel"

# Or preview immediately
bash ~/.config/opencode/platforms/post.sh \
  --text "Generated caption" \
  --media ./optimized/slide1_instagram_square.png \
  --platforms instagram \
  --hashtags "socialmedia,automation" \
  --dry-run
```

---

## Common Workflows

### Educational carousel ("5 steps to...")

```
Slide 1: "5 Steps to Automate Your Social Media" (cover)
Slide 2: "Step 1: Connect your platforms" (screenshot of setup-wizard.sh)
Slide 3: "Step 2: Generate content" (content-gen.py in action)
Slide 4: "Step 3: Optimize per platform" (media-optimizer.py)
Slide 5: "Step 4: Schedule strategically" (calendar.py process)
Slide 6: "Step 5: Analyze and improve" (analytics.py report)
Slide 7: "Save this for later! 🔖"
```

### Before/after carousel

```
Slide 1: "Before → After: My Social Media Workflow" (cover)
Slide 2: "Before: Buffer + Hootsuite + Later = $99/month" (sad wallet)
Slide 3: "After: OpenCode Platform Manager = FREE" (happy face)
Slide 4: "Time saved: 15h/week → 2h/week" (data chart)
Slide 5: "Link in bio to get started" (CTA)
```

---

## Caption Templates

### Educational
```
How to manage 11 platforms from one terminal 🖥️

I used to spend 15 hours/week posting manually.
Now it takes 2 hours.

Here's my exact setup:

1. Connect your accounts (5 min)
2. Generate content with AI (10 min)
3. Schedule in batches (15 min)
4. Analyze results weekly (5 min)

Want the full guide? Save this post! 📌
```

### Launch
```
We built a Buffer alternative that's... free. 🚀

11 platforms supported.
AI content generation.
Auto-resize for every format.
Zero monthly subscription.

It's open source and self-hosted.

Drop a 🔥 if you're interested!
```

---

## Best Practices

| Practice | Why |
|----------|-----|
| ✅ 5-7 slides | Optimal engagement window |
| ✅ Strong cover slide | That's what shows in the feed |
| ✅ Consistent visual style | Looks professional |
| ✅ Text overlays on images | Works even without sound |
| ✅ CTA on last slide | Drives saves and shares |
| ✅ 10-15 hashtags | Max reach without looking spammy |
| ❌ More than 10 slides | Engagement drops |
| ❌ Text-heavy slides | Hard to read on mobile |
| ❌ No caption strategy | Images need context |
| ❌ All caps hashtags | Just looks loud |

---

## Error Handling

| Symptom | Cause | Fix |
|---------|-------|-----|
| Image generation fails | AI endpoint not running | Run `setup-free-models.sh` |
| Wrong dimensions | media-optimizer.py not used | Run `media-optimizer.py` before posting |
| "Media too large" | File > 4MB | Compress or use smaller resolution |
| Caption truncated | Over 2200 chars | Shorten; Instagram has a display limit |
| Hashtags not working | Shadowban or broken formatting | Remove banned hashtags; space them out |
| Post fails silently | Backend not connected | Run `setup-wizard.sh` to reconfigure |
| Slides out of order | Wrong file ordering | Name files `slide_01.png`, `slide_02.png` etc. |

---

## Agent Workflow

When an AI agent uses this skill:

1. **Check prerequisites** — Verify content-gen.py, media-optimizer.py are available
2. **Ask user for topic** — What's the carousel about? Educational, launch, tutorial?
3. **Plan slides** — Outline 5-7 slides with the user's approval
4. **Generate visuals** — Run content-gen.py image for each slide
5. **Resize** — Run media-optimizer.py for Instagram dimensions
6. **Generate caption + hashtags** — Use content-gen.py caption and hashtags
7. **Preview** — Show the user what it looks like (`--dry-run`)
8. **Confirm** — Get explicit yes/no before scheduling or posting
9. **Schedule or post** — Execute calendar.py add or post.sh
10. **Follow up** — Offer to track engagement in 24h

**Never post without explicit user confirmation and a dry-run preview.**

---

## Troubleshooting

| Problem | Likely Root | Quick Fix |
|---------|-------------|-----------|
| Image has wrong colors | PNG vs JPG confusion | Use JPG for photos, PNG for graphics |
| Text overlay in wrong spot | LLM didn't add text to prompt | Explicitly include "with bold white overlay text" |
| Carousel looks disjointed | No style guide per slide | Use consistent color palette in prompts |
| "Command not found" | Script not in PATH | Use full `~/.config/opencode/platforms/` path |
| AI model returns gibberish | Wrong model for images | Use `--model z-image-turbo` or compatible |
