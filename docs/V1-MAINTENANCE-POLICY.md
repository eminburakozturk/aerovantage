# AeroVantage v1.x Maintenance Policy

> **Status:** AeroVantage **v1.x is Feature Complete** and in **Maintenance Mode**.  
> The v1.x product development cycle is **closed** as of `v1.0.0-rc1` (Sprint G5).  
> Primary future development focus: **Hyper Core** — [`HYPER-CORE.md`](HYPER-CORE.md).  
> This document defines what may change on v1.x after the locked final roadmap. It complements — and does not replace — [`AEROVANTAGE-FINAL-ROADMAP.md`](AEROVANTAGE-FINAL-ROADMAP.md).

---

## Purpose

After this version, primary goals are **Stability**, **Maintenance**, **Security**, and **Quality** — **not** new feature development.

---

## Current freeze status

| Freeze / gate | Status |
|---------------|--------|
| Feature Freeze | **Active** |
| UI Freeze | **Active** |
| Architecture Freeze | **Active** |
| Repository Freeze | **Active** (no unsolicited GitHub push / publish) |
| Release status | **v1.0.0-rc1 tagged** · **Maintenance Mode active** |
| Primary focus (post-RC1) | **Hyper Core** — see [`HYPER-CORE.md`](HYPER-CORE.md) |

New product work is out of scope for v1.x. Record future ideas in [`V2-BACKLOG.md`](V2-BACKLOG.md).

---

## Allowed in v1.x

| Category | Notes |
|----------|--------|
| Bug fix | Correct broken or incorrect behavior |
| Security fix | Vulnerabilities, credential posture, auth hardening |
| Performance optimization | Same behavior, better resource use / latency |
| Documentation update | Policy, runbooks, checklists, user guides |
| Dependency update | Patches / safe upgrades that preserve behavior |
| UI polish | Visual or copy polish **with no behavior change** |
| Accessibility improvement | A11y without new product surfaces |
| Localization improvement | Existing locales / missing keys; no new product locales required |
| Test coverage improvement | Tests for existing behavior |
| Build / CI improvement | Gates, scripts, packaging hygiene |
| Deployment improvement | Ops docs, compose/scripts hardening — no new product architecture |

---

## Not allowed in v1.x

| Category | Examples |
|----------|----------|
| New dashboard | Additional executive or ops dashboards |
| New workspace | New workspace routes or shells |
| New AI module | New agents, briefing types, or AI product surfaces |
| New data source | New connectors beyond current EPİAŞ / weather / SCADA posture |
| New business logic | Domain rules that change decisions or product meaning |
| Large architecture change | New layers, rewrite of pipeline core, BFF redesign |
| New API surface | New public endpoints or breaking contract expansion for features |
| New pipeline | Extra pipeline stages or parallel product pipelines |
| New feature | Anything that expands product scope beyond Feature Complete v1.x |

---

## New ideas

- **Do not implement** new ideas in v1.x.
- Write all proposed product / architecture ideas to [`docs/V2-BACKLOG.md`](V2-BACKLOG.md).
- No new features enter v1.x until **v2.0 planning** formally starts.

Historical sprint tracking remains in [`docs/backlog.md`](backlog.md) (locked to the final roadmap). It is **not** a channel for new v1.x scope.

---

## Release rule (v1.x)

Ship **only** Bug / Security / Performance / Maintenance releases under the v1.x line.

**Examples:** `v1.0.1`, `v1.0.2`, `v1.1`

Do **not** use a v1.x bump to introduce new product features.

---

## Major version rule (v2.0)

**v2.0 planning starts when** any of the following is required:

- New product vision
- Large architecture change
- New AI platform
- New dashboard system
- New workspace
- New data source
- New user type

Until then, keep ideas in the v2 backlog and keep v1.x maintenance-only.

---

## Relationship to other docs

| Document | Role |
|----------|------|
| [`AEROVANTAGE-FINAL-ROADMAP.md`](AEROVANTAGE-FINAL-ROADMAP.md) | Locked FAZ 1–7 plan (complete); still the sole historical development plan |
| [`V2-BACKLOG.md`](V2-BACKLOG.md) | Ideas only — not for v1.x implementation |
| [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md) | RC / release hygiene |
| [`backlog.md`](backlog.md) | Historical engineering backlog (frozen to final roadmap) |

---

*Policy established: 2026-07-14 — AeroVantage v1.x Feature Complete / RC1*
