# -*- coding: utf-8 -*-
"""경로 · 색상 · 범주 순서 · 지표 정의 (대시보드 전역 상수)"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
P_DONG = DATA / "dong.parquet"
P_DONG_GEO = DATA / "dong_geo.parquet"
P_GU_GEO = DATA / "gu_geo.parquet"
P_GU = DATA / "gu_summary.parquet"
P_TAGS = DATA / "tags.parquet"
P_GAP = DATA / "biz_gap.parquet"

SEOUL_CENTER = (37.5585, 126.9900)

# ── 색상 (dataviz 기본 팔레트: 슬롯 순서 고정, 순환 금지) ─────────────────
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, GRID, BASELINE = "#fcfcfb", "#e1e0d9", "#c3c2b7"
NEUTRAL = "#f0efec"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
DIV_BLUE_RED = ["#1c5cab", "#6da7ec", "#cde2fb", NEUTRAL, "#f6c9c8", "#ec8a89", "#c03a39"]
GRAY = "#b5b3ab"

# ── 범주 순서 & 색 (범주 → 색이 항상 같도록 고정) ────────────────────────
OPP_ORDER = ["① 선점형 기회", "② 유출보완형 기회", "③ 확장형",
             "④ 검증·포화형", "⑤ 경고(둔화)", "⑥ 주의(위축)"]
OPP_COLOR = dict(zip(OPP_ORDER, CAT[:6])) | {"데이터점검": GRAY}
OPP_DESC = {
    "① 선점형 기회": "기대 미만 + 격차 축소 중 → 임대료 오르기 전 진입",
    "② 유출보완형 기회": "기대 미만 + 안정 → 빠진 필수 업종을 채우는 근린형",
    "③ 확장형": "기대 이상 + 성장 중 → 2선 골목·공백 업종 공략",
    "④ 검증·포화형": "기대 이상 + 안정 → 차별화 없으면 비추천",
    "⑤ 경고(둔화)": "기대 이상 + 식는 중 → 신규 진입 보수적",
    "⑥ 주의(위축)": "기대 미만 + 악화 중 → 원인 확인 전 보류",
}
MBTI_ORDER = ["자산안정형", "알뜰안정형", "생활압박형", "영앤레버리지형"]
MBTI_COLOR = dict(zip(MBTI_ORDER, CAT[:4]))
TYPE_ORDER = ["저평가", "기대수준", "초과달성"]
TYPE_COLOR = dict(zip(TYPE_ORDER, CAT[:3]))
ARCH_ORDER = ["근린주거형", "가족·아파트단지형", "청년1인·원룸형", "학원가·에듀형",
              "오피스·업무형", "고자산·아파트형", "광역집객·관광형", "직주혼합형"]

# ── 지도 지표: 컬럼 → (표시명, 척도, 표시 형식) ──────────────────────────
#   척도: div_log(배율, ×1 중심) · div(0 중심) · seq(크기) · cat(범주)
MAP_METRICS = {
    "기회_유형": ("기회 유형", "cat", None),
    "배율": ("배율 (실제÷기대 소비)", "div_log", "×{:.2f}"),
    "잔차_추세_pct": ("잔차 추세 (%p/년)", "div", "{:+.1f}"),
    "기회점수": ("기회점수 (①·②만)", "seq", "{:.1f}"),
    "금융MBTI": ("금융MBTI", "cat", None),
    "상권_원형": ("상권 원형", "cat", None),
    "상주인구": ("상주인구", "seq", "{:,.0f}명"),
    "직장인구": ("직장인구", "seq", "{:,.0f}명"),
    "1인가구비율": ("1인가구비율", "seq", "{:.1%}"),
    "청년인구비율": ("청년인구비율", "seq", "{:.1%}"),
    "아파트시가_억": ("아파트 평균 시가 (억)", "seq", "{:.1f}억"),
    "집객시설": ("집객시설 수", "seq", "{:,.0f}개"),
}
# 서울 전체(자치구) 보기용 지표
GU_METRICS = {
    "배율_중앙값": ("배율 중앙값", "div_log", "×{:.2f}"),
    "추세_중앙값_pct": ("잔차 추세 중앙값 (%p/년)", "div", "{:+.1f}"),
    "n_1": ("① 선점형 동 수", "seq", "{:.0f}개"),
    "n_2": ("② 유출보완형 동 수", "seq", "{:.0f}개"),
    "아파트시가_중앙값_억": ("아파트 시가 중앙값 (억)", "seq", "{:.1f}억"),
    "1인가구비율_중앙값": ("1인가구비율 중앙값", "seq", "{:.1%}"),
    "상주인구_합": ("상주인구 합계", "seq", "{:,.0f}명"),
}
ALL_METRICS = MAP_METRICS | GU_METRICS
CAT_COLORS = {"기회_유형": OPP_COLOR, "금융MBTI": MBTI_COLOR,
              "상권_원형": dict(zip(ARCH_ORDER, CAT))}

NUM_COLS = ["배율", "격차금액_억", "잔차_추세_pct", "기회점수", "상주인구", "직장인구", "직주비",
            "청년비율", "청년인구비율", "1인가구비율", "아파트시가_억", "아파트비중순위",
            "지하철역", "집객시설"]
# 상관 분석용 — 기회점수(①·②만 존재)와 격차금액(배율에서 파생)은 제외
CORR_COLS = [c for c in NUM_COLS if c not in ("기회점수", "격차금액_억")]
