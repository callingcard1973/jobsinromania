---
name: estate-orchestrator
description: ROOT meta-orchestrator for the entire D:\MEMORY estate. Use when a request spans the whole repo or is not clearly scoped to one sub-project — "audit the estate", "find duplicates", "clean up D:\MEMORY", "what can make money", "scan for opportunities", "route this to the right harness", "estate status", or any top-level / cross-domain ask. Routes domain work to existing sub-harnesses (INTERJOB master, AGROEVOLUTION.EU, ISCIR, A2 operations, etc.) instead of rebuilding them. Also handles re-runs: "redo the dedup", "rescan money ideas", "update the estate map".
---

# Estate Orchestrator (ROOT meta-harness)

D:\MEMORY는 ~40개 활성 도메인 하네스를 가진 거대한 추정치다. 이 루트 하네스는 **새 하네스를 만들지 않는다**. 세 가지 일을 한다: (1) 작업을 기존 도메인 오케스트레이터로 라우팅, (2) 전역 중복 감사, (3) 전역 수익 기회 스캔.

핵심 규칙: **모든 응답은 번호 매긴 액션 목록으로 끝낸다**(CLAUDE.md HARD RULE). 데이터 제시 → 번호 옵션 → 번호 대기. 산문 질문 금지.

## Phase 0 — 컨텍스트 확인
1. `_workspace/` 존재 여부 확인.
   - 없음 → 초기 실행.
   - 있음 + 부분 요청("redo dedup") → 해당 에이전트만 재호출.
   - 있음 + 신규 입력 → 기존을 `_workspace_prev/`로 이동 후 새 실행.
2. 요청 유형 분류: **route** / **dedup** / **opportunity** / **mixed**.

## Phase 1 — 라우팅 (route)
`estate-harness-router` 에이전트(또는 인라인 판단)로 도메인 매칭. 기존 오케스트레이터 스킬로 위임:

| 도메인 | 위임 대상 스킬 |
|--------|----------------|
| InterJob 마켓플레이스 전반 | `interjob-master-orchestrator` |
| 일일 데이터 파이프라인/카탈로그 | `pipeline-orchestrator` |
| A2 웹/도메인/WP/디스크 | `a2-operations-orchestrator` |
| SEO 카운티 페이지 | `seo-county-pages` |
| 인프라 헬스 | `infrastructure-health` |
| raspi Romania/ANOFM | `raspi-romania-inspect` |
| 농지 EN 미러 | `agroevolution-eu-loop` |
| 규제 컴플라이언스 데이터 | `iscir-operations` (`ISCIR/.claude/skills/iscir-operations/`) |
| 도메인별 잡 루프 | `electricjobs-loop` / `bpp-loop` 등 |
| 언론 리뷰/뉴스 | `revista-presei-orchestrator` |
| 슈퍼마켓/바이어 캠페인 | `supermarket-orchestrator` |
| DB 미러/델타 싱크 | `db-sync-harness` |
| WhatsApp CV 인입 | `whatsapp-cv-orchestrator` |
| 후보-잡 매칭 | `matcher-orchestrator` |
| raspi/raspibig 인프라 점검 | `raspi-romania-inspect` / `infrastructure-health` |

매칭 없을 때만 신규 하네스 빌드를 `harness` 스킬로 제안.

**드리프트 주의(2026-06-26 감사):** 13개 2026-06-26 하네스가 미커밋 → 라우터에 안 보임. 마스터 위임 테이블에 `revista-presei`/`supermarket`/`db-sync`/`whatsapp-cv`/`matcher`/`job-catalog` 누락. 커밋은 Tudor 명시 지시 시에만.

## Phase 2 — 중복 감사 (dedup)
`estate-dedup-auditor` 에이전트 호출 (`model: "opus"`). 4축 스캔 → `_workspace/dedup_report.md`.
**삭제는 자동 실행 금지.** 보고서 끝에 번호 매긴 삭제 후보 목록을 만들고, Tudor가 번호로 승인한 항목만 명시적 경로로 삭제(`git add -A` 금지, ARCHIVE 경로 우선).

## Phase 3 — 기회 스캔 (opportunity)
`estate-opportunity-scout` 에이전트 호출 (`model: "opus"`). 실재 자산 근거 → `_workspace/opportunity_report.md`. 상위 3개 "do this week" 플래그. 실행은 도메인 하네스로 위임.

## Phase 4 — 종합 + 번호 액션
세 산출물을 종합하여 한 화면 요약 + **번호 매긴 다음 액션**으로 마무리.

## 실행 모드
서브 에이전트 패턴(기본): 세 에이전트는 독립적이므로 `Agent` 도구로 병렬 호출(`run_in_background` 가능), 결과만 수집. 전역 합의가 필요 없으므로 팀 오버헤드 불필요.

## 데이터 전달
파일 기반: 모든 중간 산출물은 `D:\MEMORY\.claude\_workspace\{phase}_{agent}_{artifact}.md`. 최종 요약만 사용자에게.

## 에러 핸들링
- glob/find 타임아웃 → 경로 좁혀 재시도. 1회 재시도 후 실패 시 누락 명시하고 진행.
- DB 도달 불가 → CSV 행수 추정으로 폴백, 명시.
- 에이전트 세션 한도 → 부분 결과로 진행, 미완 항목을 번호 액션에 남김.

## 테스트 시나리오
- 정상: "audit the estate" → dedup + opportunity 병렬 → 종합 보고 + 번호 액션.
- 에러: dedup 에이전트 타임아웃 → opportunity 결과만으로 부분 보고 + "1. dedup 재시도" 옵션.

## 변경 이력
| 날짜 | 변경 | 대상 | 사유 |
|------|------|------|------|
| 2026-06-26 | 초기 구성 | 전체 | 루트 estate 하네스 신규 |
| 2026-06-27 | ISCIR 라우팅 정밀화 | SKILL.md | ISCIR 하네스 신규 (`iscir-operations` 스킬 + CLAUDE.md) |
