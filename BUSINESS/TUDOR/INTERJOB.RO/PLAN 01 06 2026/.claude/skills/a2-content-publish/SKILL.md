---
name: a2-content-publish
description: "Publish HTML content (articles, landing pages, SEO pages) to A2 Hosting static sites via cPanel API. Handles file creation, OG tag injection, cross-link insertion, and HTTP verification. Use for: publishing articles, adding OG meta tags, adding cross-links, updating index pages, creating SEO pages across the InterJob network of 8+ domains. Trigger: 'publish article', 'add OG tags', 'add cross-links', 'create page', 'update site content', 'publish to all domains'."
---

# A2 Content Publishing

Publish static HTML content to A2 Hosting domains (InterJob network) via cPanel UAPI.

## Connection

Same as `a2-cpanel` skill: `nl1-cl8-ats1.a2hosting.com:2083`, auth `cpanel loaiidil:KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453`.

## Docroot Rule

Exception: `warehouseworkers.eu` → `/home/loaiidil/public_html/warehouseworkers.eu`
All others: `/home/loaiidil/<domain>/`

## Active Domains (InterJob Network)

| Domain | Type | Docroot |
|--------|------|---------|
| buildjobs.eu | Static HTML | `/home/loaiidil/buildjobs.eu` |
| factoryjobs.eu | Static HTML | `/home/loaiidil/factoryjobs.eu` |
| electricjobs.eu | Static + WP | `/home/loaiidil/electricjobs.eu` |
| mechanicjobs.eu | Static HTML | `/home/loaiidil/mechanicjobs.eu` |
| horecaworkers.eu | Static HTML | `/home/loaiidil/horecaworkers.eu` |
| farmworkers.eu | Static HTML | `/home/loaiidil/farmworkers.eu` |
| meatworkers.eu | Static HTML | `/home/loaiidil/meatworkers.eu` |
| interjob.ro | WordPress | `/home/loaiidil/interjob.ro` (WP via PHP bootstrap) |

## OG Tags Required

Every article page must have:
- `og:title`, `og:description`, `og:type`, `og:site_name`
- `og:url` (canonical, per-page)
- `article:published_time` (ISO 8601)
- `twitter:card` (summary_large_image)

## Cross-Links Required

Every article must link to all sibling domains' articles. Pattern:
```html
<div class="cross-links">
<h3>Vezi și alte ocupații deficitare</h3>
<ul>
<li><a href="https://buildjobs.eu/articles/...">Build Jobs</a></li>
<!-- ... all 7 others ... -->
</ul>
</div>
```

Add cross-link sections to `articles/index.html` and root `index.html` as well.

## Write Method

Use `Fileman/save_file_content` with:
- `filename=<name>` (not `file`)
- `content=<text>`

Best practice: Python `urllib` for reliability (avoids MSYS2 path mangling that affects bash).

## Verification

After writing each file, verify with `curl -o /dev/null -w "%{http_code}" "https://domain/path"`. Expected: 200.

## Error Handling

- **Disk quota exceeded**: stop immediately, report BLOCKED with details
- **HTTP non-200**: retry once, then mark FAILED
- **Partial success**: report which domains succeeded and which failed

## References

- Full cPanel API cheatsheet: `C:\Users\apami\.agents\skills\a2-cpanel\references\api-cheatsheet.md`
- Cross-site-publish skill: `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ANOFM\.claude\skills\cross-site-publish\SKILL.md`
- Article content: `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ANOFM\DATA\article_ocupatii_deficitare_2026.md`
