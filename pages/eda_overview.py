# -*- coding: utf-8 -*-
import streamlit as st

from src import charts as G
from src import data as D
from src import tables as T
from src.ui import figure, header, table

header("📋 데이터 개요", "표 1–4 · 그림 1–3 — 구조, 컬럼, 결측, 기술통계")

df = D.dong()

a, b = st.columns([1, 2])
with a:
    table(1, "데이터셋 개요", T.overview(df))
with b:
    table(2, "컬럼 사전 (원본 43개)", T.column_dict(df), height=390,
          note="정성 키워드 컬럼은 고유값이 51개 — `상권_유형`마다 같은 문장이 들어 있다.")

miss = T.missing(df)
a, b = st.columns([1, 1])
with a:
    table(3, "결측치 현황과 원인", miss, fmt={"결측 비율": "{:.1%}"}, height=520)
with b:
    figure(1, G.bar_missing(miss))

table(4, "수치 컬럼 기술통계", T.describe(df),
      fmt={c: "{:,.3f}" for c in ["평균", "표준편차", "최소", "25%", "중앙값", "75%", "최대", "왜도"]} | {"개수": "{:.0f}"},
      note="|왜도| ≥ 2 인 컬럼은 로그 변환 후 분석 권장. 배율은 평균(1.73)이 아니라 중앙값(0.90)을 볼 것.")

a, b = st.columns(2)
with a:
    figure(2, G.hist_ratio(df), "로그 축 기준 거의 대칭. 서울 행정동 대부분은 기대보다 약간 덜 쓴다.")
with b:
    figure(3, G.hist_trend(df), "±5%p/년 안쪽이 '안정'. 꼬리 쪽이 개선·악화 동.")
