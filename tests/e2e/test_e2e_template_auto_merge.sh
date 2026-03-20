#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}/src"

TEST_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

UPSTREAM_DIR="$TEST_DIR/upstream"
LOCAL_DIR="$TEST_DIR/local"
CHEZMOI_CONFIG_FILE="$TEST_DIR/chezmoi.toml"

echo "Running Template Auto-Merge E2E Test..."
echo "Test Directory: $TEST_DIR"

cat > "$CHEZMOI_CONFIG_FILE" <<'EOF'
[data]
ls_flags = "l"
EOF
export CHEZMOI_CONFIG="$CHEZMOI_CONFIG_FILE"

mkdir -p "$UPSTREAM_DIR"
cd "$UPSTREAM_DIR"
git init --quiet
git config user.email "test@example.com"
git config user.name "Test User"
cat > .bashrc <<'EOF'
line 1
line 2
line 3
line 4
line 5
line 6
line 7
line 8
line 9
alias ll='ls -l'
EOF
git add .bashrc
git commit -m "Initial commit" --quiet

mkdir -p "$LOCAL_DIR"
cat > "$LOCAL_DIR/dot_bashrc.tmpl" <<'EOF'
line 1
line 2
line 3
line 4
line 5
line 6
line 7
line 8
line 9
alias ll='ls -{{ .ls_flags }}'
EOF

echo "--- Initializing Chezmerge ---"
uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" > /dev/null
git -C "$LOCAL_DIR" add .
git -C "$LOCAL_DIR" commit -m "Baseline import" --quiet

echo "--- Updating Upstream ---"
cd "$UPSTREAM_DIR"
cat > .bashrc <<'EOF'
line 1 updated upstream
line 2
line 3
line 4
line 5
line 6
line 7
line 8
line 9
alias ll='ls -l'
EOF
git add .bashrc
git commit -m "Update PATH" --quiet

echo "--- Running Chezmerge (Dry Run) ---"
OUTPUT=$(uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" --dry-run)

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "dot_bashrc.tmpl \[AUTO_MERGEABLE\]"; then
    echo "SUCCESS: Template detected as auto-mergeable."
else
    echo "FAILURE: Expected AUTO_MERGEABLE for dot_bashrc.tmpl"
    echo "Got output:"
    echo "$OUTPUT"
    exit 1
fi

echo "--- Running Chezmerge ---"
uv run python -m chezmerge.main --repo "$UPSTREAM_DIR" --source "$LOCAL_DIR" > /dev/null

echo "--- Verifying merged template source ---"
TARGET_FILE="$LOCAL_DIR/dot_bashrc.tmpl"
cat "$TARGET_FILE"

if grep -q "line 1 updated upstream" "$TARGET_FILE" \
    && grep -q "alias ll='ls -{{ .ls_flags }}'" "$TARGET_FILE"; then
    echo "SUCCESS: Upstream change merged into template source without losing template logic."
else
    echo "FAILURE: Template source did not contain expected merged content."
    exit 1
fi
