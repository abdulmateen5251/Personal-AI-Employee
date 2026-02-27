```skill
---
name: social-poster
description: Draft-first Facebook, Instagram, and X posting with approval workflow and posting summaries.
---
```

# Social Poster

Creates social post drafts for Facebook, Instagram, and X (Twitter), routes them through `/Pending_Approval`, and processes approved posts with audit logging and summaries.

## Platforms
- Facebook
- Instagram
- Twitter (X)

## Server Lifecycle

### Start
```bash
bash scripts/start.sh
```

### Stop
```bash
bash scripts/stop.sh
```

### Verify
```bash
python3 scripts/verify.py
```

## Configuration
- `DRY_RUN=true` recommended for setup validation.
- Optional tokens: `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_ACCESS_TOKEN`, `TWITTER_BEARER_TOKEN`.

## Behavior
- Generates `SOCIAL_DRAFT_<platform>_<timestamp>.md` in `/Pending_Approval`.
- Only publishes drafts moved to `/Approved`.
- Appends daily summary in `/Briefings/YYYY-MM-DD_Social_Posting_Summary.md`.
