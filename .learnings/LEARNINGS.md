## [LRN-20260505-001] correction

**Logged**: 2026-05-05T22:45:00+02:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
When resolving merge conflicts, always verify ALL conflict markers are removed before committing. The `git diff --check` command only checks for conflict markers in the working tree, not in the index/staged files.

### Details
During F-02 merge conflict resolution, I used `git checkout --theirs` for most files but `README.md` and `03-backlog.md` retained conflict markers (`<<<<<<< HEAD`, `=======`, `>>>>>>>`) even after staging. The conflict markers were not caught by `git diff --check` because the files were already staged.

The correct workflow should be:
1. Resolve conflicts with `git checkout --ours` or `--theirs`
2. Manually verify with `grep -rn "<<<<<<<" files` 
3. Stage with `git add`
4. Commit

### Suggested Action
Always run `grep` to verify no conflict markers remain, regardless of `git diff --check` output.

### Metadata
- Source: error
- Related Files: README.md, 03-backlog.md
- Tags: git, merge-conflicts, workflow
- Pattern-Key: git.verify_no_conflicts
- Recurrence-Count: 1
- First-Seen: 2026-05-05
- Last-Seen: 2026-05-05

---
