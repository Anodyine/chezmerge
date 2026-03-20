#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-undo-last"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Undo Last) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
for i in {1..10}; do echo "Line $i"; done > .config
git add .config
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

BASE_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse HEAD)

echo -e "${GREEN}=== Creating Divergence ===${NC}"
cd "$MAINTAINER_DIR"
sed -i.bak 's/^Line 1$/Line 1 Modified Remote/' .config && rm .config.bak
git commit -am "Update Line 1"
git push origin HEAD
cd "$PROJECT_ROOT"

sed -i.bak 's/^Line 10$/Line 10 Modified Local/' "$USER_DIR/dot_config" && rm "$USER_DIR/dot_config.bak"
git -C "$USER_DIR" commit -am "Customize line 10 locally" >/dev/null

echo -e "${GREEN}=== Running Chezmerge Merge ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR"

MERGED_CONTENT=$(cat "$USER_DIR/dot_config")
if ! echo "$MERGED_CONTENT" | grep -q "Line 1 Modified Remote"; then
  echo "FAILURE: Expected merged file to contain upstream change before undo"
  exit 1
fi

LATEST_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse HEAD)
if [ "$LATEST_SHA" = "$BASE_SHA" ]; then
  echo "FAILURE: Expected submodule pointer to advance after merge"
  exit 1
fi

echo -e "${GREEN}=== Undoing Last Chezmerge Merge ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --undo-last)

echo "$OUTPUT"

CONTENT=$(cat "$USER_DIR/dot_config")
if echo "$CONTENT" | grep -q "Line 1 Modified Remote"; then
  echo "FAILURE: Undo should remove the upstream change from the merged file"
  exit 1
fi

if ! echo "$CONTENT" | grep -q "Line 10 Modified Local"; then
  echo "FAILURE: Undo should preserve the local customization"
  exit 1
fi

CURRENT_SHA=$(git -C "$USER_DIR/.chezmerge-upstream" rev-parse HEAD)
if [ "$CURRENT_SHA" != "$BASE_SHA" ]; then
  echo "FAILURE: Undo should restore the previous submodule pointer"
  exit 1
fi

LAST_MESSAGE=$(git -C "$USER_DIR" log -1 --format=%s)
if ! echo "$LAST_MESSAGE" | grep -q "^Revert \"chore(chezmerge): Merge upstream changes\"$"; then
  echo "FAILURE: Expected undo-last to create a revert commit"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Undo last reverted the completed chezmerge merge.${NC}"
