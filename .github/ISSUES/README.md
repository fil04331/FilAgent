# HTN Orchestration Refactor - GitHub Issues

This directory contains 7 GitHub issue templates for the HTN-Planning refactor to support multi-source orchestration with intermediate transformations.

## Issue Summary

| # | Title | Priority | Estimated Effort |
|---|-------|----------|------------------|
| 1 | TypedResult - Structured result preservation | P0 | 2-3 days |
| 2 | ResultReference - Declarative result chaining | P0 | 1-2 days |
| 3 | Enhanced TaskExecutor - Automatic resolution | P0 | 3-4 days |
| 4 | Aggregator - Multi-source result merging | P1 | 2-3 days |
| 5 | Transformer - Format conversion pipeline | P1 | 3-4 days |
| 6 | OrchestrationPlan - High-level plan builder | P1 | 3-4 days |
| 7 | Enhanced HierarchicalPlanner - Auto-detection | P2 | 4-5 days |

**Total Estimated Effort**: 18-25 days

## Dependency Graph

```
┌─────────────────┐
│  #1 TypedResult │ (P0 - Foundation)
└────────┬────────┘
         │
    ┌────┴────┬──────────────────┐
    │         │                  │
    ▼         ▼                  ▼
┌───────┐ ┌───────┐         ┌────────┐
│ #2    │ │ #4    │         │ #5     │
│Result │ │Aggreg │         │Transf  │
│Ref    │ │ator   │         │ormer   │
└───┬───┘ └───┬───┘         └────┬───┘
    │         │                  │
    ▼         │                  │
┌───────┐     │                  │
│ #3    │     │                  │
│Task   │◄────┴──────────────────┘
│Exec   │
└───┬───┘
    │
    ▼
┌─────────────────┐
│ #6 Orchestration│ (P1)
│     Plan        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ #7 Enhanced     │ (P2)
│    Planner      │
└─────────────────┘
```

## How to Create Issues

### Option 1: Using the script (requires `gh` CLI)

```bash
chmod +x create_issues.sh
./create_issues.sh
```

### Option 2: Manual creation via GitHub Web

1. Go to your repository's Issues page
2. Click "New Issue"
3. Copy-paste the content from each `issue-*.md` file
4. Add appropriate labels and milestone

### Option 3: Using `gh` CLI manually

```bash
gh issue create \
    --title "[Refactor] Implement TypedResult class" \
    --label "enhancement,refactor,htn-planning" \
    --body-file issue-1-typed-result.md
```

## Labels to Create

Before creating issues, ensure these labels exist:

- `enhancement` - New feature or improvement
- `refactor` - Code refactoring
- `feature` - New feature
- `htn-planning` - HTN planning system
- `priority-p0` - Critical priority
- `priority-p1` - High priority
- `priority-p2` - Medium priority

## Sprint Planning

### Sprint 1 (Week 1-2): Foundation
- [ ] Issue #1: TypedResult
- [ ] Issue #2: ResultReference

### Sprint 2 (Week 2-3): Execution Engine
- [ ] Issue #3: Enhanced TaskExecutor

### Sprint 3 (Week 3-4): Pipeline Components
- [ ] Issue #4: Aggregator
- [ ] Issue #5: Transformer

### Sprint 4 (Week 4-5): Integration
- [ ] Issue #6: OrchestrationPlan
- [ ] Issue #7: Enhanced HierarchicalPlanner

### Sprint 5 (Week 5-6): Testing & Documentation
- End-to-end testing
- Performance benchmarks
- Documentation updates
