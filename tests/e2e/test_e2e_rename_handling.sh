#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-rename-handling"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Rename Handling) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles
echo "stable content" > dotfiles/.oldname
echo "base content" > dotfiles/.modold
git add .
git commit -m "Initial commit with rename candidates"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR" \
  --inner-path "dotfiles"

echo -e "${GREEN}=== Creating Local Modification for Rename Conflict Case ===${NC}"
echo "local customized content" > "$USER_DIR/dot_modold"

echo -e "${GREEN}=== Renaming Files Upstream ===${NC}"
cd "$MAINTAINER_DIR"
git mv dotfiles/.oldname dotfiles/.newname
git mv dotfiles/.modold dotfiles/.modnew
git commit -m "Rename files upstream"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --inner-path "dotfiles")

echo "$OUTPUT"

if [ ! -f "$USER_DIR/dot_newname" ]; then
  echo "FAILURE: Unchanged renamed file was not auto-renamed to dot_newname"
  exit 1
fi

if [ -f "$USER_DIR/dot_oldname" ]; then
  echo "FAILURE: Old renamed path dot_oldname still exists after auto-rename"
  exit 1
fi

if [ ! -f "$USER_DIR/dot_modold" ]; then
  echo "FAILURE: Locally modified renamed file should remain at old path for manual resolution"
  exit 1
fi

if [ -f "$USER_DIR/dot_modnew" ]; then
  echo "FAILURE: Locally modified renamed file should not be auto-renamed"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "Rename conflict: .modold -> .modnew (local file modified)"; then
  echo "FAILURE: Expected rename conflict message for locally modified file"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Rename handling behaves as expected.${NC}"
