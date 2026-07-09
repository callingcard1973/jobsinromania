---
name: iscir-normalize
description: Zero-token deterministic normalizer turning scraped ISCIR register PDFs into standardized CSVs (firms, RSVTI operators, suspended authorizations, authorized/endorsed legal persons, CAEN codes). Use when asked to normalize/parse/convert ISCIR PDFs to CSV, build lead tables from the iscir_pdfs folder, or refresh ISCIR lead data without spending model tokens. Used by the registry-scraper agent.
---

# iscir-normalize

스크레이프된 ISCIR 등록부 PDF → 표준 CSV. **Zero-token**: 순수 Python(pdfplumber + regex), LLM 호출 없음. 매달 재실행해도 모델 토큰 0.

## 왜 zero-token이 중요한가
하네스의 핵심 비용 원칙(부모 CLAUDE.md "스크립트지 LLM이 아니다"). PDF 표 파싱은 결정적 작업이므로 에이전트 추론에 맡기면 토큰 낭비 + 비결정적. 한 번 스크립트로 고정 → 갱신은 `python CODE/iscir_normalize.py` 한 줄.

## 실행
```
python CODE/iscir_normalize.py [src_dir=DATA/iscir_pdfs] [out_dir=DATA/leads]
```
의존성: `pip install pdfplumber`. 8개 lead-value 등록부만 처리(79개 PT/법령 PDF는 건너뜀).

## 처리 대상 (8)
| PDF | 출력 CSV | 내용 |
|-----|----------|------|
| Operatori-RSVTI-PJ / RSVTIPJ | operatori_rsvti_pj.csv | RSVTI 오퍼레이터 PJ + 만료일 |
| Autorizatii-suspendate | autorizatii_suspendate.csv | 정지/철회 인증 (firme) |
| Registru | registru.csv | 제재된 개인 |
| firme-ROMANIA-autorizate-IMSP-CLASIC | ..._imsp_classic.csv | 검사/측정 인증 firme |
| firme-ROMANIA-autorizate-IR-CLASIC | ..._ir_classic.csv | 들어올리기 설비 인증 firme |
| pj-avizate | pj_avizate.csv | 아비자트(승인) 법인 |
| comunicat-coduri-CAEN | comunicat_coduri_caen.csv | CAEN 코드 → 활동 (클라이언트 라우팅용) |

## 동작 방식
1. `extract_tables()` 전 페이지. 헤더 = 'crt/denumire/persoane' 포함 행, 데이터 = 첫 칸이 숫자인 행.
2. 원본 컬럼 보존 + 표준 필드 regex 추출: `cui, j_number, email, phone, date_1, date_2` (어느 셀에서든). CUI는 J-number/날짜 조각 제외.
3. 전부 ASCII 폴드(NFKD), 줄바꿈 접기.
4. CAEN comunicat은 표가 없음 → 텍스트 라인에서 `(\d{4}) 활동명` 추출.

## 한계 (정직하게)
- 멀티라인 셀이 깨진 행(예: IR-CLASIC "R e p a r a r e")은 폴드로 일부 복원되나 100% 아님 → 출력 CSV를 `portfolio-analyst`가 spot-check.
- CUI 추출은 휴리스틱(6-9자리). j_number 매칭이 더 신뢰도 높음.
- archive-before-overwrite: out_dir 기존 CSV는 lead-enricher 산출물과 이름 충돌 주의(이건 raw 정규화, enrich는 그 다음 단계).
