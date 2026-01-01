# QA Plan 2: End-to-End Workflow (Real Upstream)

## Objective
Verify the full lifecycle using a real public repository that you control. This allows us to test the "Init" phase with real network cloning and the "Update" phase by actually pushing changes to the upstream repository.

## Prerequisites
1.  `uv` installed.
2.  `git` installed.
3.  A GitHub account (or similar git hosting service).

## Test Steps

### 1. Setup "Upstream" Repository
We need a repository to act as the source dotfiles.

1.  **Create Repo**: Go to GitHub and create a new **public** repository named `chezmerge-test-dots`.
2.  **Clone as Maintainer**: Open a terminal and clone this repo to a temporary location. This represents the "Maintainer's Workstation".
    ```bash
    git clone https://github.com/<YOUR_USERNAME>/chezmerge-test-dots.git /tmp/upstream-maintainer
    cd /tmp/upstream-maintainer
    ```
3.  **Add Initial Files**:
    ```bash
    # Create a basic bashrc
    echo "alias ll='ls -l'" > .bashrc
    # Create a basic vimrc
    echo "set number" > .vimrc
    
    git add .
    git commit -m "Initial commit"
    git push
    ```

### 2. Test Initialization (The User)
Now act as the user installing these dotfiles.

1.  **Prepare Local Directory**:
    ```bash
    rm -rf /tmp/local-chezmoi
    ```
2.  **Run Initialization**:
    ```bash
    # Run from your project root
    uv run src/chezmerge/main.py \
      --repo https://github.com/<YOUR_USERNAME>/chezmerge-test-dots.git \
      --source /tmp/local-chezmoi
    ```

**Verification:**
*   Check `/tmp/local-chezmoi`.
*   It should contain `dot_bashrc` and `dot_vimrc`.
*   It should contain `.merge_workspace/base` and `.merge_workspace/latest`.

### 3. Create Divergence (The "Merge" Scenario)

**A. Update Upstream (Theirs)**
Act as the maintainer again.
```bash
cd /tmp/upstream-maintainer
echo "alias gs='git status'" >> .bashrc
git commit -am "Add git alias"
git push
```

**B. Update Local (Ours)**
Act as the user customizing their files.
```bash
# Edit the local chezmoi source file
echo "# My local customization" >> /tmp/local-chezmoi/dot_bashrc
```

### 4. Test Update Workflow
Run `chezmerge` again. It should fetch the new commits from GitHub and detect the conflict.

```bash
uv run src/chezmerge/main.py \
  --repo https://github.com/<YOUR_USERNAME>/chezmerge-test-dots.git \
  --source /tmp/local-chezmoi
```

**Verification:**
1.  **TUI Launch**: The TUI should appear for `.bashrc`.
2.  **Context**:
    *   **Theirs**: Should show the new `alias gs`.
    *   **Ours**: Should show `# My local customization`.
3.  **Action**:
    *   Edit the **Template** pane to combine them:
        ```bash
        alias ll='ls -l'
        alias gs='git status'
        # My local customization
        ```
    *   Press `Ctrl+S`.
4.  **Result**:
    *   App exits.
    *   Check `/tmp/local-chezmoi/dot_bashrc`. It should contain the combined content.
    *   Run the command again. It should say "No upstream changes detected".
```
