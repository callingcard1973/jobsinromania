---
name: expats-funnel-orchestrator
description: Use when operating the expatsinromania.org relocation funnel — triggers include "run expats daily cycle", "publish expats content / press review / job digest", "post expats jobs to Facebook", "qualify/nurture expat leads", "deploy to expats WP", or "check expats funnel status". Coordinates content publishing, social distribution, lead nurture, and cPanel deploys for the A2 WordPress site.
---

# Expats Funnel Orchestrator Skill

Trigger skill for the expatsinromania.org WordPress relocation funnel harness (EUR 300–2500 packages).

## When to use
- Daily/weekly operations cycle for expatsinromania.org.
- Any single task: publish content, distribute to FB, qualify leads, deploy WP changes.

## Agents coordinated
- `expats-funnel-orchestrator` — top-level coordinator.
- `expats-content-publisher` — WP press review (daily) + oss-jobs digest (weekly).
- `expats-social-distributor` — FB pages/groups + weekly top-salary digest.
- `expats-lead-nurture` — qualify leads → Brevo `expat-leads` → nurture + Directorist.
- `expats-cpanel-deployer` — A2 cPanel file/theme/script deploys (no SSH).
- Reuse shared: `campaign-launcher`, `bounce-monitor`, `dnc-manager`, `infrastructure-health`.

## Usage steps
1. Identify the task (full cycle vs single action) and invoke `expats-funnel-orchestrator`.
2. For content: `expats-content-publisher` (verify WP REST, run digest on raspibig via plink, confirm post URL).
3. For distribution: `expats-social-distributor` after content lands (respect FB blockers).
4. For leads: `expats-lead-nurture` (score → Brevo, GDPR consent-gated).
5. For deploys: `expats-cpanel-deployer` (backup → save_file_content → verify → clear LSCache).

## Daily/trigger cycle
| Time (UTC) | Component | Agent |
|-----------|-----------|-------|
| 07:00 | Press review | expats-content-publisher |
| 08:00 (Mon) | oss-jobs weekly digest | expats-content-publisher |
| 10:00 / 10:15 | Daily FB job posts | expats-social-distributor |
| 11:30 | Per-audience FB jobs | expats-social-distributor |
| 07:00 (Mon) | FB weekly top-salary digest | expats-social-distributor |
| daily | Lead qualification + Brevo nurture | expats-lead-nurture |
| on demand | WP/theme/file deploy | expats-cpanel-deployer |

## Guardrails
- No SSH/FTP to A2 — cPanel API + WP REST only. raspibig via plink.
- Quote all paths (spaces). Backup before destructive WP ops. GDPR consent-gated nurture.
