---
name: iscir-portfolio-orchestrator
description: Orchestrates the ISCIR Compliance Vault portfolio (ISCIR Vault, ElectroSafe, NetVault, GovTender, InsolvencyVault, Bundle) end-to-end — refresh government registries, enrich+cross-reference leads, match tenders by CPV, build product assets, prepare gated campaigns, and QA. Use whenever the user works on ISCIR portfolio: "refresh the registries", "build leads for ElectroSafe", "match tenders", "prepare the NetVault campaign", "build a landing page", "rerun the portfolio", "update/redo/improve" any ISCIR product, or names ISCIR/ElectroSafe/NetVault/GovTender/InsolvencyVault. Simple questions answer directly.
---

# ISCIR Portfolio Orchestrator

ISCIR 포트폴리오 에이전트 팀을 조율한다. 실행 모드: **에이전트 팀 (하이브리드 파이프라인)**. 모든 Agent 호출은 `model: "opus"`.

## 팀 구성
| 에이전트 | 역할 | 스킬 |
|---------|------|------|
| registry-scraper | 등록부 갱신 → CSV | iscir-registry-refresh, iscir-scrape, iscir-normalize |
| lead-enricher | 정제·교차참조·세그먼트 | iscir-lead-enrich |
| tender-matcher | CPV 입찰 매칭 | iscir-tender-match |
| product-builder | 랜딩·카탈로그·사양 | iscir-product-build |
| campaign-runner | 게이트형 캠페인 | iscir-campaign-run |
| portfolio-analyst | 교차검증·KPI·드리프트 (general-purpose) | (재사용 analytics) |

## Phase 0: 컨텍스트 확인
1. `_workspace/` 존재 여부 확인.
   - 미존재 → **초기 실행**.
   - 존재 + 부분 수정 요청 → **부분 재실행** (해당 에이전트만 호출).
   - 존재 + 새 입력 → 기존 `_workspace/`를 `_workspace_prev/`로 이동 후 **새 실행**.
2. 요청 범위 파악: 단일 제품인가 전체 포트폴리오인가, 어느 단계(데이터/리드/입찰/자산/캠페인)인가.

## Phase 1: 데이터 (실행 모드: 서브 — 독립 병렬)
registry-scraper로 대상 기관 갱신. 단일 제품이면 해당 소스만.

## Phase 2: 리드 + 입찰 (실행 모드: 팀)
lead-enricher → tender-matcher 파이프라인. 리드 준비되는 제품부터 입찰 매칭 시작(배리어 없음). portfolio-analyst가 각 산출물 직후 점진 검증.

## Phase 3: 자산 (실행 모드: 서브)
product-builder로 제품별 랜딩/카탈로그/리드매그닛 생성. tender 통계 삽입.

## Phase 4: 캠페인 준비 (실행 모드: 서브, 게이트)
campaign-runner로 캠페인 설정+템플릿 준비. **"READY — awaiting approval"에서 정지. 사용자 승인 없이 발송 금지.**

## Phase 5: QA + 종합
portfolio-analyst가 전체 교차검증 + KPI/TAM 재추정 → `_workspace/06_qa_report.md`. 리더가 종합 보고.

## 데이터 전달
- 태스크 기반(조율) + 파일 기반(산출물, `_workspace/{NN}_{agent}_{artifact}.md` + `DATA/`) + 메시지 기반(통지).
- 최종 자산만 제품 폴더/`DATA/`에 출력, 중간물은 `_workspace/` 보존.

## 에러 핸들링
각 단계 1회 재시도. 재실패 시 해당 산출물 없이 진행 + 보고서에 누락 명시. 상충 데이터는 삭제하지 않고 출처 병기. 데이터 50% 미만 급감 시 덮어쓰기 금지.

## 하드 규칙 (D:\MEMORY 상속)
- **발송/배포/커밋은 사용자 명시 승인 필요.** 자동 발송·자동 커밋 금지.
- **이메일 자산 ASCII only**, diacritice 금지.
- 일시적 부정 신호(ANAF 부채 등)로 리드 억제 금지 — 정보용 only, as-of 날짜.
- DATA 안전: archive before overwrite.

## 테스트 시나리오
- **정상 흐름**: "refresh ANRE and prepare the ElectroSafe campaign" → Phase1(ANRE만) → Phase2(ElectroSafe 리드+45xxx 입찰) → Phase3(랜딩) → Phase4(캠페인 READY, 정지) → Phase5(QA). 발송 없음.
- **에러 흐름**: OPENTENDER 로드 실패 → tender-matcher 1회 재시도 → 실패 시 입찰 매칭 SKIPPED, 리드/자산은 계속, QA 보고서에 누락 명시.
