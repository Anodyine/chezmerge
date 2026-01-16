#!/bin/bash
set -e

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}/src"

# Setup test environment
TEST_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

UPSTREAM_DIR="$TEST_DIR/upstream"
LOCAL_DIR="$TEST_DIR/local"

echo "Running Template Detection E2E Test..."
echo "Test Directory: $TEST_DIR"

# 1. Setup Upstream Repo
# We simulate an upstream repo with a simple config file
mkdir -p "$UPSTREAM_DIR"
cd "$UPSTREAM_DIR"
git init --quiet
git config user.email "test@example.com"
git config user.name "Test User"
echo "upstream_v1" > config_file
git add config_file
git commit -m "Initial commit" --quiet

# 2. Setup Local Source (Chezmoi style)
# We simulate a local chezmoi source with a template for that file
mkdir -p "$LOCAL_DIR"
echo "local_template_v1" > "$LOCAL_DIR/config_file.tmpl"

# 3. Initialize Chezmerge
# This establishes the baseline
echo "--- Initializing Chezmerge ---"
uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" > /dev/null

# 4. Update Upstream
# Simulate the upstream project changing the file
echo "--- Updating Upstream ---"
cd "$UPSTREAM_DIR"
echo "upstream_v2" > config_file
git add config_file
git commit -m "Update config_file" --quiet

# 5. Run Chezmerge in Dry Run mode
# We expect it to detect the change and flag it as TEMPLATE_DIVERGENCE
# because the local file is a template (.tmpl) and content differs.
echo "--- Running Chezmerge (Dry Run) ---"
OUTPUT=$(uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" --dry-run)

echo "$OUTPUT"

# 6. Verify Results
# We look for the specific scenario that triggers the UI
if echo "$OUTPUT" | grep -q "config_file.tmpl \[TEMPLATE_DIVERGENCE\]"; then
    echo "SUCCESS: Template divergence detected correctly."
    echo "The application would open the UI with:"
    echo "  - Bottom Pane: Raw template content (config_file.tmpl)"
    echo "  - Top Panes: Base, Theirs (upstream), and Ours (Rendered)"
else
    echo "FAILURE: Expected TEMPLATE_DIVERGENCE for config_file.tmpl"
    echo "Got output:"
    echo "$OUTPUT"
    exit 1
fi
