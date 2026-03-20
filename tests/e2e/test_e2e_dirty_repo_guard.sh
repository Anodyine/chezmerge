#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-dirty-guard"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Dirty Repo Guard) ===${NC}"
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

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

echo -e "${GREEN}=== Making Local Repo Dirty ===${NC}"
echo "# scratch" >> "$USER_DIR/dot_zshrc"

echo -e "${GREEN}=== Running Chezmerge Against Dirty Repo ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR")

echo "$OUTPUT"

if ! echo "$OUTPUT" | grep -q "Refusing to run because the repository has pending changes"; then
  echo "FAILURE: Expected dirty repo guard message"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Dirty repositories are rejected before merge work begins.${NC}"
