---
name: iscir-lead-enrich
description: Clean, validate, dedupe and cross-reference ISCIR registry CSVs into segmented sendable lead lists per product. Use when asked to build/segment a lead list, cross-reference agencies (ISCIR∩ANRE bundle), check email coverage, or apply DNC suppression for an ISCIR product. Used by the lead-enricher agent.
---

# iscir-lead-enrich

원시 등록부 CSV → 제품별 판매 가능 리드 리스트.

## 제품 → 소스
| 제품 | 소스 CSV | 타겟 |
|------|----------|------|
| ISCIR Vault | DATA/iscir_ops.csv | 압력장비 계약자 7,502 |
| ElectroSafe | ANRE electricieni_enriched.csv | 전기기사 ~50K active |
| NetVault | DATA/ancom_final.csv | 텔레콤 operators 568 |
| Bundle | iscir_ops ∩ ANRE (CUI) | 양 등록부 교집합 |

## 표준 소스 DB (canonical)
`romania.companies_master` (2,917,045 firme, ONRC+enrichment, CAEN 99% / email 36%). 두 노드 동일:
- 랩탑: `psql -h localhost -p 5433 -U tudor -d romania` (PG18, pass tudor)
- raspibig: `psql -h 192.168.100.21 -p 5432 -U tudor -d romania` (PG15)
인덱스: caen, cui, county, j_number. **interjob_master(40M) 사용 금지** — RO 클라이언트엔 CAEN 없음. join은 CUI 우선(j_number는 master에 1%만).

## 절차
1. 이메일 검증: 정규식 + 도메인 형식. role 주소(office@, contact@) 표시하되 유지.
2. 중복제거: CUI 우선 → 없으면 정규화 email.
3. 교차참조: CUI join으로 Bundle 타겟 산출. CUI 없으면 정규화 name fallback + 정확도 경고.
4. 세그먼트: county별, 이메일 도메인(yahoo/gmail/other)별.
5. **억제**: DNC/master_dnc + 이미 보낸 리스트 제외. 일시적 부정 신호로는 억제 금지.
6. 출력 데이터 ASCII 폴드(`unicodedata.normalize('NFKD', s).encode('ascii','ignore')`).
7. 출력: `DATA/leads/{product}_leads.csv` + `_workspace/02_leads_summary.md` (총 리드, 이메일 커버리지 %, 교집합 크기, 억제 수).

## 데이터 스키마 (leads CSV)
`name, cui, county, email, email_valid, phone, product, segment, source_agency, suppressed_reason`

## 왜
교차참조 Bundle 리스트는 경쟁사가 만들 수 없는 자산(D1 가치). 억제는 영구 신호(opt-out/bounce/DNC)에만 — 부채 같은 가변 상태는 "We are not suppressing anybody".
