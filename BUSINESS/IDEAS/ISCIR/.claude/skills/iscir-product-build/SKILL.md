---
name: iscir-product-build
description: Build customer-facing assets for ISCIR portfolio products — landing pages, catalogs, kit/pricing specs, lead-magnet PDFs, SaaS feature scaffolds. Use when asked to build a landing page, create/refresh a product spec, make a catalog or lead magnet, or update marketing for ISCIR Vault / ElectroSafe / NetVault / GovTender / InsolvencyVault. Used by the product-builder agent.
---

# iscir-product-build

PRODUCT_PORTFOLIO.md 사양 → 실제 고객 대면 자산.

## 진실 소스
- `PRODUCT_PORTFOLIO.md` — 킷 내용, 가격, TAM, GTM.
- `PARALLEL_3_PRODUCT_PLAN.md`, `NEXT_ACTIONS.md` — 빌드 순서/카피.
가격·킷은 인용만, 임의 변경 금지(충돌 시 사용자 질의).

## 자산 유형
| 자산 | 출력 | 비고 |
|------|------|------|
| 랜딩 페이지 | {product}/CODE/landing_page.html | frontend-design 패턴, 제네릭 AI 미관 회피 |
| 카탈로그 | {product}/CODE/{product}_catalog.html | interjob-catalog 패턴 재사용, ISCIR 브랜딩 |
| 제품 사양 | {product}/SPEC.md | 킷/가격/SaaS 기능 |
| 리드매그닛 | DATA/lead_magnets/{product}_checklist.html | "무료 audit readiness 체크리스트" |

## 절차
1. 사양 읽기 → 자산 생성.
2. tender-matcher 통계 있으면 랜딩에 "당신 스킬에 맞는 X개 입찰, 총 €Y" 삽입.
3. **이메일에 들어갈 텍스트는 ASCII only.** 웹 HTML은 diacritice 허용.
4. `_workspace/04_product_assets.md`에 생성 목록 + 미리보기 경로.

## 하드 규칙
배포(A2/cPanel) 금지 — 산출물만 생성. 실제 배포는 사용자 승인 게이트(prestashop-posthog-a2/cpanel-wp-deploy 스킬은 승인 후에만).

## 왜
랜딩/카탈로그가 캠페인 전환을 좌우. 입찰 사회적 증거 + 명확한 가격 = B2B 2% 전환 목표. 무단 배포는 미완성 자산 노출 위험이라 게이트.
