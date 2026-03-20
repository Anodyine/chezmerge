#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-missing-local-delete"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Missing Local Delete) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles/.config/ml4w/scripts/arch
echo "echo printers" > dotfiles/.config/ml4w/scripts/arch/installprinters.sh
git add .
git commit -m "Initial commit with script"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR" \
  --inner-path "dotfiles"

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

echo -e "${GREEN}=== Removing Local Counterpart Manually ===${NC}"
rm -f "$USER_DIR/dot_config/ml4w/scripts/arch/installprinters.sh"
git -C "$USER_DIR" add -A
git -C "$USER_DIR" commit -m "Remove local counterpart" >/dev/null

echo -e "${GREEN}=== Deleting File Upstream ===${NC}"
cd "$MAINTAINER_DIR"
git rm dotfiles/.config/ml4w/scripts/arch/installprinters.sh
git commit -m "Delete script upstream"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --inner-path "dotfiles")

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "manual resolution required"; then
  echo "FAILURE: Missing local counterpart for upstream delete should not require manual resolution"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "upstream deleted, local counterpart already absent"; then
  echo "FAILURE: Expected auto-skip message for already-absent local counterpart"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Missing local counterpart on delete is handled automatically.${NC}"
