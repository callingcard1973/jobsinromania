# CLAUDE.md — MERCOSUR2 (General)

## Purpose of This Directory Group
The MERCOSUR2 directory cluster under `/opt/ACTIVE/IDEAS/MERCOSUR/` is a **research, development, and experimentation zone** for the Mercosur Data Factory ecosystem.  
It is not the production environment — instead, it is where ideas, prototypes, prompts, code experiments, and workflow designs are created before being promoted to `/opt/MERCOSUR`.

This folder group is intended for:
- LLM-assisted research
- Code prototyping
- Workflow design
- Prompt engineering
- Experimentation with scrapers, agents, and automation
- Cross-tool development (Claude, OpenCode, VS Code)

Claude should treat this directory as a **creative and analytical sandbox**.

---

## Subdirectory Roles

### 1. `CLAUDE/`
This folder contains:
- High-level prompts
- Research instructions
- System-level reasoning
- Multi-agent planning
- Data acquisition strategies
- Architecture notes
- Country-specific intelligence

Claude should:
- Generate structured plans
- Propose new modules
- Analyze feasibility
- Identify missing components
- Suggest improvements to the Mercosur intelligence system
- Maintain a strategic, high-level perspective

---

### 2. `OPENCODE/`
This folder contains:
- Code drafts
- Experimental scrapers
- Parsing prototypes
- Data transformation utilities
- Early-stage modules not ready for production

Claude should:
- Generate clean, modular code
- Keep experiments isolated
- Avoid hardcoding production paths
- Use mock data when needed
- Document assumptions
- Provide multiple implementation options when useful

---

### 3. `VSCODE/`
This folder contains:
- Editor-friendly files
- Project scaffolding
- Task definitions
- Debug configurations
- Workspace-level notes
- Refactoring plans

Claude should:
- Provide code navigation hints
- Suggest refactoring strategies
- Maintain compatibility with Python, Bash, and Node-RED workflows
- Keep files readable and well-structured
- Support incremental development

---

## Core Themes Across All MERCOSUR2 Directories

### A. Research & Discovery
Claude should help identify:
- New data sources (exporters, importers, procurement, statistics)
- New Mercosur/EU portals
- New anti-blocking strategies
- New automation opportunities
- New cross-country correlations

### B. Scraper Development
Claude should:
- Propose scraper architectures
- Suggest parsing strategies
- Identify HTML structure changes
- Recommend anti-bot techniques
- Maintain Tor routing and UA rotation

### C. Data Engineering
Claude should:
- Propose schemas
- Normalize company names
- Detect duplicates
- Suggest database models
- Recommend ETL pipelines

### D. Procurement Intelligence
Claude should:
- Identify TED-like portals in Mercosur countries
- Propose extraction strategies for winners, bidders, contract values
- Cross-reference procurement winners with exporters/importers

### E. Free Trade Agreement Analysis
Claude should:
- Summarize FTAs relevant to Romania, Canada, UK
- Extract tariff schedules
- Identify sensitive sectors
- Map FTA benefits to exporters/importers

### F. Multi-Agent Workflows
Claude may propose:
- Scraper agent
- Validator agent
- Procurement agent
- FTA agent
- Company profiler agent
- Data quality agent

---

## Behaviour Guidelines for Claude

1. **Stay modular**  
   Every idea, script, or workflow should be easy to move into production (`/opt/MERCOSUR`) later.

2. **Stay country-aware**  
   Prioritize:
   - Brazil  
   - Argentina  
   - EU  
   - Other Mercosur members  
   - UN/NGO procurement  
   - FTAs for Romania, Canada, UK  

3. **Stay anonymous**  
   Always assume Tor routing, IP cycling, and anti-blocking are required.

4. **Stay structured**  
   When generating:
   - Use clear sections  
   - Provide reasoning  
   - Suggest alternatives  
   - Document assumptions  

5. **Stay experimental**  
   This directory is for:
   - Prototypes  
   - Drafts  
   - Ideas  
   - Explorations  
   - Unfinished modules  

6. **Stay safe**  
   Never overwrite production files unless explicitly instructed.

---

## Future Expansion Ideas
- Add a “country intelligence pack” for each Mercosur member
- Add a procurement ontology
- Add a trade-flow graph model
- Add embeddings for semantic search
- Add anomaly detection for trade patterns
- Add a multi-agent orchestrator
- Add a “promotion pipeline” from MERCOSUR2 ? MERCOSUR (production)

---

## Final Note
This `claude.md` is intentionally broad.  
You can trim, specialize, or split it into multiple files