# -*- coding: utf-8 -*-
"""페이지 공통 UI 조각 — 번호 붙은 표·그림 블록, 숫자 포맷"""

from __future__ import annotations

import pandas as pd
import streamlit as st

PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def figure(no: int, fig, note: str | None = None) -> None:
    st.markdown(f"**그림 {no}.**")
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
    if note:
        st.caption(note)


def table(no: int, title: str, df: pd.DataFrame, note: str | None = None, fmt: dict | None = None,
          height: int | None = None, **kw) -> None:
    st.markdown(f"**표 {no}. {title}**")
    if height:
        kw["height"] = height
    st.dataframe(formatted(df, fmt) if fmt else df, width="stretch", hide_index=True, **kw)
    if note:
        st.caption(note)


def formatted(df: pd.DataFrame, fmt: dict) -> pd.DataFrame:
    """fmt 에 있는 컬럼을 표시용 문자열로 바꾼다. 결측은 '-' (st.dataframe 은 NaN 을 'None' 으로 보여서)."""
    out = df.copy()
    for col, f in fmt.items():
        if col in out:
            out[col] = [("-" if pd.isna(v) else f.format(v)) for v in out[col]]
    return out


def eok(v: float) -> str:
    return f"{v:+,.0f}억" if abs(v) < 10000 else f"{v / 10000:+,.2f}조"
