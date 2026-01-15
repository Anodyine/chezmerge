#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-automerge"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Auto Merge) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

# Create initial content with enough lines to separate changes
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
# Create a 10-line file
for i in {1..10}; do echo "Line $i"; done > .config
git add .
git commit -m "Initial commit"
git push origin master
cd "$PROJECT_ROOT"

# 2. Initialize Local
echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# 3. Create Non-Overlapping Divergence

# A. Modify Upstream (Change Line 1)
echo -e "${GREEN}=== Modifying Upstream (Line 1) ===${NC}"
cd "$MAINTAINER_DIR"
# Replace Line 1
sed -i.bak 's/^Line 1$/Line 1 Modified Remote/' .config && rm .config.bak
git commit -am "Update Line 1"
git push
cd "$PROJECT_ROOT"

# B. Modify Local (Change Line 10)
echo -e "${GREEN}=== Modifying Local (Line 10) ===${NC}"
# Replace Line 10
sed -i.bak 's/^Line 10$/Line 10 Modified Local/' "$USER_DIR/dot_config" && rm "$USER_DIR/dot_config.bak"

# 4. Run Update (Dry Run to check detection)
echo -e "${GREEN}=== Running Update (Dry Run) ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --dry-run)

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "dot_config \[AUTO_MERGEABLE\]"; then
    echo -e "${GREEN}SUCCESS: Detected as AUTO_MERGEABLE.${NC}"
else
    echo "FAILURE: Did not detect as AUTO_MERGEABLE."
    exit 1
fi

# 5. Run Actual Update
echo -e "${GREEN}=== Running Actual Update ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# 6. Verify Content
echo -e "${GREEN}=== Verifying Merged Content ===${NC}"
CONTENT=$(cat "$USER_DIR/dot_config")
echo "$CONTENT"

if echo "$CONTENT" | grep -q "Line 1 Modified Remote" && echo "$CONTENT" | grep -q "Line 10 Modified Local"; then
    echo -e "${GREEN}SUCCESS: Both changes are present.${NC}"
else
    echo "FAILURE: Merge failed. Missing one or both changes."
    exit 1
fi
