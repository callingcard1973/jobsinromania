---
name: iscir-scrape
description: Scrape iscir.ro public registers past the Cloudflare managed challenge and normalize them into DATA CSVs. Use when asked to scrape/download/refresh ISCIR registers (operatori RSVTI, persoane juridice autorizate, autorizatii suspendate/retrase, any iscir.ro PDF), get past the "Un moment va rog" Cloudflare wall, or update the ISCIR source data. Used by the registry-scraper agent.
---

# iscir-scrape

iscir.ro公개 등록부를 Cloudflare 챌린지 너머에서 받아 `DATA/*.csv`로 정규화한다.

## Cloudflare — 왜 curl이 안 되는가
iscir.ro는 **managed challenge / Turnstile**. curl·cloudscraper·번들 chromium은 모두 11-71KB "Un moment, vă rog…" 챌린지 페이지만 받는다 (정적 `wp-content/uploads/*.pdf`도 HTTP 200 text/html). **진짜 Chrome + 영속 프로필**만 통과한다.

## Fetcher (이미 빌드됨)
`CODE/iscir_fetch.py` — Playwright `launch_persistent_context(channel="chrome", headless=False, args=["--disable-blink-features=AutomationControlled"])`. 영속 프로필 `.cf_profile`이 `cf_clearance` 쿠키를 보관 → 이후 실행은 즉시 통과. 챌린지가 멈추면 열린 창에서 사람이 체크박스 클릭 가능.

```
python CODE/iscir_fetch.py "https://iscir.ro/<page>" DATA
```
페이지가 클리어되면 그 위의 모든 `.pdf` 링크를 받아 `DATA/`에 저장. 의존성: `pip install playwright` + `python -m playwright install chromium` (단, 실제 통과는 `channel="chrome"` = Program Files Chrome). pdfplumber로 파싱.

## ISCIR 공개 등록부 (스크레이프 대상)
| 페이지 | 내용 | 출력 |
|--------|------|------|
| /autorizatii-suspendate-retrase | 정지/철회된 인증 (firme + persoane) — 국가 확인 부적합 | DATA/autorizatii_suspendate.csv |
| /persoane-juridice-autorizate | 인증된 법인 전체 등록부 | DATA/pja.csv |
| (직접 PDF) Operatori-RSVTI-PJ.pdf | RSVTI 오퍼레이터 PJ (1,250행, 만료일 포함) | DATA/rsvti_pj.csv |
| /sectiune/autorizatii | 인증 허브 (하위 PDF 링크) | — |

URL 패턴: `wp-content/uploads/{YYYY}/{MM}/{Name}.pdf` (월별 갱신 — 최신 월을 listing 페이지에서 찾아라, 하드코드 금지).

## 정규화 절차
1. fetcher로 PDF 받기 → pdfplumber `extract_table()` (페이지 149개까지, 6열).
2. ASCII 폴드(NFKD). 행 필터: `nr.crt`가 숫자인 행만.
3. 컬럼 매핑 → 표준 스키마 `name, cui, county, email, phone, source_agency, scraped_at, raw_status` + 등록부 고유 필드(만료일, 인증번호, 처분유형, 처분일).
4. **Archive before overwrite**: 신규 행수 < 기존 50% → 덮어쓰지 말고 보고.
5. `_workspace/01_registry_refresh.md`에 before→after, 실패, 스키마 이상.

## 왜
ISCIR 데이터가 포트폴리오 리드의 원천. Cloudflare가 핵심 장애물이었고 진짜-Chrome 우회가 유일한 해법 — 매 갱신마다 이 fetcher를 거쳐야 한다. 월별 PDF는 URL이 바뀌므로 listing 페이지에서 링크를 동적으로 찾아라.
