# -*- coding: utf-8 -*-
import streamlit as st

from src import charts as G
from src import config as C
from src import data as D
from src import tables as T
from src.ui import figure, header, table

header("🔗 관계 분석", "표 9–11 · 그림 11–15 — 교차표, 상관, 추세와의 관계 (데이터점검 4개 동 제외)")


def ct_table(no, row, order, title):
    ct = D.crosstab(row, "기회_유형")
    ct = ct.reindex(index=[r for r in order if r in ct.index], columns=C.OPP_ORDER, fill_value=0)
    ct["합계"] = ct.sum(axis=1)
    table(no, title, ct.reset_index())


st.subheader("금융MBTI × 기회 유형")
a, b = st.columns([1, 1.3])
with a:
    ct_table(9, "금융MBTI", C.MBTI_ORDER, "금융MBTI × 기회 유형 (동 수)")
    st.info("영앤레버리지형은 ⑤·⑥ 비율이 58%, 자산안정형은 ①·③ 비율이 43% — 주민 금융 성향과 상권 흐름이 연결된다.")
with b:
    figure(11, G.heat_pct(D.crosstab("금융MBTI", "기회_유형"), C.MBTI_ORDER, "금융MBTI별 기회 유형 구성 (행 %)"))

st.subheader("상권 원형 × 기회 유형")
a, b = st.columns([1, 1.3])
with a:
    ct_table(10, "상권_원형", C.ARCH_ORDER, "상권 원형 × 기회 유형 (동 수)")
    st.info("청년1인·원룸형은 ⑤·⑥이 55%, 가족·아파트단지형은 ② 유출보완형이 46%.")
with b:
    figure(12, G.heat_pct(D.crosstab("상권_원형", "기회_유형"), C.ARCH_ORDER, "상권 원형별 기회 유형 구성 (행 %)"))

st.subheader("수치 변수 상관")
df = D.dong(tuple(["행정동_코드", "자치구", "행정동_코드_명", "기회_유형", "유형"] + C.NUM_COLS))
a, b = st.columns([1.4, 1])
with a:
    figure(13, G.heat_corr(df, C.CORR_COLS),
           "배율은 입력 변수와 상관이 거의 없다(|ρ| ≤ 0.11) — 모델 잔차이므로 정상.")
with b:
    table(11, "상관이 큰 변수 쌍 Top 12", T.top_pairs(df), fmt={"ρ": "{:+.2f}"},
          note="직장인구–직주비(0.95), 청년비율–청년인구비율(0.91)은 사실상 같은 정보 — 모델에는 하나만.")

st.subheader("무엇이 소비 추세와 함께 움직이나")
opts = {"청년비율": "청년비율", "청년인구비율": "청년인구비율", "1인가구비율": "1인가구비율",
        "아파트시가_억": "아파트 평균 시가 (억)", "직주비": "직주비", "집객시설": "집객시설 수"}
x = st.selectbox("x 축 변수", list(opts), format_func=opts.get)
figure(14, G.scatter_trend(df[df["기회_유형"] != "데이터점검"], x, opts[x]),
       "청년·1인가구 비율이 높을수록 기대 대비 소비가 식고, 아파트 시가가 높을수록 개선된다.")
figure(15, G.scatter_quadrant(df), "가로 = 지금 수준(배율), 세로 = 방향(추세). 사분면이 곧 기회 유형이다.")
