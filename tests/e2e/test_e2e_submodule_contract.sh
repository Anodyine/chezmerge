#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-submodule-contract"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Submodule Contract) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
echo "alias ll='ls -l'" > .bashrc
git add .
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

# 2. Initialize Local
echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# 3. Verify Submodule Contract
echo -e "${GREEN}=== Verifying Submodule Contract ===${NC}"

if ! grep -q 'path = .chezmerge-upstream' "$USER_DIR/.gitmodules"; then
    echo "FAILURE: .gitmodules is missing .chezmerge-upstream path."
    cat "$USER_DIR/.gitmodules"
    exit 1
fi

if grep -q '\.external_sources' "$USER_DIR/.gitmodules"; then
    echo "FAILURE: .gitmodules unexpectedly contains .external_sources."
    cat "$USER_DIR/.gitmodules"
    exit 1
fi

SUBMODULE_LINES=$(git -C "$USER_DIR" ls-files --stage | grep '^160000' || true)
SUBMODULE_COUNT=$(echo "$SUBMODULE_LINES" | sed '/^$/d' | wc -l)

if [ "$SUBMODULE_COUNT" -ne 1 ]; then
    echo "FAILURE: Expected exactly 1 tracked submodule, found $SUBMODULE_COUNT."
    echo "$SUBMODULE_LINES"
    exit 1
fi

if ! echo "$SUBMODULE_LINES" | grep -q '\.chezmerge-upstream$'; then
    echo "FAILURE: Tracked submodule is not .chezmerge-upstream."
    echo "$SUBMODULE_LINES"
    exit 1
fi

echo -e "${GREEN}SUCCESS: Only .chezmerge-upstream is tracked as a submodule.${NC}"
