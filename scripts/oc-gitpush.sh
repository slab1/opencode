#!/bin/bash
# oc-gitpush - Push OpenCode repo to GitHub
# Usage: oc-gitpush [commit-msg]
# If no commit msg, commits with "Update" and pushes
# Token via GITHUB_TOKEN env var, or prompt if not set

REPO_DIR="/public/.config/opencode"

if [ ! -d "$REPO_DIR" ]; then
  echo "Error: Repo directory $REPO_DIR not found"
  exit 1
fi

TOKEN="${GITHUB_TOKEN}"
if [ -z "$TOKEN" ]; then
  echo "GITHUB_TOKEN not set. Provide one now (or press Enter to use last stored URL):"
  read -r TOKEN
fi

# Optional: commit first
if [ -n "$1" ]; then
  git -C "$REPO_DIR" add -A
  git -C "$REPO_DIR" commit -m "$*"
fi

CURRENT_URL=$(git -C "$REPO_DIR" remote get-url origin)

if [ -n "$TOKEN" ]; then
  REMOTE="https://${TOKEN}@github.com/slab1/opencode.git"
  git -C "$REPO_DIR" remote set-url origin "$REMOTE"
  git -C "$REPO_DIR" push origin master
  git -C "$REPO_DIR" remote set-url origin "https://github.com/slab1/opencode.git"
else
  git -C "$REPO_DIR" push origin master
fi

echo "✅ Pushed to github.com/slab1/opencode"
