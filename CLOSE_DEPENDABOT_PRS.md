# Instructions for Closing Dependabot PRs

## PRs to Close Manually

Since the `gh` CLI is not available, please manually close the following Dependabot PRs on GitHub:

### ❌ Close These PRs:

#### 1. TailwindCSS v4 Update (CRITICAL - DO NOT MERGE)
**Branch:** `dependabot/npm_and_yarn/src/agcluster/container/ui/tailwindcss-4.1.16`

**Close with this comment:**
```
Closing this PR as TailwindCSS v4 introduces breaking changes that require extensive refactoring.

The project already attempted upgrading to v4 and had to roll back due to stability issues:
- Commit e67e97a: "fix: downgrade to TailwindCSS v3 for stability"
- Commit 6877ba3: "fix: replace @apply directives with CSS for TailwindCSS v4 compatibility"

TailwindCSS v4 requires:
- Complete configuration migration (from JS to CSS-first config)
- Rewriting all @apply directives
- Testing entire UI for visual regressions
- Build pipeline updates

We've configured Dependabot to block future TailwindCSS major update PRs. When we're ready to migrate to v4, it will be planned as a dedicated project with proper QA.

See DEPENDABOT_PR_REVIEW.md for full analysis.
```

#### 2. Next.js 16 Update (Requires Extensive Testing)
**Branch:** `dependabot/npm_and_yarn/src/agcluster/container/ui/next-16.0.1`

**Close with this comment:**
```
Closing this PR as Next.js 16 is a major version update that requires extensive testing and may include breaking changes.

Before upgrading to Next.js 16, we need to:
- Review the Next.js 16 migration guide
- Test all pages and routes
- Verify API endpoints work correctly
- Test file upload functionality
- Run full test suite
- Perform thorough QA

We've configured Dependabot to block future Next.js major update PRs. The upgrade to Next.js 16 should be planned separately with dedicated QA time.

See DEPENDABOT_PR_REVIEW.md for full analysis.
```

#### 3. actions/setup-node v6 Update (Needs CI/CD Testing)
**Branch:** `dependabot/github_actions/actions/setup-node-6`

**Close with this comment:**
```
Closing this PR as it's a major version update (v4 → v6, skipping v5) for our GitHub Actions workflow.

While this is likely safe, it should be tested in CI/CD before merging to ensure:
- Node.js caching still works correctly
- Build processes complete successfully
- No workflow runtime issues

This can be revisited when we have time to properly test the workflow changes.

See DEPENDABOT_PR_REVIEW.md for full analysis.
```

---

## PRs Already Merged ✅

The following 8 safe PRs have been merged into branch `claude/review-dependabot-prs-011CUm235iZViKUL4LNNiko8`:

1. ✅ **ai**: 5.0.81 → 5.0.86 (patch)
2. ✅ **@ai-sdk/react**: 2.0.81 → 2.0.86 (patch)
3. ✅ **eslint-config-next**: 16.0.0 → 16.0.1 (patch)
4. ✅ **lucide-react**: 0.548.0 → 0.552.0 (minor)
5. ✅ **@types/node**: 24.9.1 → 24.10.0 (minor)
6. ✅ **vitest**: 4.0.4 → 4.0.6 (patch)
7. ✅ **@vitest/coverage-v8**: 4.0.4 → 4.0.6 (patch)
8. ✅ **@vitest/ui**: 4.0.4 → 4.0.6 (patch)

These are low-risk patch and minor version updates that maintain backward compatibility.

---

## Dependabot Configuration Updated ⚙️

Updated `.github/dependabot.yml` to prevent future PRs for:
- TailwindCSS major updates
- Next.js major updates
- eslint-config-next major updates

This prevents Dependabot from automatically creating PRs for changes that require careful planning and extensive testing.

---

## Next Steps

1. Close the 3 PRs listed above on GitHub with the provided comments
2. Review and merge this PR (`claude/review-dependabot-prs-011CUm235iZViKUL4LNNiko8`)
3. The 8 merged dependency updates will go live
4. Dependabot will stop creating PRs for TailwindCSS/Next.js major updates

---

**Created:** 2025-11-03
**Branch:** claude/review-dependabot-prs-011CUm235iZViKUL4LNNiko8
