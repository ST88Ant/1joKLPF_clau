# 서울 행정동 상권 기회 대시보드

> 1조 KLPF 프로젝트 — 인구·인프라 기반 소비 예측 및 ‘소비 잠재력’ 상권 발굴
> 📁 모델링·보고서 등 분석 자료는 [`analysis/`](analysis/) 폴더에 있습니다 → [분석 README](analysis/README.md) · [상권기회 인사이트 보고서](analysis/report/상권기회_인사이트_보고서.md)

서울 25개 자치구 · 425개 행정동의 **인구·인프라 기반 기대소비 대비 실제 소비(배율)**, 소비 추세, 금융MBTI, 상권 키워드를 한곳에서 보는 Streamlit 대시보드입니다.

- **기본 EDA:** 표 16개 · 그래프 19개 (모든 그래프에 마우스 오버 툴팁)
- **지도:** folium + 인증키가 필요 없는 타일 (Esri 회색 지도 · OpenStreetMap)
- **빠른 로딩:** Parquet + DuckDB(필요한 컬럼·자치구만 조회) + Polars(집계) + Streamlit 캐시

## 빠른 시작

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 <http://localhost:8501> 이 열립니다. 전처리된 Parquet(`data/processed/`)이 저장소에 들어 있어 바로 실행됩니다.

## 페이지 구성

| 메뉴 | 파일 | 내용 | 표 / 그림 |
|---|---|---|---|
| 🏠 홈 | `pages/home.py` | 핵심 지표, 메뉴 안내, 주요 발견 | – |
| 📋 데이터 개요 | `pages/eda_overview.py` | 개요 · 컬럼 사전 · 결측 · 기술통계 · 배율/추세 분포 | 표 1–4 · 그림 1–3 |
| 📊 분포 분석 | `pages/eda_distribution.py` | 기회 유형 · 금융MBTI · 상권 원형 · 태그 · 업종 공백 | 표 5–8 · 그림 4–10 |
| 🔗 관계 분석 | `pages/eda_relationship.py` | 교차표 · 상관 행렬 · 추세 산점도 · 수준×추세 사분면 | 표 9–11 · 그림 11–15 |
| 🏙️ 자치구 비교 | `pages/eda_district.py` | 25개 구 요약 · 배율 · 기회 구성 · 지표 순위 | 표 12 · 그림 16–19 |
| 🗺️ 상권 지도 | `pages/map.py` | 서울 전체(자치구) ↔ 선택 자치구의 행정동 지도, 클릭하면 요약 | folium |
| 🎯 기회 탐색 | `pages/opportunity.py` | 선점형·유출보완형 Top 10, 조건 필터, CSV 내려받기 | 표 13–16 |
| 🔍 행정동 상세 | `pages/dong_detail.py` | 한 동의 키워드 · 업종 · 모델 결과 프로필 | – |

## 폴더 구조

```
1joKLPF_clau/
├─ app.py                  진입점 (st.navigation 으로 페이지 묶음)
├─ pages/                  페이지 8개
├─ src/
│  ├─ config.py            경로 · 색 · 범주 순서 · 지도 지표 정의
│  ├─ data.py              DuckDB/Polars 데이터 접근 + 캐시
│  ├─ charts.py            Plotly 그래프 빌더
│  ├─ tables.py            EDA 표 빌더
│  ├─ maps.py              folium 지도 빌더
│  └─ ui.py                번호 붙은 표·그림 블록
├─ scripts/
│  └─ build_data.py        CSV + 행정동 경계 → Parquet 전처리
├─ data/
│  ├─ raw/                 서울시_행정동별_상권분석_통합.csv (원본)
│  ├─ processed/           대시보드가 읽는 Parquet 6개 (약 220 KB, 저장소에 포함)
│  └─ cache/               경계 원본 GeoJSON 35 MB (자동 다운로드, git 제외)
├─ .streamlit/config.toml  테마
├─ requirements.txt        실행용
├─ requirements-build.txt  전처리용 (+ shapely)
└─ analysis/               모델링 코드 · 보고서 · 이미지 (기존 분석 자료)
```

## 데이터 다시 만들기

원본 CSV가 바뀌었을 때만 필요합니다.

```bash
pip install -r requirements-build.txt
python scripts/build_data.py          # 경계 파일이 없으면 GitHub 에서 자동 다운로드
python scripts/build_data.py --offline  # data/cache 에 받아 둔 파일만 사용
```

| 출력 | 내용 |
|---|---|
| `dong.parquet` | 행정동 425행 × 49열 (원본 43 + 파생 6) |
| `dong_geo.parquet` | 행정동 경계 — 약 15 m 단순화, 좌표 소수 5자리 (GeoJSON 170 KB) |
| `gu_geo.parquet` | 자치구 경계 (행정동 경계 병합) |
| `gu_summary.parquet` | 자치구 요약 지표 |
| `tags.parquet` | 키워드 태그 long 테이블 |
| `biz_gap.parquet` | 업종 공백·강점 long 테이블 |

**경계 코드 보정:** 데이터(2025 행정동 체계)와 경계(2025-12) 사이에 바뀐 3개 동을 맞췄습니다 — 개포3동 → 일원2동(명칭 변경), 상일1·2동 → 상일동, 신설동·용두동 → 용신동(분동 전으로 병합).

## 성능 설계

| 요구 | 구현 |
|---|---|
| 지도를 빠르게 | 첫 화면은 자치구 25개(27 KB)만 → 고른 자치구(최대 6개)의 행정동 경계만 조회 |
| 전체를 한 번에 올리지 않기 | `data.dong(columns, gu)` 가 DuckDB 로 필요한 컬럼·행만 Parquet 에서 읽음 |
| 무거운 처리는 미리 | 경계 병합·단순화·태그 분해는 `build_data.py` 에서 한 번만 |
| 반복 계산 없애기 | `st.cache_data`(조회 결과·GeoJSON) · `st.cache_resource`(DuckDB 연결) |
| 브라우저 부담 줄이기 | 색·툴팁 값은 파이썬에서 계산해 GeoJSON 속성으로 전달, `prefer_canvas=True` |

## 지도 타일 (인증키 불필요)

| 레이어 | 기본 | 출처 |
|---|---|---|
| 회색 지도 | ✅ | Esri World Light Gray Canvas |
| 지명 라벨 | ✅ (폴리곤 위) | Esri World Light Gray Reference |
| 일반 지도 | 레이어 버튼으로 전환 | OpenStreetMap |

> CARTO basemaps(`CartoDB positron`)는 키 없이 쓰면 타일에 **API KEY REQUIRED** 워터마크가 찍혀(2026-09 확인) 쓰지 않았습니다.

## 배포 (Streamlit Community Cloud)

share.streamlit.io → **New app** → 저장소 `ST88Ant/1joKLPF_clau` · 브랜치 `main` · Main file `app.py` → **Deploy**

`.gitignore` 가 `__pycache__/`, `data/cache/`(35 MB 경계 원본), `.streamlit/secrets.toml` 을 제외합니다.

## 데이터 출처

- 서울시 상권분석서비스 (소비·상주인구·직장인구·집객시설·아파트)
- SKT 서울 시민생활 데이터 (청년·1인가구 비율)
- apt.wiki 단지 키워드 (정성 키워드)
- 행정동 경계: 행정안전부, [vuski/admdongkor](https://github.com/vuski/admdongkor)
