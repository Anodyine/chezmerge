#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-wrong-directory"
HOME_DIR="$TEST_ROOT/home"
EXPECTED_SOURCE="$HOME_DIR/.local/share/chezmoi"
OTHER_DIR="$TEST_ROOT/not-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Wrong Directory Guard) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$EXPECTED_SOURCE" "$OTHER_DIR"

echo -e "${GREEN}=== Running Chezmerge Outside Chezmoi Source ===${NC}"
cd "$OTHER_DIR"
OUTPUT=$(HOME="$HOME_DIR" uv run --directory "$PROJECT_ROOT" -m chezmerge.main --inner-path dotfiles)

echo "$OUTPUT"

if ! echo "$OUTPUT" | grep -q "Refusing to run outside your chezmoi source directory"; then
  echo "FAILURE: Expected wrong-directory guard message"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "Expected chezmoi source: $EXPECTED_SOURCE"; then
  echo "FAILURE: Expected message to include the resolved chezmoi source path"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Wrong-directory runs are rejected with a clear message.${NC}"
