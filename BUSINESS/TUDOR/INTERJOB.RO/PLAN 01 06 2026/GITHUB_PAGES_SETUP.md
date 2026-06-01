# GitHub Pages Deployment - BuildJobs.eu

**Simple static HTML export to GitHub Pages FREE**

## Files Ready
- `CODE/output/jobs/buildjobs_jobs_homepage.html` → `public/index.html`
- `CODE/output/jobs/buildjobs_jobs_seo.html` → `public/seo.html`

## Setup Steps (5 minutes)

### 1. Enable GitHub Pages
- Go to https://github.com/callingcard1973/jobsinromania/settings/pages
- Source: Deploy from a branch → `gh-pages` → `/ (root)`
- Save

### 2. Configure DNS for buildjobs.eu
```
Type: CNAME
Name: @
Value: callingcard1973.github.io

Type: CNAME  
Name: www
Value: callingcard1973.github.io
```

### 3. Add custom domain in GitHub
- Go to Settings → Pages → Custom domains
- Add: `buildjobs.eu`
- GitHub will give you a TXT verification record
- Add TXT record to DNS
- Enable "Enforce HTTPS"

### 4. Trigger deployment
- Go to Actions → Deploy Static HTML → Run workflow
- Wait 2 minutes
- Visit https://buildjobs.eu

## Workflow
- Runs daily at 3:00 AM UTC
- Manual trigger available
- Copy HTML from CODE/output/ to public/
- Deploy to gh-pages branch

## Estimated Time
- Setup: 5 minutes
- DNS propagation: 24-48 hours