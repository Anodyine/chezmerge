#!/bin/bash

# Define colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect if sourced or executed
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0

# Helper to find project root
get_project_root() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ -z "$root" || ! -f "$root/pyproject.toml" ]]; then
        return 1
    fi
    echo "$root"
}

# Function to setup the test environment
setup_visual_test() {
    echo -e "${BLUE}Setting up visual diff test environment...${NC}"
    
    PROJECT_ROOT=$(get_project_root)
    if [ -z "$PROJECT_ROOT" ]; then
        echo -e "${RED}Error: Could not detect chezmerge project root.${NC}"
        echo "Please run this command from within the chezmerge repository."
        return 1
    fi

    TEST_DIR="/tmp/chezmerge-visual-test"
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR"
    
    REPO_DIR="$TEST_DIR/upstream"
    LOCAL_DIR="$TEST_DIR/local"
    
    # 1. Create Upstream Repo (Base State)
    mkdir -p "$REPO_DIR"
    git -C "$REPO_DIR" init --initial-branch=main > /dev/null
    
    cat <<EOF > "$REPO_DIR/config.txt"
Line 01: Common Header
Line 02: Keep Unchanged
Line 03: To be DELETED by Upstream (Theirs)
Line 04: To be DELETED by Local (Ours)
Line 05: To be MODIFIED by Upstream (Theirs)
Line 06: To be MODIFIED by Local (Ours)
Line 07: Keep Unchanged
EOF
    git -C "$REPO_DIR" add config.txt
    git -C "$REPO_DIR" commit -m "Initial Base State" > /dev/null
    
    # 2. Initialize Local Workspace (Establish Baseline)
    echo "Initializing local workspace..."
    uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
        --repo "$REPO_DIR" \
        --source "$LOCAL_DIR" > /dev/null 2>&1
        
    if [ ! -d "$LOCAL_DIR/.git" ]; then
        echo -e "${RED}Error: Failed to initialize local workspace.${NC}"
        return 1
    fi

    # 3. Create Local Changes (Ours)
    # Modify the file in the local workspace
    cat <<EOF > "$LOCAL_DIR/config.txt"
Line 01: Common Header
Line 02: Keep Unchanged
Line 03: To be DELETED by Upstream (Theirs)
Line 05: To be MODIFIED by Upstream (Theirs)
Line 06: To be MODIFIED by Local (Ours) - LOCAL CHANGE
Line 07: Keep Unchanged
Line 08: ADDED by Local (Ours)
EOF

    # 4. Update Upstream (Theirs)
    # Modify the file in the upstream repo and commit
    cat <<EOF > "$REPO_DIR/config.txt"
Line 01: Common Header
Line 02: Keep Unchanged
Line 04: To be DELETED by Local (Ours)
Line 05: To be MODIFIED by Upstream (Theirs) - UPSTREAM CHANGE
Line 06: To be MODIFIED by Local (Ours)
Line 07: Keep Unchanged
Line 09: ADDED by Upstream (Theirs)
EOF
    git -C "$REPO_DIR" add config.txt
    git -C "$REPO_DIR" commit -m "Upstream Updates" > /dev/null
    
    echo -e "${GREEN}Environment ready at $TEST_DIR${NC}"
    echo "Upstream: $REPO_DIR"
    echo "Local:    $LOCAL_DIR"
}

# Function to run the test
run_visual_test() {
    TEST_DIR="/tmp/chezmerge-visual-test"
    REPO_DIR="$TEST_DIR/upstream"
    LOCAL_DIR="$TEST_DIR/local"
    
    if [ ! -d "$TEST_DIR" ]; then
        echo "Test environment not found. Run 'setup_visual_test' first."
        return
    fi

    PROJECT_ROOT=$(get_project_root)
    if [ -z "$PROJECT_ROOT" ]; then
        echo -e "${RED}Error: Could not detect chezmerge project root.${NC}"
        echo "Please run this command from within the chezmerge repository."
        return 1
    fi
    
    echo -e "${BLUE}Running chezmerge with nvim...${NC}"
    echo "Project Root: $PROJECT_ROOT"
    
    # Use --directory to run in the project context
    uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
        --repo "$REPO_DIR" \
        --source "$LOCAL_DIR" \
        --editor "nvim"
}

# Print Instructions
echo -e "${GREEN}=== Chezmerge Visual Diff Permutation Test ===${NC}"
echo ""
echo "This script loads functions into your shell to test the nvim visual highlighting."
echo ""
echo -e "0. Run ${BLUE}source tests/manual/05_visual_diff_permutations.sh${NC} to load the functions (if you haven't already)."
echo ""
echo -e "1. Run ${BLUE}setup_visual_test${NC} to create the git repos and file states."
echo "   - Creates a Base state."
echo "   - Initializes the local workspace."
echo "   - Creates Upstream changes (Theirs)."
echo "   - Creates Local changes (Ours)."
echo ""
echo -e "2. Run ${BLUE}run_visual_test${NC} to launch chezmerge."
echo "   - It will detect the conflict and launch nvim."
echo ""
echo -e "3. Verify the following in nvim:"
echo -e "   ${BLUE}Top Left (Theirs)${NC}:"
echo "     - Green background for 'ADDED by Upstream'."
echo "     - Red filler lines where 'To be DELETED by Upstream' used to be."
echo -e "   ${BLUE}Top Middle (Base)${NC}:"
echo "     - Red text for 'To be DELETED by Upstream' (Deleted in Theirs)."
echo "     - Red text for 'To be DELETED by Local' (Deleted in Ours)."
echo "     - Green filler lines where additions occurred in Theirs/Ours."
echo -e "   ${BLUE}Top Right (Ours)${NC}:"
echo "     - Green background for 'ADDED by Local'."
echo "     - Red filler lines where 'To be DELETED by Local' used to be."
echo ""
echo -e "4. Cleanup: Run ${BLUE}unset -f setup_visual_test run_visual_test${NC} to remove functions from your shell."
echo ""

if [ "$SOURCED" -eq 1 ]; then
    echo -e "To start, type: ${BLUE}setup_visual_test${NC}"
else
    echo -e "${RED}NOTE: You executed this script in a subshell.${NC}"
    echo -e "The functions are NOT available in your current shell."
    echo -e "Please run: ${GREEN}source $0${NC}"
fi
