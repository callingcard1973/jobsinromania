# Device Improvements Analysis — 2026-04-28
## Comprehensive Study: Raspibig + Raspi + Laptop + Minipc

Generated: 2026-04-28 11:15 UTC  
Status: 4 parallel agent analyses, ready for implementation  
Next: Phase 1-3 remote agents + enhancements scheduled  

---

## RASPIBIG (192.168.100.21, 16GB RAM, always-on)

### 5 Priority Improvements

1. **SWAP ELIMINATION: Off-Load Ollama to Laptop** (Quick)
   - Problem: 2.8GB swap thrashing, Ollama idle in RAM
   - Impact: Frees 6GB, eliminates swap thrashing, no latency penalty
   - Solution: `ollama rm qwen3-4b qwen2.5:1.5b llama3.2:3b` + disable service
   - Effort: Quick (1h)
   - Priority: HIGH

2. **FIREFOX PDF RENDERER → LIGHTWEIGHT ALTERNATIVE** (Medium)
   - Problem: 2.3GB Firefox RAM for sporadic PDF generation
   - Impact: Frees 2GB, reduces context switching
   - Solution: Replace with wkhtmltopdf/weasyprint, on-demand subprocess
   - Effort: Medium (package + script refactor)
   - Priority: HIGH

3. **EXTERNAL HDD I/O OPTIMIZATION: Batch Writes + Async Logging** (Medium)
   - Problem: USB HDD 5.14s write latency, email campaigns stall
   - Impact: Reduce latency → <500ms, enable concurrent scraping
   - Solution: Buffered logging + ramdisk /tmp + async writes
   - Effort: Medium (logging refactor + ramdisk config)
   - Priority: MEDIUM

4. **CAMPAIGN PARALLELIZATION: 6 → 12 Concurrent Workers** (Quick)
   - Problem: 76% CPU idle, slow send windows
   - Impact: 2x throughput, 24h → 12h send window
   - Solution: `--workers 6` → `--workers 12`, add Brevo quota manager
   - Effort: Quick (~30 lines code)
   - Priority: MEDIUM

5. **MONITORING + AUTO-HEALING: Predictive Alerts** (Medium)
   - Problem: Reactive 15-min watchdog, no predictive alerts
   - Impact: Detect bottlenecks before failures, 15m → 2m MTTR
   - Solution: Prometheus metrics + thresholds + Telegram auto-heal
   - Effort: Medium (metrics export + dashboard)
   - Priority: MEDIUM

**Recommended execution order**: Week 1 (Quick: 1+4), Week 2 (Medium: 2), Week 3 (Medium: 3), Ongoing (5)

---

## RASPI (192.168.100.20, 4GB RAM, always-on)

### 5 Priority Improvements

1. **EURES SCRAPER RESILIENCE & VISIBILITY** (2-3h)
   - Problem: Exit code 1 every cycle, no structured error logs
   - Impact: 5K-15K jobs/day lost, no alerts
   - Solution: JSON logging + heartbeat + 1h cycle → 2h, structured error DB
   - Effort: 2-3h
   - Priority: HIGH

2. **POSTGRESQL QUERY TUNING & WAL ARCHIVING** (4-6h)
   - Problem: 358 raw tables, no indexing, no WAL archive
   - Impact: Slow queries, crash-vulnerable, recovery loss
   - Solution: Partition eures tables, enable WAL archiving, add slow query log
   - Effort: 4-6h
   - Priority: HIGH

3. **MEMORY PRESSURE & SWAP MITIGATION** (1-2h)
   - Problem: 475MB swap, 360MB free, OOM risk
   - Impact: Random scraper/dashboard kills, fragmentation
   - Solution: Reduce PG buffers, MemoryLimit cgroups, swap tuning
   - Effort: 1-2h
   - Priority: MEDIUM (stability baseline)

