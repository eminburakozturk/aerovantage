# ADR-002: Navigation and Workspace Single Source of Truth

## Problem
Navigation paths, default tabs, and page metadata were split between `nav-config.ts` and `workspace-config.ts`. This created drift risk and duplicated route-specific knowledge.

## Decision
Treat `workspace-config.ts` as the canonical source for workspace routes and metadata. Consume it from `nav-config.ts` for:
- workspace navigation links
- default tab interpretation
- page metadata mapping for workspace pages

Also introduce `src/lib/routes.ts` for non-workspace core routes (`/`, `/operations`, `/activity`) used by layout components.

## Rationale
- Reduces duplicate literals and route drift
- Keeps layout-level navigation behavior backward-compatible
- Makes future workspace changes one-edit operations

## Consequences
- `workspace-config.ts` now carries stronger ownership of workspace identity
- New workspace additions must be registered once in `WORKSPACES`
- Route integrity is improved, and link consistency in layout is easier to maintain

