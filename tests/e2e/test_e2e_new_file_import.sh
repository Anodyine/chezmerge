#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-new-file-import"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (New File Import) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

echo "alias ll='ls -l'" > .bashrc
git add .bashrc
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

echo -e "${GREEN}=== Adding New Upstream File ===${NC}"
cd "$MAINTAINER_DIR"
echo "set number" > .vimrc
git add .vimrc
git commit -m "Add vimrc"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR"

if [ ! -f "$USER_DIR/dot_vimrc" ]; then
  echo "FAILURE: New upstream file was not imported to dot_vimrc"
  exit 1
fi

if ! grep -q "set number" "$USER_DIR/dot_vimrc"; then
  echo "FAILURE: Imported dot_vimrc content mismatch"
  exit 1
fi

echo -e "${GREEN}SUCCESS: New upstream file imported correctly.${NC}"