4. **TASK QUEUE RUNNER POLLING OPTIMIZATION** (2-4h)
   - Problem: 288 empty polls/day, lock contention
   - Impact: Wasted DB connections, CPU 30% during cycles
   - Solution: LISTEN/NOTIFY event-driven (replaces polling)
   - Effort: 2-4h
   - Priority: MEDIUM (efficiency)

5. **APPLICANT DASHBOARD SCALING & OFFLINE MODE** (6-8h)
   - Problem: 942 lines monolith, single SQLite, no resilience
   - Impact: CV upload blocks across 8 sites, no graceful degradation
   - Solution: Split upload/admin, PG migration, queuing, streaming, rate limits
   - Effort: 6-8h
   - Priority: MEDIUM (scale)

**Recommended execution order**: Priority 1 (high visibility) → 3 (stability) → 2 (correctness) → 4 (efficiency) → 5 (scale)  
**Total: 15-23h over 3-4 weeks**

---

## LAPTOP (D:\MEMORY, 64GB RAM, intermittent online, LM Studio)

### 5 Priority Improvements

1. **LLM SERVING ARCHITECTURE — Dedicated Model Orchestration** (4-6h)
   - Problem: Manual model management, no load balancing, offline = zero capacity
   - Impact: 4-8x faster inference, 2-4 models concurrent
   - Solution: vLLM orchestration + model router (1.7B quick/8B batch)
   - Effort: 4-6h (vLLM + router + tests)
   - Priority: HIGH

2. **SYNC PERFORMANCE — Bandwidth Saturation Fix** (5-7h)
   - Problem: Full DB replication timeouts, email classifier stalls
   - Impact: 40-90% network time wasted, 5-15min task lag
   - Solution: PostgreSQL logical replication (LISTEN/NOTIFY), binary delta sync
   - Effort: 5-7h (PG setup + subscription + refactor)
   - Priority: HIGH

3. **GPU UTILIZATION — External GPU Support** (6-8h)
   - Problem: CPU-bound, eGPU pending but not connected
   - Impact: 12-36x speedup for batch (RTX 3060)
   - Solution: Activate eGPU, CUDA 12.4, vLLM GPU config
   - Effort: 6-8h (hardware setup + driver + tests)
   - Priority: HIGH (once hardware arrives)

4. **RELIABILITY — Offline-First Task Queue** (3-4h)
   - Problem: Task state on raspibig only, offline = idles
   - Impact: Work on 2-3 days cached tasks, no network dependency
   - Solution: SQLite cache + conflict-free merge + 7-day expiry
   - Effort: 3-4h (schema + offline worker + merge logic)
   - Priority: MEDIUM

5. **LLM MODEL PRELOADING — Memory-Optimized Auto-Start** (2-3h)
   - Problem: Manual bonsai.bat start, 20s delay, 80% RAM unused
   - Impact: <100ms first query, models hot at boot
   - Solution: Task Scheduler + memory pinning + health check
   - Effort: 2-3h (batch + Python + restart logic)
   - Priority: MEDIUM

**Recommended execution order**: 5 (auto-start, 2-3h ROI) → 4 (offline queue) → 2+3 parallel (sync + GPU) → 1 (orchestration)  
**Total: 20-28h over 2-3 weeks**

---

## MINIPC (31GB RAM, Tailscale, rarely online)

### Problem: Under-Utilization (Bonus Worker, Starved of Tasks)

**Current state**: Offline-more-than-on, Ollama idle, wasted capex  
**Root cause**: Task routing prefers always-on devices (raspibig, laptop)  
**Cost**: $50-80/mo idle power  
**ROI if utilized**: 18 months (if 2+ ideas live)  

### 5 Ideas to Drive Utilization

1. **RESERVED TASK TYPE: Batch LLM Inference** (1-2h)
   - Use qwen2.5:14b for `email_batch_classify` (100-200 tasks)
   - Impact: +300% LLM throughput, 4-8h/day utilization
   - Solution: Route `email_batch_classify` → minipc only
   - Effort: 1-2h

