---
name: iscir-campaign-run
description: Prepare and (only after explicit approval) run gated cold-email campaigns for ISCIR portfolio products, reusing the InterJob Brevo/orchestrator infra with ASCII-only templates, DNC suppression, gentle ramp, and reply/bounce handling. Use when asked to prepare/launch/resume an ISCIR campaign, draft outreach templates, set sending caps, or wire a product into sending. Used by the campaign-runner agent.
---

# iscir-campaign-run

제품별 콜드이메일 캠페인 준비/발송. **발송은 항상 사용자 명시 승인 게이트 뒤.**

## 인프라 재사용
- 기존 raspibig orchestrator(port 8096) + Brevo 발송 엔진(InterJob 하네스). 새 발송 코드 작성 대신 캠페인 설정 추가.
- 리플라이: campaign-reply-handler 스킬. 바운스: 기존 bounce cleaner → DNC.
- Brevo 키 도메인별 매핑은 메모리 `brevo_keys_all` 참조.

## 템플릿 규칙
- 별도 `.txt` 파일: `Subject:` 1행 + 빈 행 + body.
- **전체 ASCII, diacritice 금지** (제목+본문). 데이터(이름)도 NFKD 폴드.
- 위치: `{product}/CAMPAIGN/templates/{product}_initial.txt` (+ bump, final).

## 절차
1. lead-enricher 세그먼트 + DNC 억제 적용 확인.
2. 발송자/cap 설정: yahoo 10/day, gmail/other 50/day, 부드러운 ramp + 3-6분 지연.
3. 랜딩 링크(product-builder) + 입찰 후크(tender-matcher) 삽입.
4. `_workspace/05_campaign_plan.md`: 대상 수, 일일 cap, 예상 기간, 발송자, 억제 제외.
5. **정지: "READY — awaiting approval".** 사용자가 명시 승인할 때까지 발송 금지.

## 하드 규칙
- 무단 발송 금지. 자동 cron 발송 추가도 승인 후.
- 일시적 부정 신호로 억제 금지.
- DNC 파일 없으면 중단(억제 없는 발송 금지).
- Brevo 차단 시 A2 SMTP/Gmail fallback 제안만, 발송 안 함.

## 왜
PARALLEL_3_PRODUCT_PLAN.md의 Approval Gate 정책 + D:\MEMORY 발송 규칙. 잘못된 대량 발송은 도메인 평판·법적 위험이라 사람 승인이 안전판.
