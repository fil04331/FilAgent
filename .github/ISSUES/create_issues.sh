#!/bin/bash
# Script to create GitHub issues from markdown files
# Usage: ./create_issues.sh
# Requires: gh CLI authenticated

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Creating GitHub issues for HTN Orchestration Refactor..."
echo "========================================================="

# Issue 1: TypedResult
echo ""
echo "[1/7] Creating issue: TypedResult"
gh issue create \
    --title "[Refactor] Implement TypedResult class for structured result preservation" \
    --label "enhancement,refactor,htn-planning,priority-p0" \
    --body-file "$SCRIPT_DIR/issue-1-typed-result.md"

# Issue 2: ResultReference
echo ""
echo "[2/7] Creating issue: ResultReference"
gh issue create \
    --title "[Refactor] Implement ResultReference for declarative result chaining" \
    --label "enhancement,refactor,htn-planning,priority-p0" \
    --body-file "$SCRIPT_DIR/issue-2-result-reference.md"

# Issue 3: Enhanced TaskExecutor
echo ""
echo "[3/7] Creating issue: Enhanced TaskExecutor"
gh issue create \
    --title "[Refactor] Enhance TaskExecutor with automatic ResultReference resolution" \
    --label "enhancement,refactor,htn-planning,priority-p0" \
    --body-file "$SCRIPT_DIR/issue-3-enhanced-task-executor.md"

# Issue 4: Aggregator
echo ""
echo "[4/7] Creating issue: Aggregator"
gh issue create \
    --title "[Feature] Implement Aggregator for multi-source result merging" \
    --label "enhancement,feature,htn-planning,priority-p1" \
    --body-file "$SCRIPT_DIR/issue-4-aggregator.md"

# Issue 5: Transformer
echo ""
echo "[5/7] Creating issue: Transformer"
gh issue create \
    --title "[Feature] Implement Transformer for format conversion pipeline" \
    --label "enhancement,feature,htn-planning,priority-p1" \
    --body-file "$SCRIPT_DIR/issue-5-transformer.md"

# Issue 6: OrchestrationPlan
echo ""
echo "[6/7] Creating issue: OrchestrationPlan"
gh issue create \
    --title "[Feature] Implement OrchestrationPlan builder for multi-source pipelines" \
    --label "enhancement,feature,htn-planning,priority-p1" \
    --body-file "$SCRIPT_DIR/issue-6-orchestration-plan.md"

# Issue 7: Enhanced HierarchicalPlanner
echo ""
echo "[7/7] Creating issue: Enhanced HierarchicalPlanner"
gh issue create \
    --title "[Feature] Enhance HierarchicalPlanner with orchestration detection and planning" \
    --label "enhancement,feature,htn-planning,priority-p2" \
    --body-file "$SCRIPT_DIR/issue-7-enhanced-planner.md"

echo ""
echo "========================================================="
echo "All 7 issues created successfully!"
echo ""
echo "Issue dependency order:"
echo "  #1 TypedResult (P0) ─┬─> #2 ResultReference (P0) ──> #3 TaskExecutor (P0)"
echo "                       │"
echo "                       ├─> #4 Aggregator (P1)"
echo "                       │"
echo "                       └─> #5 Transformer (P1)"
echo ""
echo "  #3, #4, #5 ──────────> #6 OrchestrationPlan (P1) ──> #7 Enhanced Planner (P2)"
