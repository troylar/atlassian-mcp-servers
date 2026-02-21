---
name: deploy
description: Merge PR, verify CI, bump version, and publish to PyPI
allowed-tools: Bash, Read, Edit, Grep, Glob, WebFetch
---

# /deploy Skill

Deploy a server update: merge PR, verify CI, bump version, publish to PyPI.

## Usage

```
/deploy              # Auto-detect PR, server, and version bump
/deploy patch        # Force patch bump
/deploy minor        # Force minor bump
/deploy major        # Force major bump
```

## Workflow

### Step 1: Pre-flight Checks

1. Confirm on a feature branch (not main)
2. Find open PR: `gh pr view --json number,title,state,mergeable`
3. Verify every commit references a GitHub issue
4. Determine which server(s) this PR modifies

### Step 1b: PR Queue Context

```bash
gh pr list --state open --json number,title,headRefName,mergeable
```

Show all open PRs so the user understands the deploy queue.

### Step 2: Quick Documentation Check

1. Check if README changes are needed for new tools
2. Note the pre-bump version in the server's `pyproject.toml`

### Step 3: Rebase, Validate, and Merge

#### 3a. Check if main has moved
```bash
git fetch origin main
MERGE_BASE=$(git merge-base HEAD origin/main)
MAIN_HEAD=$(git rev-parse origin/main)
```

#### 3b. Rebase
```bash
git rebase origin/main
git push --force-with-lease
```

#### 3c. Wait for CI
Poll `gh pr checks` every 15 seconds, up to 10 minutes.

#### 3d. Evaluate checks
- All pass: proceed
- Non-required fail: proceed with `--admin`, log bypass
- Required fail: abort

#### 3e. Merge (worktree-aware)
```bash
gh pr merge <PR> --squash
```

Clean up worktree if applicable:
```bash
WORKTREE_PATH=$(git rev-parse --show-toplevel)
MAIN_WORKTREE=$(git worktree list --porcelain | grep -A0 'worktree ' | head -1 | sed 's/worktree //')
if [ "$WORKTREE_PATH" != "$MAIN_WORKTREE" ]; then
    BRANCH=$(git branch --show-current)
    cd "$MAIN_WORKTREE"
    git worktree remove "$WORKTREE_PATH"
    git branch -d "$BRANCH" 2>/dev/null || true
fi
```

Pull merged changes: `git checkout main && git pull`

### Step 3f: Post-Merge Queue Check

Check if other PRs are now conflicting.

### Step 4: Determine Version Bump

Read the affected server's `pyproject.toml` for current version.

If user passed bump level, use it. Otherwise:
- `feat:` → minor
- `fix:`, `docs:`, `chore:` → patch
- `BREAKING CHANGE` → major

### Step 5: Create Version Commit and Tag

```bash
# Edit pyproject.toml version
git add <server>/pyproject.toml
git commit -m "chore(<server>): bump version to X.Y.Z"
git tag <server>-vX.Y.Z
git push origin main --tags --no-verify
```

### Step 6: Build and Publish

```bash
cd <server>
rm -rf dist/ build/
python -m build
twine check dist/*
twine upload dist/*
```

### Step 7: Create GitHub Release

Generate release notes from the PR and referenced issues. Categorize as New Features, Bug Fixes, Other Improvements.

```bash
gh release create <server>-vX.Y.Z --title "<server> vX.Y.Z" --notes "<notes>"
```

### Step 7b: Clean Up Issue Labels

Remove `in-progress` and `ready-for-review` from closing issues.

### Step 8: Verify

```bash
pip install <package-name>==X.Y.Z --dry-run 2>&1 | head -5
```

## Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 Deployed <server> vX.Y.Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔗 PR:       #NN (merged)
  🧪 CI:       ✅ passed
  📦 PyPI:     https://pypi.org/project/<package>/X.Y.Z/
  🏷️ Tag:      <server>-vX.Y.Z
  📊 Version:  X.Y.Z-1 → X.Y.Z (<type> bump)

────────────────────────────────────────────
  ✅ Deploy complete
────────────────────────────────────────────
```

## Error Handling

- Merge fails: show error, stop
- CI fails: show URL, stop
- Build fails: show error, stop
- Upload fails: tag exists, suggest manual `twine upload`
- Never force-push to main
