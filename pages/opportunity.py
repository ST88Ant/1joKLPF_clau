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
    table(
        13, "① 선점형 기회 Top 10", T.ranking(df, C.OPP_ORDER[0]),
        fmt={"기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}", "기회점수": "{:.1f}"},
        summary="아직 소비가 기대에 못 미치지만 빠르게 살아나고 있어, 임대료가 오르기 전 선점해야 할 서울 1위~10위 유망 동네입니다.",
        details="""
##### 1. 선정 기준
* 기대치 대비 저평가되어 있고(배율 낮음), 최근 2~3년간 격차가 빠르게 줄어드는(추세 +) 동네 중 배후인구가 풍부한 곳입니다.

##### 2. 창업·투자 전략
* 신축 아파트 입주나 신설 지하철역 개통 등으로 인구가 급증하는 초입 단계인 경우가 많으므로 선제적 출점에 유리합니다.
"""
    )
with b:
    table(
        14, "② 유출보완형 기회 Top 10", T.ranking(df, C.OPP_ORDER[1]),
        fmt={"기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}", "기회점수": "{:.1f}"},
        summary="주민 배후인구는 풍부한데 동네에 쓸 만한 상가가 없어 돈이 밖으로 새는 서울 1위~10위 생활밀착형 기회 동네입니다.",
        details="""
##### 1. 선정 기준
* 상주인구와 직장인구가 풍부하지만 실제 소비가 기대의 2/3 이하(배율 ×0.67 미만)로 꾸준히 낮게 유지되는 동네입니다.

##### 2. 창업·투자 전략
* '격차금액'만큼의 소비가 매년 동네 밖으로 유출되고 있으므로, 동네에 빠져 있는 '공백 업종'(병원, 약국, 반찬, 생활용품 등)을 채워 넣으면 안전하게 단골을 확보할 수 있습니다.
"""
    )
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
table(
    15, "필터 결과", q.drop(columns=["행정동_코드", "기회_인사이트"]),
    fmt={"기회점수": "{:.1f}", "기회순위": "{:.0f}", "배율": "×{:.2f}", "격차금액_억": "{:+,.0f}",
         "잔차_추세_pct": "{:+.1f}"}, height=420,
    summary="사용자가 설정한 자치구, 기회 유형, 상권 원형, 금융MBTI, 태그 등의 조건에 맞는 행정동 맞춤 목록입니다.",
    details="""
##### 1. 맞춤형 상권 탐색
* 본인이 창업하려는 지역(자치구), 원하는 리스크 성향(선점형 vs 유출보완형), 타깃 고객(금융MBTI)을 조합하여 후보지를 압축할 수 있습니다.

##### 2. CSV 다운로드
* 아래 버튼을 눌러 필터링된 행정동 전체 데이터를 엑셀(CSV)로 내려받아 세부 분석에 활용할 수 있습니다.
"""
)
st.download_button("필터 결과 CSV 내려받기", q.to_csv(index=False).encode("utf-8-sig"),
                   "상권기회_필터결과.csv", "text/csv")

st.divider()
table(
    16, "해석주의 동 (배율 극단)", T.caution(df), fmt={"배율": "×{:.2f}", "격차금액_억": "{:+,.0f}"},
    summary="배율이 너무 높거나(×5 이상) 너무 낮은(×0.25 이하) 22개 동으로, 데이터 착시 가능성이 있어 분리한 목록입니다.",
    details="""
##### 1. 왜 주의해서 해석해야 하나요?
* **배율 ×5 이상 (극단적 초과)**: 대기업 본사 카드 결제가 본사 주소지로 일괄 잡히거나, 대형 백화점 등이 입점해 있어 실제 동네 상권보다 통계가 부풀려졌을 수 있습니다.
* **배율 ×0.25 이하 (극단적 저평가)**: 동 전체가 대규모 재건축 공사 중이거나, 바로 옆 초대형 상권에 완전히 흡수되어 통계상 왜곡이 생겼을 수 있습니다.

##### 2. 분석 원칙
* 상권 기회 순위 계산 시 착시를 막기 위해 이 22개 동은 순위표에서 제외되었습니다.
"""
)
