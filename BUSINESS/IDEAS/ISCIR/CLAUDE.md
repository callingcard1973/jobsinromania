# CLAUDE.md — ISCIR Compliance Vault Portfolio

부모 규칙 상속: `D:\MEMORY\CLAUDE.md`, `D:\MEMORY\BUSINESS\IDEAS\CLAUDE.md` (Unix 스타일, 250줄/파일, 발송/배포/커밋은 사용자 승인 게이트, 이메일 ASCII only).

## 하네스: ISCIR Compliance Vault Portfolio

**목표:** RO 정부 등록부(ISC/ISCIR, ANRE, ANCOM, IGSU, ITM 외)를 컴플라이언스 vault 제품(ISCIR Vault, ElectroSafe, NetVault, GovTender, InsolvencyVault, Bundle)으로 전환 — 트래픽·리드·매출 극대화.

**트리거:** ISCIR 포트폴리오 작업(등록부 갱신, 리드 빌드/세그먼트, CPV 입찰 매칭, 랜딩/카탈로그, 캠페인 준비, QA/KPI) 요청 시 `iscir-portfolio-orchestrator` 스킬을 사용하라. ISCIR/ElectroSafe/NetVault/GovTender/InsolvencyVault를 언급하거나 "rerun/update/redo/improve" 요청 시 포함. 단순 질문은 직접 응답.

**팀:** registry-scraper · lead-enricher · tender-matcher · product-builder · campaign-runner · portfolio-analyst (전부 opus). 상세는 `.claude/agents/` + `.claude/skills/`.

**하드 규칙:** 발송/배포/커밋은 사용자 명시 승인 후. 이메일 자산 ASCII only. 일시적 부정 신호(ANAF 부채 등)로 리드 억제 금지. DATA archive-before-overwrite, 50% 급감 시 덮어쓰기 금지.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-06-26 | 초기 구성 (6 에이전트 + 6 스킬 + 오케스트레이터) | 전체 | - |
| 2026-06-26 | iscir-scrape 스킬 추가 (Cloudflare 우회 fetcher) | skills/iscir-scrape, CODE/iscir_fetch.py | iscir.ro managed challenge |
| 2026-06-26 | iscir-normalize 스킬 추가 (zero-token PDF→CSV) | skills/iscir-normalize, CODE/iscir_normalize.py | 8 등록부 정규화, 토큰 0 |
