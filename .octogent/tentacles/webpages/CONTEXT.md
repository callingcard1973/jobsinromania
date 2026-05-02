# Webpages Tentacle

## Scope
D:\MEMORY\CODE\INFRA\WEBPAGES\ — 28 InterJob sites

## Domains
Job (15): careworkers.eu, factoryjobs.eu, buildjobs.eu, electricjobs.eu, farmworkers.eu,
  horecaworkers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu,
  aluminumrecyclehub.com, expatsinromania.org, interjob.ro, mivromania.info,
  mivromania.online, nepalezi.com
Static (5): internaltransfers.eu, horecaworkers2026.com/eu/online, weddnesday.org
WordPress (7): cumparlegume.com, seicarescu.com, agroevolution.com, ajwang.org,
  baneasa39.com, haritina.com, mivromania.com

## Deploy pattern
cPanel UAPI Fileman save_file_content — param name is "file" not "filename"
A2 docroot: ~/domainname/ (NOT ~/public_html/)

## Key scripts
- generate_llm_seo.py + deploy_llm_seo.py — llms.txt on all 28 domains (deployed)
- wp_draft_agent.py — draft WP articles via XML-RPC (never auto-publish)
- a2_deployer.py — HTML deploy via cPanel API

## Pending
- Deploy code-review.html + ai-assistant.html to seicarescu.com
