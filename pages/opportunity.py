# -*- coding: utf-8 -*-
import streamlit as st

from src import config as C
from src import data as D
from src import tables as T
from src.ui import header, table

header("🎯 기회 탐색", "표 13–16 — 조건으로 행정동을 거르고, 순위를 보고, CSV 로 내려받기")

COLS = ("행정동_코드", "자치구", "행정동_코드_명", "상권_원형", "금융MBTI", "상권_유형", "기회_유형", "기회점수",
        "기회순위", "배율", "격차금액_억", "잔차_추세_pct", "업종_공백", "업종_강점", "타깃_업종",
        "키워드_접근성인프라", "키워드_소비배후수요", "키워드_환경리스크", "해석주의", "기회_인사이트")
df = D.dong(COLS)

a, b = st.columns(2)
with a:
    table(13, "① 선점형 기회 Top 10", T.ranking(df, C.OPP_ORDER[0]),
          fmt={"기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}", "기회점수": "{:.1f}"})
with b:
    table(14, "② 유출보완형 기회 Top 10", T.ranking(df, C.OPP_ORDER[1]),
          fmt={"기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}", "기회점수": "{:.1f}"})
st.caption("기회순위는 ①·② 전체 통합 순위. 해석주의 동은 순위표에서 뺐다.")

st.divider()
st.subheader("조건 필터")
with st.form("filter"):
    f1, f2, f3 = st.columns(3)
    gus = f1.multiselect("자치구", D.gu_list())
    opps = f2.multiselect("기회 유형", C.OPP_ORDER, default=C.OPP_ORDER[:2])
    archs = f3.multiselect("상권 원형", C.ARCH_ORDER)
    f4, f5, f6 = st.columns(3)
    mbtis = f4.multiselect("금융MBTI", C.MBTI_ORDER)
    tags = f5.multiselect("태그 포함 (모두 만족)", sorted(D.tags()["태그"].unique()))
    lo, hi = f6.select_slider("배율 범위", options=[0.1, 0.25, 0.5, 0.67, 0.9, 1.1, 1.5, 2, 5, 100], value=(0.1, 100))
    excl = st.checkbox("해석주의 동 제외", value=True)
    st.form_submit_button("적용", type="primary")

q = df.copy()
if gus:
    q = q[q["자치구"].isin(gus)]
if opps:
    q = q[q["기회_유형"].isin(opps)]
if archs:
    q = q[q["상권_원형"].isin(archs)]
if mbtis:
    q = q[q["금융MBTI"].isin(mbtis)]
q = q[q["배율"].between(lo, hi)]
if excl:
    q = q[q["해석주의"].isna()]
if tags:
    alltags = q[["키워드_접근성인프라", "키워드_소비배후수요", "키워드_환경리스크"]].fillna("").agg(" ".join, axis=1)
    for t in tags:
        q = q[alltags.loc[q.index].str.split().map(lambda s, t=t: t in s)]

q = q.sort_values(["기회순위", "배율"], na_position="last")
st.markdown(f"**{len(q)}개 동**")
table(15, "필터 결과", q.drop(columns=["행정동_코드", "기회_인사이트"]),
      fmt={"기회점수": "{:.1f}", "기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}",
           "잔차_추세_pct": "{:+.1f}"}, height=420)
st.download_button("필터 결과 CSV 내려받기", q.to_csv(index=False).encode("utf-8-sig"),
                   "상권기회_필터결과.csv", "text/csv")

st.divider()
table(16, "해석주의 동 (배율 극단)", T.caution(df), fmt={"배율": "×{:.2f}", "격차금액_억": "{:+,.0f}"},
      note="×5↑ = 대형점·본사 매출이 주소로 잡혔을 가능성, ×0.25↓ = 인접 거대상권 흡수·재건축 영향 가능성.")
