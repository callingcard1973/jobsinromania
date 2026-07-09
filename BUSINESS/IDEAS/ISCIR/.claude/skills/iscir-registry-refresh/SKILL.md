---
name: iscir-registry-refresh
description: Refresh Romanian government registries into normalized CSVs under ISCIR/DATA. Use when asked to rescrape/refresh/update ISC, ISCIR, ANRE, ANCOM, IGSU, ITM, ANRM, ANRSC, AFER, RAR, AEO, rebuild the lead source data, or check when a registry was last updated. Used by the registry-scraper agent.
---

# iscir-registry-refresh

정부 등록부를 갱신해 `DATA/{agency}.csv`를 최신화하는 절차.

## 기관 → 스크레이퍼 → 출력
| 기관 | 코드 | 출력 CSV | 현재 행수(참고) |
|------|------|----------|------|
| ISC/ISCIR | ISC/CODE/scrape_isc.py | DATA/iscir_ops.csv | 7,476 |
| ANRE | ANRE/CODE/import_anre_db.py | DATA/ (electricieni) | — |
| ANCOM | ANCOM/CODE/import_ancom_db.py | DATA/ancom_final.csv | 568 |
| IGSU | IGSU/CODE | DATA/igsu.csv | 19,515 |
| ITM | ITM/CODE | DATA/itm_plasare.csv, itm_temp.csv | 500/1,401 |
| ANRM | — | DATA/anrm.csv | 389 |
| ANRSC | — | DATA/anrsc.csv | 6,487 |
| AFER | — | DATA/afer.csv | 98 |
| RAR | — | DATA/rar.csv | 15,838 |
| AEO | — | DATA/aeo.csv | 18 |

## 절차
1. 대상 기관의 스크레이퍼를 `{AGENCY}/CODE/`에서 실행.
2. 출력을 임시 파일에 쓰고 행수 측정.
3. **신규 행수 < 기존 50% → 실패 의심, 덮어쓰지 말고 보고.** 정상이면 기존 CSV를 `DATA/_archive/{agency}_{날짜}.csv`로 백업 후 교체.
4. 정규화 컬럼 보장: `name, cui, county, email, phone, source_agency, scraped_at, raw_status`.
5. `_workspace/01_registry_refresh.md`에 before→after, 실패, 스키마 이상 기록.

## 왜
데이터가 곧 경쟁우위다. 부분/깨진 스크레이프로 좋은 리스트를 덮어쓰면 회복 불가 — 그래서 archive-before-overwrite와 50% 가드가 필수.

## 새 스크레이퍼 작성 시
250줄 이내, `#!/usr/bin/env python3`, `main()`, 정중한 지연 >=0.5s, 차단 시 중단.
