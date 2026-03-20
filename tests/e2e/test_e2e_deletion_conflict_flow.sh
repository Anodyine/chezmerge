#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-deletion-conflict"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Deletion Conflict) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

echo "base line" > .zshrc
git add .zshrc
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

echo -e "${GREEN}=== Modifying Local File ===${NC}"
echo "local customization" >> "$USER_DIR/dot_zshrc"

echo -e "${GREEN}=== Deleting Upstream File ===${NC}"
cd "$MAINTAINER_DIR"
git rm .zshrc
git commit -m "Delete zshrc upstream"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update (Dry Run) ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --dry-run)

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "manual resolution"; then
  echo "FAILURE: Deletion conflict should enter the merge flow instead of aborting for manual resolution"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "dot_zshrc \\[DELETION_CONFLICT\\]"; then
  echo "FAILURE: Expected deletion conflict to be surfaced as a merge item"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Deletion conflict is routed through the merge flow.${NC}"
