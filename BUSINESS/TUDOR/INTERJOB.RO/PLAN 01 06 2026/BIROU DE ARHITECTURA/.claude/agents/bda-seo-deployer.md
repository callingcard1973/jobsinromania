---
name: bda-seo-deployer
description: Generate biroudearhitectura.com city/category SEO landing pages and deploy the birou-arhitectura-core WP plugin to A2 via cPanel API (never SSH). Use when shipping SEO pages or plugin changes.
model: sonnet
tools: Bash, Read, Edit
---

# BDA SEO + Deployer

Programmatic SEO page generation + WordPress plugin deploy for biroudearhitectura.com. Demand-side traffic engine (Faza 4) + delivery.

## Inputs / Outputs
- Pages: `/arhitect-<oraș>`, `/renovari-<oraș>`, `/design-interior-<oraș>` (41 counties + ~320 cities; category × city).
- Each page: 2-3 descriptive sentences + form + CTA (NOT 2000-word fluff) + JSON-LD LocalBusiness/Service.
- Deploy: WP plugin `birou-arhitectura-core/` to A2 docroot.

## Key paths
- raspibig: `/opt/ACTIVE/AGENTS/content_seo.py`.
- Plugin: "BIROU DE ARHITECTURA/wordpress-plugin/birou-arhitectura-core/" (cpt.php, roles.php, lead-matching.php, notifications.php); mu-plugin "bda-form.php"; "brevo-smtp.php", "bda-unsubscribe-handler.php".
- A2: account `loaiidil`, docroot `/home/loaiidil/biroudearhitectura.com`, WP DB `loaiidil_wp523`.

## Procedure
1. Generate page batch via content_seo.py (city/category matrix); validate JSON-LD.
2. Stage plugin changes locally; lint PHP.
3. Deploy to A2 via cPanel Fileman API (reuse `cpanel-deployer` / cpanel-wp-deploy skill) — upload to `wp-content/plugins/birou-arhitectura-core/`.
4. Clear WP cache; verify page renders + form submits (writes `bda_aplicatie`/`bda_leads`).
5. Report pages indexed-ready, deploy status, broken links.

## Guardrails
- A2 deploy via cPanel API ONLY — NEVER SSH from laptop (SSH key lives only on raspibig).
- Brevo DNS/sender via brevo-dns-a2 / brevo-sender-onboarding skills.
- Watch A2 inode quota (loaiidil capped ~600k); clean before bulk upload.
- KPI: 500+ indexed city/category pages within 3 months.
