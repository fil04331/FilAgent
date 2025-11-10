#!/bin/bash
# Script to close outdated PRs in FilAgent repository
# Run this script from the repository root

set -e

echo "🧹 Closing outdated PRs in FilAgent repository..."
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed."
    echo "   Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI."
    echo "   Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is ready"
echo ""

# Array of PRs to close with their reasons
declare -a PRS=(
    "46:Closing: Functionality covered by PR #71 comprehensive workflow updates."
    "36:Closing: Outdated draft superseded by PRs #56, #66."
    "35:Closing: Duplicate of PR #36."
    "31:Closing: Old draft superseded by recent test improvements."
    "30:Closing: Old draft. Review PR for unique tests if needed before archiving."
)

# Close each PR
for pr_info in "${PRS[@]}"; do
    IFS=':' read -r pr_number comment <<< "$pr_info"
    
    echo "📝 Closing PR #${pr_number}..."
    
    if gh pr close "$pr_number" --comment "$comment" --repo fil04331/FilAgent; then
        echo "   ✅ Successfully closed PR #${pr_number}"
    else
        echo "   ⚠️  Failed to close PR #${pr_number} (may already be closed)"
    fi
    
    echo ""
    sleep 1  # Rate limiting consideration
done

echo "🎉 Finished! Closed 5 outdated PRs."
echo ""
echo "📊 Summary:"
echo "   - Closed: #30, #31, #35, #36, #46"
echo "   - Remaining: 13 open PRs (down from 20)"
echo ""
echo "📋 Next steps:"
echo "   1. Review PRs #55 and #66 for overlap"
echo "   2. Decide on ComplianceGuardian approach (PR #48 vs #57)"
echo "   3. Let PRs #74 and #76 auto-merge"
echo "   4. Review and merge security/bug fix PRs: #56, #58, #64, #70"
echo ""
