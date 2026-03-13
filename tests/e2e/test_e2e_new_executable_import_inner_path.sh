#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-new-executable-import-inner-path"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (New Executable Import with Inner Path) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles/.config/hypr
echo "# base" > dotfiles/.config/hypr/hyprland.conf

git add .
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR" \
  --inner-path "dotfiles"

echo -e "${GREEN}=== Adding New Upstream Executable File ===${NC}"
cd "$MAINTAINER_DIR"
mkdir -p dotfiles/.config/ml4w/scripts
cat > dotfiles/.config/ml4w/scripts/ml4w-toggle-allfloat <<'SCRIPT'
#!/usr/bin/env bash
echo "toggle all float"
SCRIPT
chmod +x dotfiles/.config/ml4w/scripts/ml4w-toggle-allfloat

git add .
git commit -m "Add new executable script"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --inner-path "dotfiles"

TARGET="$USER_DIR/dot_config/ml4w/scripts/executable_ml4w-toggle-allfloat"
LEGACY="$USER_DIR/dot_config/ml4w/scripts/ml4w-toggle-allfloat"

if [ ! -f "$TARGET" ]; then
  echo "FAILURE: Expected imported executable at $TARGET"
  echo "Current files:"
  ls -R "$USER_DIR/dot_config/ml4w/scripts" || true
  exit 1
fi

if [ -f "$LEGACY" ]; then
  echo "FAILURE: Expected executable_ mapped filename, but found legacy path $LEGACY"
  exit 1
fi

if ! grep -q 'toggle all float' "$TARGET"; then
  echo "FAILURE: Imported file content mismatch in $TARGET"
  exit 1
fi

echo -e "${GREEN}SUCCESS: New upstream executable was auto-imported with executable_ mapping.${NC}"
