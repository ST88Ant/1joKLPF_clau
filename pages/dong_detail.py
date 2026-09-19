# -*- coding: utf-8 -*-
import streamlit as st

from src import config as C
from src import data as D
from src.ui import header

header("🔍 행정동 상세", "한 동의 키워드 · 업종 · 모델 결과를 한 화면에 (지도에서 클릭한 동이 자동 선택됨)")

gus = D.gu_list()
code0 = st.session_state.get("detail_code")
gu0 = D.dong_one(code0)["자치구"] if code0 else "강남구"

c1, c2 = st.columns(2)
gu = c1.selectbox("자치구", gus, index=gus.index(gu0))
names = D.dong_names(gu)
codes = names["행정동_코드"].tolist()
idx = codes.index(code0) if code0 in codes else 0
code = c2.selectbox("행정동", codes, index=idx,
                    format_func=dict(zip(names["행정동_코드"], names["행정동_코드_명"])).get)
st.session_state["detail_code"] = code
d = D.dong_one(code)


def v(x, f="{}"):
    return "-" if x is None or x != x else f.format(x)


st.markdown(f"## {d['자치구']} {d['행정동_코드_명']}")
opp = d["기회_유형"]
st.markdown(f"**{opp}** — {C.OPP_DESC.get(opp, '집계 이상치 — 해석 제외')}")
if d["해석주의"]:
    st.warning(d["해석주의"])

k = st.columns(4)
k[0].metric("배율", v(d["배율"], "×{:.2f}"), help="실제 소비 ÷ 기대 소비")
k[1].metric("격차 (분기)", v(d["격차금액_억"], "{:+,.0f}억"))
k[2].metric("잔차 추세 (%p/년)", v(d["잔차_추세_pct"], "{:+.1f}"))
k[3].metric("기회점수 · 순위", f"{v(d['기회점수'], '{:.1f}')} · {v(d['기회순위'], '#{:.0f}')}")
k = st.columns(3)
k[0].metric("금융MBTI", v(d["금융MBTI"]))
k[1].metric("상권 원형", v(d["상권_원형"]))
k[2].metric("소비 수준", {"저평가": "기대 미만", "초과달성": "기대 초과"}.get(d["유형"], d["유형"]))

st.info(d["기회_인사이트"])

a, b = st.columns(2)
with a:
    st.subheader("키워드 태그")
    for col, lab in [("키워드_접근성인프라", "접근성·인프라"), ("키워드_소비배후수요", "소비·배후수요"),
                     ("키워드_환경리스크", "환경·리스크")]:
        st.markdown(f"**{lab}**  \n{v(d[col])}")
    st.subheader("업종")
    st.markdown(f"**공백 (들어갈 자리)**: {v(d['업종_공백'])}  \n**강점 (이미 포화)**: {v(d['업종_강점'])}")
    st.markdown(f"**타깃 업종**: {v(d['타깃_업종'])}")
    st.markdown(f"**비추천·주의 업종**: {v(d['비추천_주의_업종'])}")
with b:
    st.subheader("현장 키워드 (apt.wiki)")
    st.caption(f"상권 유형: {v(d['상권_유형'])} — 같은 유형의 동은 같은 문장을 공유")
    for col, lab in [("대표_아파트_단지", "대표 단지"), ("접근성_교통_키워드", "접근성·교통"),
                     ("상권_장점_키워드", "장점"), ("상권_단점_리스크_키워드", "단점·리스크"),
                     ("주요_배후수요_특성", "배후수요"), ("상권_한줄평", "한줄평")]:
        st.markdown(f"**{lab}**: {v(d[col])}")

st.subheader("정량 지표")
q = st.columns(3)
q[0].metric("상주인구", v(d["상주인구"], "{:,.0f}명"))
q[1].metric("직장인구", v(d["직장인구"], "{:,.0f}명"))
q[2].metric("아파트 평균 시가", v(d["아파트시가_억"], "{:.1f}억"))
q = st.columns(3)
q[0].metric("청년인구비율", v(d["청년인구비율"], "{:.1%}"))
q[1].metric("1인가구비율", v(d["1인가구비율"], "{:.1%}"))
q[2].metric("지하철역 · 집객시설", f"{v(d['지하철역'], '{:.0f}')}개 · {v(d['집객시설'], '{:.0f}')}개")
