#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-inner-path-boundary"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Inner Path Boundary) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles
echo "alias ll='ls -l'" > dotfiles/.bashrc
git add dotfiles/.bashrc
git commit -m "Initial commit"
git push origin master
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local with --inner-path dotfiles ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR" \
  --inner-path "dotfiles"

echo -e "${GREEN}=== Changing sibling prefix path dotfiles2 ===${NC}"
cd "$MAINTAINER_DIR"
mkdir -p dotfiles2
echo "should be ignored" > dotfiles2/ignore.me
git add dotfiles2/ignore.me
git commit -m "Add file outside inner-path but with prefix"
git push origin master
cd "$PROJECT_ROOT"

OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --inner-path "dotfiles" \
  --dry-run)

echo "$OUTPUT"

if ! echo "$OUTPUT" | grep -q "No upstream changes detected."; then
  echo "FAILURE: Expected no changes for sibling prefix path dotfiles2/"
  exit 1
fi

echo -e "${GREEN}SUCCESS: inner-path boundary filtering works correctly.${NC}"
