# -*- coding: utf-8 -*-
"""
네이버 검색 트렌드 결합 온·오프라인 소비 분석 페이지
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import naver_data as ND
from src.ui import figure, header, table

header("🟢 네이버 검색 트렌드 결합 온·오프라인 소비 분석",
       "서울시 상권분석서비스 10대 소비 지출 데이터 & 네이버 클라우드 플랫폼(NAVER API HUB) 데이터랩 검색 트렌드 (2021Q1~2026Q2, 22분기 패널)")

# 상단 핵심 요약 메트릭
c = st.columns(4)
c[0].metric("분석 패널 기간", "22개 분기", help="2021년 1분기 ~ 2026년 2분기")
c[1].metric("동행성 1위 (외식)", "r = +0.86", help="음식 지출과 네이버 맛집/카페 검색량의 상관계수")
c[2].metric("선행 탐색 1위 (미용/헬스)", "r = +0.69 (t-1)", help="운동/뷰티는 1분기 전 사전 검색이 지출을 선행")
c[3].metric("최대 검색 독점", "동대문 87.7%", help="동대문구 '경희의료원' 검색이 구 전체 상위 검색의 87.7% 차지")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 10대 소비 동행성 상관분석",
    "⏱️ 시차(Lead-Lag) 선행성 분석",
    "🏙️ 25개 자치구 앵커 키워드 & 독점율",
    "🔍 자치구별 전수 키워드 사전",
])

# -------------------------------------------------------------
# TAB 1: 10대 소비 동행성 상관분석
# -------------------------------------------------------------
with tab1:
    st.subheader("10대 소비 카테고리별 실제 카드 지출 vs 네이버 검색량 상관계수")
    st.markdown("""
    소비자가 온라인에서 사전에 검색하는 관심도(네이버 데이터랩 지수)와 오프라인 가맹점에서 실제로 결제한 카드 지출액(서울시 상권분석)의 **피어슨(선형) 및 스피어만(순위) 상관계수**를 산출했습니다.
    """)
    
    df_corr = pd.DataFrame(ND.CATEGORY_CORR_DATA)
    
    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        # Plotly Bar Chart
        colors = ["#22c55e" if r > 0.5 else "#3b82f6" if r > 0 else "#ef4444" for r in df_corr["피어슨"]]
        fig_corr = go.Figure(go.Bar(
            x=df_corr["피어슨"],
            y=df_corr["카테고리"],
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v:+.3f}" for v in df_corr["피어슨"]],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>피어슨 r: %{x:.4f}<extra></extra>"
        ))
        fig_corr.update_layout(
            title="소비 카테고리별 온·오프라인 동행 지수 (피어슨 r)",
            xaxis_title="상관계수 (r)",
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        
    with col_b:
        table_view = df_corr[["순위", "카테고리", "피어슨", "스피어만", "특성"]].copy()
        st.dataframe(
            table_view,
            column_config={
                "피어슨": st.column_config.NumberColumn(format="%+.4f"),
                "스피어만": st.column_config.NumberColumn(format="%+.4f"),
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
    st.markdown("""
    #### 💡 핵심 인사이트
    1. **외식·식음료의 압도적 동행성 ($r = +0.8607$)**:
       - '맛집', '카페', '배달음식' 검색량이 증가하는 분기마다 서울시 전체 음식 카드 지출액도 정확히 비례하여 급증합니다. 소비자들이 오프라인 방문 직전 네이버 검색을 필수 탐색 관문으로 활용하고 있습니다.
    2. **유흥 지출의 동행성 ($r = +0.6713$)**:
       - '술집', '와인바', '이자카야' 검색 역시 오프라인 주점 카드 매출과 뚜렷한 정(+)의 상관을 보이며, 모임 및 2차 탐색이 검색량에 즉각 반영됩니다.
    3. **생활용품·식료품의 음(-)의 상관 관계**:
       - 대형마트 장보기나 생활용품은 일상 반복 소비재로, 오프라인 매출이 둔화될 때 온라인 최저가 비교 검색이 급증하는 **대체재적 성격**을 나타냅니다.
    """)

# -------------------------------------------------------------
# TAB 2: 시차(Lead-Lag) 선행성 분석
# -------------------------------------------------------------
with tab2:
    st.subheader("시차(Lead-Lag) 분석: 검색은 소비를 선행하는가?")
    st.markdown("""
    소비자가 **검색을 먼저 하고 결제는 나중에 하는지(1분기 선행 $t-1$)**, **검색과 결제가 같은 분기에 일어나는지(동행 $t$)**, 혹은 **소비 후에 후기를 검색하는지(1분기 후행 $t+1$)** 시차 교차 상관을 분석했습니다.
    """)
    
    df_lag = pd.DataFrame(ND.LEAD_LAG_DATA)
    
    # Grouped Bar chart
    fig_lag = go.Figure()
    fig_lag.add_trace(go.Bar(
        name="1분기 선행 (t-1, 검색 먼저)",
        x=df_lag["카테고리"],
        y=df_lag["선행_t_minus_1"],
        marker_color="#8b5cf6"
    ))
    fig_lag.add_trace(go.Bar(
        name="동행 (t, 동시 발생)",
        x=df_lag["카테고리"],
        y=df_lag["동행_t"],
        marker_color="#3b82f6"
    ))
    fig_lag.add_trace(go.Bar(
        name="1분기 후행 (t+1, 소비 먼저)",
        x=df_lag["카테고리"],
        y=df_lag["후행_t_plus_1"],
        marker_color="#94a3b8"
    ))
    fig_lag.update_layout(
        barmode="group",
        title="시차별 온·오프라인 상관계수 비교",
        xaxis_title="소비 카테고리",
        yaxis_title="상관계수 (r)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
    )
    st.plotly_chart(fig_lag, use_container_width=True)
    
    st.dataframe(
        df_lag[["카테고리", "선행_t_minus_1", "동행_t", "후행_t_plus_1", "최적시점", "행동특성"]],
        column_config={
            "선행_t_minus_1": st.column_config.NumberColumn("1분기 선행 (t-1)", format="%+.3f"),
            "동행_t": st.column_config.NumberColumn("동행 (t)", format="%+.3f"),
            "후행_t_plus_1": st.column_config.NumberColumn("1분기 후행 (t+1)", format="%+.3f"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("""
        **⚡ 즉시 탐색형 소비군 (외식, 유흥)**
        - **최적 시점**: 동행 ($t$) ($r = 0.861, 0.671$)
        - **행동 패턴**: 검색 당일~당주 매장 방문 및 결제
        - **마케팅 전략**: 실시간 네이버 플레이스 순위 최적화, 당일 할인 프로모션 필수
        """)
    with c2:
        st.info("""
        **🗓️ 계획 탐색형 소비군 (미용/헬스, 의료비, 여가문화)**
        - **최적 시점**: **1분기 선행 ($t-1$)** ($r = 0.690, 0.087$)
        - **행동 패턴**: 운동·피부과·공연은 분기 전부터 검색 및 정보 수집
        - **마케팅 전략**: 오프라인 성수기보다 **1~2개월 앞선 온라인 마케팅 집행**이 매출 직결
        """)

# -------------------------------------------------------------
# TAB 3: 25개 자치구 앵커 키워드 & 독점율
# -------------------------------------------------------------
with tab3:
    st.subheader("서울시 25개 자치구별 1위 앵커 키워드 및 검색 독점율")
    st.markdown("""
    각 자치구 내에서 가장 많은 검색량을 기록한 **1위 앵커 키워드와 해당 키워드의 구 내 검색 독점율(%)**입니다.
    특정 랜드마크나 상권이 해당 구의 대중 인식을 얼마나 지배하고 있는지를 보여줍니다.
    """)
    
    df_anchor = pd.DataFrame(ND.GU_ANCHOR_KEYWORDS)
    
    # Filter by region
    selected_region = st.radio("권역 필터", ["전체", "동남권", "도심권", "서북권", "서남권", "동북권"], horizontal=True)
    if selected_region != "전체":
        df_anchor_filtered = df_anchor[df_anchor["권역"] == selected_region]
    else:
        df_anchor_filtered = df_anchor

    fig_anchor = px.bar(
        df_anchor_filtered.sort_values("독점율", ascending=True),
        x="독점율",
        y="자치구",
        color="권역",
        text="키워드1위",
        orientation="h",
        title=f"자치구별 1위 키워드 검색 독점율 (%) - {selected_region}",
        labels={"독점율": "1위 키워드 검색 독점율 (%)", "자치구": "자치구"},
        height=max(350, len(df_anchor_filtered) * 26)
    )
    fig_anchor.update_traces(textposition="inside", insidetextanchor="middle")
    fig_anchor.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_anchor, use_container_width=True)

    st.dataframe(
        df_anchor_filtered[["자치구", "권역", "키워드1위", "지수1위", "키워드2위", "키워드3위", "독점율", "앵커특성"]],
        column_config={
            "지수1위": st.column_config.NumberColumn("1위 지수", format="%.1f"),
            "독점율": st.column_config.NumberColumn("1위 독점율", format="%.1f%%"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    st.subheader("주요 5대 자치구 온·오프라인 결합 패널 분석")
    df_panel = pd.DataFrame(ND.GU_PANEL_DATA)
    st.dataframe(
        df_panel,
        column_config={"상관계수": st.column_config.NumberColumn(format="%+.4f")},
        hide_index=True,
        use_container_width=True
    )

# -------------------------------------------------------------
# TAB 4: 자치구별 전수 키워드 사전
# -------------------------------------------------------------
with tab4:
    st.subheader("서울시 25개 자치구별 전수 네이버 검색 키워드 사전")
    st.markdown("특정 자치구를 선택하면 해당 구의 대표 상권, 특화 분야, 대표 추천 키워드 세트 및 **10대 소비 카테고리별 매핑 키워드**를 확인할 수 있습니다.")
    
    gu_names = list(ND.GU_DETAIL_MAPPING.keys())
    sel_gu = st.selectbox("자치구를 선택하세요", gu_names, index=0)
    
    info = ND.GU_DETAIL_MAPPING[sel_gu]
    
    k1, k2, k3 = st.columns([1, 1.5, 2.5])
    k1.metric("권역", info["권역"])
    k2.markdown(f"**대표 상권**<br>{info['대표상권']}", unsafe_allow_html=True)
    k3.markdown(f"**핵심 특화 분야**<br>{info['특화분야']}", unsafe_allow_html=True)
    
    st.markdown("**네이버 대표 추천 키워드 세트**")
    tag_html = " ".join([f"<span style='background-color:#059669;color:white;padding:4px 8px;border-radius:12px;margin:2px;display:inline-block;font-size:13px;'>{k}</span>" for k in info["대표세트"]])
    st.markdown(tag_html, unsafe_allow_html=True)
    st.write("")
    
    st.markdown("#### 10대 카테고리별 정밀 매핑 검색어")
    cat_items = list(info["카테고리"].items())
    
    col_left, col_right = st.columns(2)
    for i, (cat, kws) in enumerate(cat_items):
        target_col = col_left if i < 5 else col_right
        with target_col:
            with st.container(border=True):
                st.markdown(f"**{cat}**")
                st.caption(kws)
