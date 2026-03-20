#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-abort"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Abort Session) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

echo "base line" > .zshrc
echo "old file" > new-upstream.txt
git add .
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

echo -e "${GREEN}=== Creating Divergence ===${NC}"
echo "local customization" >> "$USER_DIR/dot_zshrc"
git -C "$USER_DIR" commit -am "Customize zshrc locally" >/dev/null
cd "$MAINTAINER_DIR"
git rm .zshrc
echo "brand new upstream file" > extra.txt
echo "updated upstream content" > new-upstream.txt
git add .
git commit -m "Delete zshrc and add updates"
git push origin HEAD
cd "$PROJECT_ROOT"

BASE_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse HEAD)
LATEST_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse origin/HEAD)

echo -e "${GREEN}=== Running Update To Create Session ===${NC}"
set +e
OUTPUT=$(timeout 2s uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" 2>&1)
STATUS=$?
set -e

echo "$OUTPUT"

if [ "$STATUS" -ne 0 ] && [ "$STATUS" -ne 124 ]; then
  echo "FAILURE: Expected chezmerge to either stay open in the UI or time out"
  exit 1
fi

if [ ! -f "$USER_DIR/.git/chezmerge-session/manifest.json" ]; then
  echo "FAILURE: Expected active chezmerge session after interrupted merge"
  exit 1
fi

if [ ! -f "$USER_DIR/extra.txt" ]; then
  echo "FAILURE: Expected imported upstream file to exist before abort"
  exit 1
fi

if ! grep -q "updated upstream content" "$USER_DIR/new-upstream.txt"; then
  echo "FAILURE: Expected auto-updated tracked file before abort"
  exit 1
fi

echo -e "${GREEN}=== Simulating Pointer Drift During Session ===${NC}"
git -C "$USER_DIR/.chezmerge-upstream" checkout "$LATEST_SHA" >/dev/null 2>&1
git -C "$USER_DIR" add .chezmerge-upstream

echo -e "${GREEN}=== Aborting Session ===${NC}"
ABORT_OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --abort)

echo "$ABORT_OUTPUT"

if [ -e "$USER_DIR/extra.txt" ]; then
  echo "FAILURE: Abort should remove imported untracked files"
  exit 1
fi

if ! grep -q "^old file$" "$USER_DIR/new-upstream.txt"; then
  echo "FAILURE: Abort should restore tracked file content"
  exit 1
fi

if ! grep -q "local customization" "$USER_DIR/dot_zshrc"; then
  echo "FAILURE: Abort should preserve untouched local customization"
  exit 1
fi

CURRENT_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse HEAD)
if [ "$CURRENT_SHA" != "$BASE_SHA" ]; then
  echo "FAILURE: Abort should restore the recorded submodule pointer"
  exit 1
fi

if [ -e "$USER_DIR/.git/chezmerge-session/manifest.json" ]; then
  echo "FAILURE: Abort should clean up the session manifest"
  exit 1
fi

STATUS=$(git -C "$USER_DIR" status --porcelain)
if [ -n "$STATUS" ]; then
  echo "FAILURE: Abort should leave the repo clean after restoring the committed pre-merge state"
  echo "$STATUS"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Abort restored the in-progress chezmerge session.${NC}"
