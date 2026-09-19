# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_folium import st_folium

from src import config as C
from src import data as D
from src import maps as M
from src.ui import header

header("🗺️ 상권 지도",
       "지도 타일: Esri 회색 지도 · OpenStreetMap (둘 다 인증키 불필요) · "
       "처음엔 자치구 25개만 그리고, 고른 자치구의 행정동 경계만 불러온다.")

MAX_GU = 6
mode = st.radio("보기", ["서울 전체 (자치구)", "행정동 (자치구 선택)"], horizontal=True)

if mode.startswith("서울"):
    metric = st.selectbox("색으로 볼 지표", list(C.GU_METRICS), format_func=lambda k: C.GU_METRICS[k][0])
    m = M.seoul_map(metric, C.GU_METRICS[metric][0])
    st_folium(m, height=640, use_container_width=True, returned_objects=[], key=f"seoul_{metric}")
    st.caption("자치구 위에 마우스를 올리면 요약이 보입니다. 행정동 단위로 보려면 위에서 '행정동'을 고르세요.")
    st.stop()

c1, c2, c3 = st.columns([2, 1.3, 1])
with c1:
    gus = st.multiselect(f"자치구 (최대 {MAX_GU}개)", D.gu_list(), default=["강남구", "서초구"],
                         max_selections=MAX_GU)
with c2:
    metric = st.selectbox("색으로 볼 지표", list(C.MAP_METRICS), format_func=lambda k: C.MAP_METRICS[k][0])
with c3:
    top_n = st.slider("기회 Top 표시 (①·②)", 0, 20, 5, help="선택한 자치구 안에서 기회점수 상위 동에 점을 찍는다")

if not gus:
    st.info("자치구를 한 개 이상 고르세요.")
    st.stop()

gus_t = tuple(sorted(gus))
top = None
if top_n:
    top = (D.dong(("행정동_코드_명", "기회_유형", "기회순위", "기회점수", "위도", "경도", "해석주의_여부"), gus_t)
             .query("기회순위.notna() and not 해석주의_여부").nsmallest(top_n, "기회순위"))

m = M.dong_map(gus_t, metric, top)
out = st_folium(m, height=620, use_container_width=True, returned_objects=["last_active_drawing"],
                key=f"dong_{'_'.join(gus_t)}_{metric}_{top_n}")

clicked = (out or {}).get("last_active_drawing")
if clicked:
    p = clicked["properties"]
    st.session_state["detail_code"] = p["행정동_코드"]
    d = D.dong_one(p["행정동_코드"])
    st.markdown(f"### {d['자치구']} {d['행정동_코드_명']}  ·  {d['기회_유형']}")
    k = st.columns(4)
    k[0].metric("배율", f"×{d['배율']:.2f}")
    k[1].metric("잔차 추세", f"{d['잔차_추세_pct']:+.1f}%p/년")
    k[2].metric("금융MBTI", d["금융MBTI"] or "-")
    k[3].metric("상권 원형", d["상권_원형"])
    st.write(d["기회_인사이트"])
    st.page_link("pages/dong_detail.py", label="이 동 상세 보기 →", icon="🔍")
else:
    st.caption("행정동을 클릭하면 요약과 상세 보기 링크가 나타납니다.")

with st.expander("선택 자치구 행정동 목록"):
    cols = ("자치구", "행정동_코드_명", "기회_유형", "배율", "잔차_추세_pct", "기회점수", "금융MBTI", "상권_원형")
    lst = D.dong(tuple(dict.fromkeys(cols + ((metric,) if metric not in cols else ()))), gus_t)
    st.dataframe(lst.sort_values(metric, ascending=False), width="stretch", hide_index=True)
