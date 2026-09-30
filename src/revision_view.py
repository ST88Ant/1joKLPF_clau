# -*- coding: utf-8 -*-
"""
[수정사항] 페이지 전용 — 데이터 로더 + 그림 빌더

이 페이지에 필요한 것만 **새 모듈** 안에 모아 둔다.
`config.toml` 의 `runOnSave = false` 때문에 Streamlit Cloud 는 배포 때 이미 임포트된 모듈을
다시 읽지 않는다. 기존 모듈(`config`·`data`·`charts`)에 함수를 더하면 앱을 재시작하기 전까지
`AttributeError` 가 난다. 새 모듈은 처음 임포트되므로 그 문제가 없다.

색·레이아웃은 기존 `config`·`charts` 의 것을 그대로 쓴다 (둘 다 배포본에 이미 있는 이름만 참조).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import config as C
from src.charts import style, _bar_marks

P_REV = C.DATA / "revision.parquet"
P_REV_STATS = C.DATA / "revision_stats.json"

# 문제 있는 값 / 정상 값, 두 정체성만 쓴다
PROBLEM, NORMAL = C.CAT[1], C.CAT[0]


# ── 데이터 ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def dong() -> pd.DataFrame:
    """행정동 425행 — 타깃 항목 구성·1인당 지출·잔차 통계 (scripts/build_revision.py 산출)"""
    return pd.read_parquet(P_REV)


@st.cache_data(show_spinner=False)
def stats() -> dict:
    """모델 성능·변수 중요도·순위 Top 등 스칼라와 소형 표"""
    return json.loads(P_REV_STATS.read_text(encoding="utf-8"))


# ── 그림 ───────────────────────────────────────────────────────────────
def bar_cat_share(share: dict[str, float]) -> go.Figure:
    """타깃(지출_총금액)의 항목 구성비 — 여가·문화 한 항목이 전체를 삼킨다"""
    s = pd.Series(share).sort_values()
    name = s.index.str.replace("_", "·")
    hit = s.index == "여가_문화"
    fig = go.Figure()
    for flag, label, color in [(hit, "여가·문화 (오염 항목)", PROBLEM), (~hit, "그 외 9개 항목", NORMAL)]:
        fig.add_bar(x=s[flag], y=name[flag], orientation="h", name=label, marker_color=color,
                    text=[f"{v:.1f}%" for v in s[flag]], textposition="outside",
                    hovertemplate="<b>%{y}</b><br>전체 지출의 %{x:.2f}%<extra></extra>")
    fig.update_traces(textfont_color=C.INK2, cliponaxis=False)
    fig.update_xaxes(title="서울 전체 지출에서 차지하는 비중 (%)", range=[0, 72])
    fig.update_yaxes(title=None)
    return _bar_marks(style(fig, "지출 항목 구성비 — 가계 소비구조라면 나올 수 없는 모양", height=420))


def line_concentration(spend: pd.Series) -> go.Figure:
    """상위 n개 동의 누적 지출 비중 (로렌츠 곡선)"""
    s = np.sort(spend.values)[::-1]
    cum = np.cumsum(s) / s.sum() * 100
    rank = np.arange(1, len(s) + 1)
    fig = go.Figure(go.Scatter(
        x=rank, y=cum, mode="lines", name="실제 누적 비중", line=dict(color=PROBLEM, width=2),
        hovertemplate="상위 %{x}개 동이<br><b>서울 전체 지출의 %{y:.1f}%</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=rank, y=rank / len(s) * 100, mode="lines", name="균등 분포",
                             line=dict(color=C.BASELINE, width=2, dash="dash"), hoverinfo="skip"))
    for n in (3, 10):
        fig.add_annotation(x=n, y=cum[n - 1], text=f"상위 {n}개 동 {cum[n - 1]:.0f}%",
                           showarrow=True, arrowhead=0, arrowcolor=C.MUTED, ax=48, ay=-24,
                           font=dict(color=C.INK2, size=11))
    fig.update_xaxes(title="지출 상위 행정동 수 (누적)", range=[0, 425])
    fig.update_yaxes(title="서울 전체 지출 중 누적 비중 (%)", range=[0, 102])
    return style(fig, "425개 동 중 3개가 서울 지출의 절반 — 상권 지표로 쓸 수 없는 쏠림", height=400)


def hist_percapita(pc: pd.Series) -> go.Figure:
    """1인당 분기 지출 분포 (로그 축)"""
    x = np.log10(pc.replace([np.inf, -np.inf], np.nan).dropna().clip(lower=0.1))
    edges = np.linspace(0, 5.2, 53)
    cnt, _ = np.histogram(x, bins=edges)
    lo, hi = 10 ** edges[:-1], 10 ** edges[1:]
    med = float(pc.median())
    fig = go.Figure(go.Bar(
        x=10 ** ((edges[:-1] + edges[1:]) / 2), y=cnt, width=(hi - lo) * 0.92, marker_color=NORMAL,
        customdata=np.stack([lo, hi], axis=1),
        hovertemplate="1인당 %{customdata[0]:,.0f}–%{customdata[1]:,.0f}만원<br><b>%{y}개 동</b><extra></extra>"))
    fig.add_vline(x=med, line_dash="dash", line_color=C.INK2, line_width=1,
                  annotation_text=f"중앙값 {med:.0f}만원 (월 {med / 3:.0f}만원)",
                  annotation_font_color=C.INK2, annotation_position="top right")
    fig.update_xaxes(type="log", tickvals=[1, 10, 100, 1000, 10000, 100000],
                     ticktext=["1만원", "10만원", "100만원", "1천만원", "1억", "10억"],
                     title="상주인구 1인당 분기 지출 (로그 축)")
    fig.update_yaxes(title="행정동 수")
    return style(fig, "1인당 분기 지출 — 중앙값은 월 7만원, 최상위 동은 9억", height=380, legend=False)


def bar_importance(imp: pd.DataFrame) -> go.Figure:
    """변수 중요도 — 인구 축이 거의 작동하지 않는다"""
    d = imp.sort_values("중요도")
    fig = px.bar(d, x="중요도", y="변수명", orientation="h", color="그룹",
                 category_orders={"그룹": ["인구", "인프라", "주거", "공간·시간"]},
                 color_discrete_sequence=C.CAT[:4])
    fig.update_traces(hovertemplate="<b>%{y}</b><br>중요도 %{x:.3f}<extra></extra>")
    fig.update_xaxes(title="permutation importance (R² 하락폭)")
    fig.update_yaxes(title=None)
    return _bar_marks(style(fig, "변수 중요도 Top 12 — 상주인구는 0.006, 사실상 0", height=440))


def bar_coef(coef: pd.DataFrame) -> go.Figure:
    """Ridge 계수 — 부호가 '동네 소비'와 맞지 않는다"""
    d = coef.sort_values("계수")
    up = d["계수"] >= 0
    fig = go.Figure()
    for flag, label, color in [(up, "지출을 올리는 방향", C.DIV_BLUE_RED[0]),
                               (~up, "지출을 내리는 방향", C.DIV_BLUE_RED[-1])]:
        fig.add_bar(x=d.loc[flag, "계수"], y=d.loc[flag, "변수명"], orientation="h",
                    name=label, marker_color=color,
                    hovertemplate="<b>%{y}</b><br>표준화 계수 %{x:+.3f}<extra></extra>")
    fig.add_vline(x=0, line_color=C.BASELINE)
    fig.update_xaxes(title="Ridge 표준화 계수 (log 지출 변화)")
    fig.update_yaxes(title=None)
    return _bar_marks(style(fig, "계수 Top 10 — 주말 유동이 많을수록 지출이 내려간다", height=420))


def bar_cut_vs_error(mae: float, cut: float) -> go.Figure:
    """분류 경계 vs 모델 오차"""
    fig = go.Figure()
    for v, label, color, ratio in [(cut, "분류 경계 (×1.5 / ×0.67)", NORMAL, 1.5),
                                   (mae, "모델 평균 오차 (MAE)", PROBLEM, float(np.exp(mae)))]:
        fig.add_bar(x=[v], y=[label], orientation="h", name=label, marker_color=color,
                    text=[f"{v:.3f}  (배율 ×{ratio:.2f})"], textposition="outside",
                    hovertemplate=f"<b>{label}</b><br>log 스케일 {v:.3f} · 배율 ×{ratio:.2f}<extra></extra>")
    fig.update_traces(textfont_color=C.INK2, cliponaxis=False)
    fig.update_xaxes(title="log 스케일 크기", range=[0, 0.95])
    fig.update_yaxes(title=None, showticklabels=False)
    return _bar_marks(style(fig, "경계선이 오차보다 좁다 — 라벨의 상당수는 구분되지 않는다", height=260))


def scatter_level_trend(df: pd.DataFrame, r: float) -> go.Figure:
    """잔차 수준 × 추세 — '잠재력'이라면 왼쪽이 위로 올라가야 한다"""
    d = df[df["유형"] != "데이터점검"]
    fig = px.scatter(d, x="배율", y="잔차_추세", color="유형", hover_name="행정동_코드_명",
                     category_orders={"유형": C.TYPE_ORDER}, color_discrete_map=C.TYPE_COLOR,
                     hover_data={"자치구": True, "배율": ":.2f", "잔차_추세": ":+.3f", "유형": False})
    fig.update_traces(marker=dict(size=9, opacity=0.8, line=dict(color=C.SURFACE, width=2)))
    fig.add_hline(y=0, line_color=C.BASELINE)
    fig.add_vline(x=1, line_color=C.BASELINE)
    # x 는 로그 축이므로 10의 지수로 준다 (-0.9 → ×0.13 부근, 점이 거의 없는 좌상단)
    fig.add_annotation(x=-0.9, y=0.55, xref="x", yref="y", xanchor="left", yanchor="top",
                       text=f"수준 × 추세 상관 = {r:+.2f}<br>저평가 동이 따라잡는 신호 없음",
                       showarrow=False, align="left", font=dict(color=C.INK2, size=12),
                       bgcolor="white", bordercolor=C.GRID, borderwidth=1, borderpad=6)
    fig.update_xaxes(type="log", tickvals=[0.1, 0.25, 0.5, 1, 2, 5, 10, 50],
                     ticktext=["×0.1", "×0.25", "×0.5", "×1", "×2", "×5", "×10", "×50"],
                     title="배율 (실제 ÷ 기대, 로그 축)")
    fig.update_yaxes(title="잔차 추세 (연간 log 변화)", range=[-0.6, 0.6])
    return style(fig, "저평가일수록 개선되는가? — 그런 관계는 없다", height=460)
