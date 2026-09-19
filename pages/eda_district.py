# -*- coding: utf-8 -*-
import streamlit as st

from src import charts as G
from src import config as C
from src import data as D
from src import tables as T
from src.ui import figure, header, table

header("🏙️ 자치구 비교", "표 12 · 그림 16–19 — 25개 자치구 요약 (데이터점검 4개 동 제외 집계)")

gu = D.gu_summary()
table(12, "자치구 요약 (배율 중앙값 높은 순)", T.gu_table(gu),
      fmt={"배율_중앙값": "×{:.2f}", "추세_중앙값_pct": "{:+.1f}", "아파트시가_중앙값_억": "{:.1f}",
           "1인가구비율_중앙값": "{:.1%}"},
      note="①–⑥ 열은 해당 기회 유형 동 수. 최고기회동 = 기회점수 1위 동.")

a, b = st.columns(2)
with a:
    figure(16, G.bar_gu_ratio(gu), "양천·노원·도봉은 기대 이상, 용산·중구·성북은 기대 미만.")
with b:
    figure(17, G.bar_gu_opp(gu), "관악·강서·영등포는 ⑤·⑥ 비율이 높다.")

opts = {k: v[0] for k, v in C.GU_METRICS.items()}
m = st.selectbox("그림 18 지표", list(opts), format_func=opts.get, index=1)
a, b = st.columns(2)
with a:
    figure(18, G.bar_gu_metric(gu, m, opts[m], C.GU_METRICS[m][2]))
with b:
    figure(19, G.scatter_gu(gu), "자산 수준이 높은 구일수록 소비 추세도 좋은 경향.")
