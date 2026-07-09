---
name: iscir-tender-match
description: Match EU/RO public tenders to ISCIR portfolio companies by CPV code, producing per-product tender-match CSVs and "X tenders worth €Y" stats. Use when asked to match tenders, generate tender alerts, run CPV matching, build the GovTender feed, or add tender social-proof to a product. Used by the tender-matcher agent.
---

# iscir-tender-match

CPV 코드로 공공입찰을 포트폴리오 기업에 매칭 → 알림/사회적 증거.

## 제품 → CPV
| 제품 | CPV | 설명 |
|------|-----|------|
| ISCIR Vault | 51720, 71520 | 압력장비 설치/검사 |
| ElectroSafe | 45100, 45200, 45300 | 전기설치/유지/난방 |
| NetVault | 64200, 64300 | 네트워크 서비스 |

## 절차
1. 입력: OPENTENDER/TED (`D:\MEMORY\DATA\ACTIVE\OPENTENDER`, 패턴은 GovTender/CODE/govtender_pipeline.py 참고) + `DATA/leads/{product}_leads.csv`.
2. CPV 필터로 관련 입찰 추출. 마감 지난 것 제외.
3. relevance_score: CPV 정확매칭=1.0, 앞 3자리 부분매칭=0.6, 지역 일치 +0.1.
4. 출력: `DATA/tenders/{product}_tender_matches.csv`
   스키마: `tender_id, company, cui, cpv, value, currency, deadline, relevance_score, region`.
5. 제품별 집계(매칭 수, 평균 relevance, 총 가치 €) → `_workspace/03_tender_matches.md`.
6. 무작위 100건 spot-check 권장 플래그.

## 왜
입찰 매칭은 premium tier(€10-15/mo)의 핵심이자 캠페인 후크("당신 스킬에 맞는 12개 EU 입찰, €5M"). 마감/통화 오류는 신뢰를 깨므로 마감 필터·통화 명시 필수.
