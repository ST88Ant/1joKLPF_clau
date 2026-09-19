# -*- coding: utf-8 -*-
import streamlit as st

from src import charts as G
from src import config as C
from src import data as D
from src import tables as T
from src.ui import figure, header, table

header("📊 분포 분석", "표 5–8 · 그림 4–10 — 범주별 구성, 태그·업종 빈도")

df = D.dong(("행정동_코드", "자치구", "행정동_코드_명", "기회_유형", "금융MBTI", "상권_원형", "배율",
             "잔차_추세_pct", "기회점수", "아파트시가_억", "청년인구비율", "1인가구비율"))
MED_FMT = {"배율_중앙값": "×{:.2f}", "추세_중앙값(%p)": "{:+.1f}", "시가_중앙값_억": "{:.1f}",
           "청년인구비율": "{:.1%}", "1인가구비율": "{:.1%}", "비율": "{:.1%}", "동수": "{:.0f}"}

st.subheader("기회 유형")
a, b = st.columns([1.2, 1])
with a:
    table(5, "기회 유형별 분포와 의미", T.opp_table(df),
          fmt={"배율_중앙값": "×{:.2f}", "추세_중앙값(%p)": "{:+.1f}", "점수_중앙값": "{:.1f}", "비율": "{:.1%}"})
with b:
    figure(4, G.bar_count(df, "기회_유형", C.OPP_ORDER + ["데이터점검"], C.OPP_COLOR, "기회 유형별 동 수"))

st.subheader("금융MBTI · 상권 원형")
a, b = st.columns(2)
with a:
    table(6, "금융MBTI별 분포와 지표 중앙값", T.dist_with_median(df, "금융MBTI", C.MBTI_ORDER), fmt=MED_FMT)
    figure(5, G.bar_count(df, "금융MBTI", C.MBTI_ORDER, C.MBTI_COLOR, "금융MBTI별 동 수"))
with b:
    table(7, "상권 원형별 분포와 지표 중앙값", T.dist_with_median(df, "상권_원형", C.ARCH_ORDER), fmt=MED_FMT)
    figure(6, G.bar_count(df, "상권_원형", C.ARCH_ORDER, None, "상권 원형별 동 수"))

a, b = st.columns(2)
with a:
    figure(7, G.box_by(df, "금융MBTI", "아파트시가_억", C.MBTI_ORDER, C.MBTI_COLOR,
                       "금융MBTI별 아파트 평균 시가", "아파트 평균 시가 (억, 로그)", log=True),
           "자산안정형만 뚜렷하게 높다 — 금융MBTI 군집의 자산 축이 잘 드러난다.")
with b:
    figure(8, G.box_by(df, "상권_원형", "배율", C.ARCH_ORDER, dict(zip(C.ARCH_ORDER, [C.CAT[0]] * 8)),
                       "상권 원형별 배율", "배율 (로그)", log=True),
           "원형별 중앙값은 ×0.77–1.02로 비슷하다(직주혼합형 4곳 제외) — 배율은 원형보다 동 개별 사정에 좌우된다.")

st.subheader("키워드 태그 · 업종")
axis = st.radio("태그 축", ["전체", "접근성·인프라", "소비·배후수요", "환경·리스크"], horizontal=True)
t = D.tags(None if axis == "전체" else axis)
a, b = st.columns([1, 1.3])
with a:
    table(8, "축별 태그 빈도 Top 8", T.tag_top(D.tags()).reset_index())
with b:
    figure(9, G.bar_tags(t))
figure(10, G.bar_biz_gap(D.biz_gap()),
       "공백 = 같은 원형 동 대비 지출 비중 ×0.75 이하, 강점 = ×1.35 이상. 공백은 생활용품(124)·의류·신발(113)·의료(95) 순. 생활용품은 강점(133)도 가장 많아 동네별 편차가 크다.")
