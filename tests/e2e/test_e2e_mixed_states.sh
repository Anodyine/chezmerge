#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-mixed"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Mixed States) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream with 4 files
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
# Use dotfiles so they get mapped to dot_ prefix locally
echo "content v1" > .f_synced
echo "content v1" > .f_local_mod
echo "content v1" > .f_remote_mod
echo "content v1" > .f_both_mod
git add .
git commit -m "Initial commit"
git push origin master
cd "$PROJECT_ROOT"

# 2. Initialize Local
echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# 3. Create Divergences

# A. Modify Upstream (Theirs)
echo -e "${GREEN}=== Modifying Upstream ===${NC}"
cd "$MAINTAINER_DIR"
echo "content v2 remote" > .f_remote_mod
echo "content v2 remote" > .f_both_mod
git commit -am "Upstream changes"
git push
cd "$PROJECT_ROOT"

# B. Modify Local (Ours)
echo -e "${GREEN}=== Modifying Local ===${NC}"
echo "content v1 local" > "$USER_DIR/dot_f_local_mod"
echo "content v1 local" > "$USER_DIR/dot_f_both_mod"

# 4. Run Update (Dry Run)
echo -e "${GREEN}=== Running Update (Dry Run) ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --dry-run)

echo "$OUTPUT"

# 5. Verify States

# Case 1: Synced File
# Should NOT appear in the output list because it hasn't changed upstream
if echo "$OUTPUT" | grep -q "dot_f_synced"; then
    echo "FAILURE: dot_f_synced should not be processed (no upstream changes)."
    exit 1
else
    echo -e "${GREEN}SUCCESS: dot_f_synced correctly ignored.${NC}"
fi

# Case 2: Local Only Change
# Should NOT appear in the output list because it hasn't changed upstream
if echo "$OUTPUT" | grep -q "dot_f_local_mod"; then
    echo "FAILURE: dot_f_local_mod should not be processed (no upstream changes)."
    exit 1
else
    echo -e "${GREEN}SUCCESS: dot_f_local_mod correctly ignored (Local changes kept).${NC}"
fi

# Case 3: Remote Only Change
# Should be identified as AUTO_UPDATE
if echo "$OUTPUT" | grep -q "dot_f_remote_mod \[AUTO_UPDATE\]"; then
    echo -e "${GREEN}SUCCESS: dot_f_remote_mod identified as AUTO_UPDATE.${NC}"
else
    echo "FAILURE: dot_f_remote_mod not identified as AUTO_UPDATE."
    exit 1
fi

# Case 4: Both Changed (Conflict)
# Should be identified as CONFLICT
if echo "$OUTPUT" | grep -q "dot_f_both_mod \[CONFLICT\]"; then
    echo -e "${GREEN}SUCCESS: dot_f_both_mod identified as CONFLICT.${NC}"
else
    echo "FAILURE: dot_f_both_mod not identified as CONFLICT."
    exit 1
fi

echo -e "${GREEN}=== All Mixed State Tests Passed ===${NC}"
