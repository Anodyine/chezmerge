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
CHEZMOI_CONFIG_FILE="$TEST_DIR/chezmoi.toml"

echo "Running Template Detection E2E Test..."
echo "Test Directory: $TEST_DIR"

cat > "$CHEZMOI_CONFIG_FILE" <<'EOF'
[data]
ls_flags = "l"
EOF
export CHEZMOI_CONFIG="$CHEZMOI_CONFIG_FILE"

# 1. Setup Upstream Repo
# We simulate an upstream repo with a dotfile that maps to dot_bashrc.tmpl locally
mkdir -p "$UPSTREAM_DIR"
cd "$UPSTREAM_DIR"
git init --quiet
git config user.email "test@example.com"
git config user.name "Test User"
cat > .bashrc <<'EOF'
alias ll='ls -l'
export EDITOR=vim
EOF
git add .bashrc
git commit -m "Initial commit" --quiet

# 2. Setup Local Source (Chezmoi style)
# We simulate a local chezmoi source with a template for that file
mkdir -p "$LOCAL_DIR"
cat > "$LOCAL_DIR/dot_bashrc.tmpl" <<'EOF'
alias ll='ls -{{ .ls_flags }}'
export EDITOR=vim
EOF

# 3. Initialize Chezmerge
# This establishes the baseline
echo "--- Initializing Chezmerge ---"
uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" > /dev/null

# 4. Update Upstream
# Simulate the upstream project changing the same logical line
echo "--- Updating Upstream ---"
cd "$UPSTREAM_DIR"
cat > .bashrc <<'EOF'
alias ll='ls -lah'
export EDITOR=vim
EOF
git add .bashrc
git commit -m "Update bashrc alias" --quiet

# 5. Run Chezmerge in Dry Run mode
# We expect it to detect the change and flag it as TEMPLATE_DIVERGENCE
# because both sides changed the same line and the template source cannot
# be merged automatically.
echo "--- Running Chezmerge (Dry Run) ---"
OUTPUT=$(uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" --dry-run)

echo "$OUTPUT"

# 6. Verify Results
# We look for the specific scenario that triggers the UI
if echo "$OUTPUT" | grep -q "dot_bashrc.tmpl \[TEMPLATE_DIVERGENCE\]"; then
    echo "SUCCESS: Template divergence detected correctly."
    echo "The application would open the UI with:"
    echo "  - Bottom Pane: Raw template content (dot_bashrc.tmpl)"
    echo "  - Top Panes: Base, Theirs (upstream), and Ours (Rendered)"
else
    echo "FAILURE: Expected TEMPLATE_DIVERGENCE for dot_bashrc.tmpl"
    echo "Got output:"
    echo "$OUTPUT"
    exit 1
fi