2. **BATCH DOCUMENT PROCESSING: HTML→PDF, Catalogs** (1h)
   - Run wkhtmltopdf in parallel (31GB allows 10+), async render
   - Impact: +200% PDF throughput, frees raspibig 20min/day
   - Solution: `catalog_batch_renderer.py`, 50 PDFs = 15min
   - Effort: 1h

3. **SCHEDULED ENRICHMENT SYNC: Offline Batch Work** (2-3h)
   - Download 100K companies, fuzzy dedup + geocoding offline
   - Impact: -20% DB load, 10-20K rows enriched weekly
   - Solution: `enrich_batch_worker.py` + staging merge
   - Effort: 2-3h

4. **ALWAYS-ON LLM API SERVER: Fallback Endpoint** (2h)
   - Expose Ollama qwen2.5:14b at port 11434, public SSH tunnel
   - Impact: Eliminates LLM timeout failures, +10h/week uptime
   - Solution: Flask proxy + SSH tunnel + fallback routing
   - Effort: 2h

5. **DEDICATED SCRAPER NODE: Reduce Raspibig Load** (1.5h)
   - Route `type: scrape` → minipc, Playwright 2-3 concurrent
   - Impact: +2-3h/day freed on raspibig, MADR real-time
   - Solution: `scraper_worker.py` + routing rule + systemd
   - Effort: 1.5h

**Cost-benefit**: Keep online only if 2+ ideas committed (ROI 6mo). Otherwise, sell/repurpose.

**Total effort if all 5 implemented**: 7-8.5h spread over 2-3 weeks

---

## SCHEDULED AGENTS (Complete Implementation Plan)

### Phase 1 (Tomorrow 3pm UTC)
- Raspibig Resource Alerts (swap>60%, CPU>14, memory leak)
- Email-Sorter Analytics Dashboard
- Routine ID: `trig_018JyLfCcqXx43q2gV5p6ZQU`

### Phase 2 (May 1, 9am UTC)
- Applications Viewer LIVE (30 IMAP real-time)
- Applicant Auto-Matching (parse CV, match solonet)
- PADINA Property Tracker (weekly MADR scrape)
- Routine ID: `trig_01T94mFV3jCbfcDMd1yvb8eE`

### Phase 3 (May 3, 9am UTC)
- Campaign A/B Testing Framework
- Log Cleanup Automation (90d emails, 30d SMTP logs)
- Routine ID: `trig_01XexNX4sNM8zbzqeE6yF8bj`

### Autoheal Enhancement (Tomorrow 3pm UTC)
- Swap Alert Module (>60% threshold)
- Disk Cleanup Automation (>70% disk)
- Memory Leak Detection (>500MB/hr growth)
- Routine ID: `trig_018JyLfCcqXx43q2gV5p6ZQU`

---

## Quick Reference: Implementation Checklist

**Immediate (Week 1):**
- [ ] Phase 1 agent deploys (tomorrow 3pm)
- [ ] Raspibig: swap elimination + campaign parallelization (2h)

**Short-term (Weeks 2-3):**
- [ ] Phase 2 agent deploys (May 1)
- [ ] Raspibig: PDF renderer swap (Medium)
- [ ] Raspi: EURES scraper resilience (2-3h)
- [ ] Laptop: Auto-start models (2-3h)

**Medium-term (Weeks 3-4):**
- [ ] Phase 3 agent deploys (May 3)
- [ ] Raspi: PG tuning + memory pressure (5-8h)
- [ ] Laptop: Sync performance + offline queue (8-11h)
- [ ] Minipc: Commit to 2+ ideas (7-8.5h)

**Total implementation estimate: 40-60 hours over 4 weeks** (distributed across 4 devices in parallel, 10-15h/week)

---

**Backup created**: D:\MEMORY\.claude\DEVICE_IMPROVEMENTS_2026_04_28.md  
**Sync to all devices**: raspibig:/opt/ACTIVE/IMPROVEMENTS/ + raspi + minipc via Tailscale
