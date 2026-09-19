# -*- coding: utf-8 -*-
"""
서울 행정동 상권 기회 대시보드 — 진입점

    streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="서울 상권 기회 대시보드", page_icon="🏙️", layout="wide")

pages = {
    "개요": [
        st.Page("pages/home.py", title="홈", icon="🏠", default=True),
    ],
    "기본 EDA": [
        st.Page("pages/eda_overview.py", title="데이터 개요", icon="📋"),
        st.Page("pages/eda_distribution.py", title="분포 분석", icon="📊"),
        st.Page("pages/eda_relationship.py", title="관계 분석", icon="🔗"),
        st.Page("pages/eda_district.py", title="자치구 비교", icon="🏙️"),
    ],
    "지도 · 탐색": [
        st.Page("pages/map.py", title="상권 지도", icon="🗺️"),
        st.Page("pages/opportunity.py", title="기회 탐색", icon="🎯"),
        st.Page("pages/dong_detail.py", title="행정동 상세", icon="🔍"),
    ],
}

st.navigation(pages).run()
