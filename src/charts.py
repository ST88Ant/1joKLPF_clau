# -*- coding: utf-8 -*-
"""Plotly 차트 빌더 — 모든 차트는 hover 툴팁 포함, 색은 config 의 고정 매핑만 사용"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src import config as C

FONT = "Malgun Gothic, Apple SD Gothic Neo, Noto Sans KR, system-ui, sans-serif"


def style(fig: go.Figure, title: str | None = None, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15, color=C.INK)) if title else None,
        height=height, margin=dict(l=10, r=10, t=(88 if legend else 50) if title else 20, b=10),
        font=dict(family=FONT, size=12, color=C.INK2),
        paper_bgcolor=C.SURFACE, plot_bgcolor=C.SURFACE,
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=C.INK), bordercolor=C.GRID),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, title=None),
        bargap=0.25,
    )
    fig.update_xaxes(gridcolor=C.GRID, linecolor=C.BASELINE, zeroline=False, title_font=dict(color=C.INK2))
    fig.update_yaxes(gridcolor=C.GRID, linecolor=C.BASELINE, zeroline=False, title_font=dict(color=C.INK2))
    return fig


def _bar_marks(fig: go.Figure) -> go.Figure:
    fig.update_traces(marker_line_color=C.SURFACE, marker_line_width=2, selector=dict(type="bar"))
    return fig


# ── 분포 ───────────────────────────────────────────────────────────────
def hist_ratio(df: pd.DataFrame) -> go.Figure:
    """배율 분포 (로그 축) + 저평가/초과달성 기준선"""
    x = np.log10(df["배율"])
    edges = np.linspace(-1, 2, 46)
    cnt, _ = np.histogram(x, bins=edges)
    mids = 10 ** ((edges[:-1] + edges[1:]) / 2)
    lo, hi = 10 ** edges[:-1], 10 ** edges[1:]
    fig = go.Figure(go.Bar(
        x=mids, y=cnt, width=(hi - lo) * 0.92, marker_color=C.CAT[0],
        customdata=np.stack([lo, hi], axis=1),
        hovertemplate="배율 ×%{customdata[0]:.2f}–×%{customdata[1]:.2f}<br><b>%{y}개 동</b><extra></extra>"))
    fig.update_xaxes(type="log", tickvals=[0.1, 0.25, 0.5, 1, 2, 5, 10, 50],
                     ticktext=["×0.1", "×0.25", "×0.5", "×1", "×2", "×5", "×10", "×50"],
                     title="배율 (실제 ÷ 기대 소비, 로그 축)")
    fig.update_yaxes(title="행정동 수")
    for v, t in [(2 / 3, "저평가 ×0.67"), (1.5, "초과달성 ×1.5")]:
        fig.add_vline(x=v, line_dash="dash", line_color=C.INK2, line_width=1,
                      annotation_text=t, annotation_font_color=C.INK2,
                      annotation_position="top left" if v < 1 else "top right")
    return style(fig, "배율 분포 — 중앙값 ×0.90, 양쪽 꼬리가 길다", legend=False)


def hist_trend(df: pd.DataFrame) -> go.Figure:
    s = df["잔차_추세_pct"].clip(-60, 60)
    fig = px.histogram(s, nbins=60, color_discrete_sequence=[C.CAT[0]])
    fig.update_traces(hovertemplate="추세 %{x:+.0f}%p/년<br><b>%{y}개 동</b><extra></extra>")
    fig.add_vline(x=0, line_color=C.INK2, line_width=1)
    fig.update_xaxes(title="잔차 추세 (%p/년, ±60에서 자름)")
    fig.update_yaxes(title="행정동 수")
    return _bar_marks(style(fig, "잔차 추세 분포 — 0 근처에 몰려 있고 양쪽이 대칭", legend=False))


def bar_missing(miss: pd.DataFrame) -> go.Figure:
    m = miss[miss["결측 수"] > 0].sort_values("결측 수")
    fig = px.bar(m, x="결측 수", y="컬럼", orientation="h", color="분류",
                 color_discrete_sequence=C.CAT, text="결측 수",
                 hover_data={"결측 비율": ":.1%", "원인": True, "분류": False})
    fig.update_traces(textposition="outside", textfont_color=C.INK2, cliponaxis=False)
    fig.update_yaxes(title=None)
    return _bar_marks(style(fig, "컬럼별 결측 수 — 대부분 설계상 빈 칸", height=520))


def bar_count(df: pd.DataFrame, col: str, order: list[str], colors: dict | None, title: str) -> go.Figure:
    vc = df[col].value_counts().reindex(order).dropna().reset_index()
    vc.columns = [col, "동 수"]
    vc["비율"] = vc["동 수"] / vc["동 수"].sum()
    fig = px.bar(vc, x="동 수", y=col, orientation="h", text="동 수",
                 color=col if colors else None, color_discrete_map=colors or {},
                 color_discrete_sequence=[C.CAT[0]], hover_data={"비율": ":.1%", col: False})
    fig.update_traces(textposition="outside", textfont_color=C.INK2, cliponaxis=False)
    fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], title=None)
    return _bar_marks(style(fig, title, legend=False))


def box_by(df: pd.DataFrame, x: str, y: str, order: list[str], colors: dict, title: str,
           ylab: str, log: bool = False) -> go.Figure:
    fig = px.box(df.dropna(subset=[x]), x=x, y=y, color=x, category_orders={x: order},
                 color_discrete_map=colors, points="outliers",
                 hover_data=["자치구", "행정동_코드_명"])
    fig.update_yaxes(title=ylab, type="log" if log else "linear")
    fig.update_xaxes(title=None)
    return style(fig, title, legend=False)


def bar_tags(t: pd.DataFrame, top: int = 15) -> go.Figure:
    vc = t.groupby(["축", "태그"]).size().reset_index(name="동 수").nlargest(top, "동 수")
    axis_color = dict(zip(["접근성·인프라", "소비·배후수요", "환경·리스크"], C.CAT[:3]))
    fig = px.bar(vc, x="동 수", y="태그", color="축", orientation="h", text="동 수",
                 color_discrete_map=axis_color)
    fig.update_traces(textposition="outside", textfont_color=C.INK2, cliponaxis=False)
    fig.update_yaxes(categoryorder="total ascending", title=None)
    return _bar_marks(style(fig, f"키워드 태그 빈도 Top {top}", height=480))


def bar_biz_gap(g: pd.DataFrame) -> go.Figure:
    vc = g.groupby(["업종", "구분"]).size().reset_index(name="동 수")
    fig = px.bar(vc, x="동 수", y="업종", color="구분", orientation="h", barmode="group",
                 color_discrete_map={"공백": C.CAT[0], "강점": C.CAT[1]},
                 category_orders={"구분": ["공백", "강점"]})
    fig.update_yaxes(categoryorder="total ascending", title=None)
    return _bar_marks(style(fig, "업종별 공백·강점 동 수 — 같은 원형 동 대비", height=420))


# ── 관계 ───────────────────────────────────────────────────────────────
def heat_pct(ct: pd.DataFrame, row_order: list[str], title: str) -> go.Figure:
    ct = ct.reindex(index=[r for r in row_order if r in ct.index],
                    columns=[c for c in C.OPP_ORDER if c in ct.columns], fill_value=0)
    pct = ct.div(ct.sum(axis=1), axis=0) * 100
    ylabels = [f"{r} (n={int(n)})" for r, n in ct.sum(axis=1).items()]
    text = [[f"{p:.0f}%<br>({int(n)})" for p, n in zip(pr, nr)] for pr, nr in zip(pct.values, ct.values)]
    fig = go.Figure(go.Heatmap(
        z=pct.values, x=[c.replace(" ", "<br>", 1) for c in pct.columns], y=ylabels,
        text=text, texttemplate="%{text}", textfont=dict(size=11),
        colorscale=[[0, "#f3f7fd"], [0.35, C.SEQ_BLUE[1]], [0.7, C.SEQ_BLUE[4]], [1, C.SEQ_BLUE[7]]],
        zmin=0, zmax=60, colorbar=dict(title="%", thickness=10),
        hovertemplate="%{y}<br>%{x}<br><b>%{z:.1f}%</b><extra></extra>", xgap=2, ygap=2))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickangle=0, side="top")
    return style(fig, title, height=130 + 46 * len(ct), legend=False)


def heat_corr(df: pd.DataFrame, cols: list[str]) -> go.Figure:
    corr = df[cols].corr(method="spearman")
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=cols, y=cols, zmin=-1, zmax=1,
        colorscale=[[0, C.DIV_BLUE_RED[0]], [0.35, C.DIV_BLUE_RED[2]], [0.5, C.NEUTRAL],
                    [0.65, C.DIV_BLUE_RED[4]], [1, C.DIV_BLUE_RED[6]]],
        text=np.round(corr.values, 2), texttemplate="%{text}", textfont=dict(size=10),
        hovertemplate="%{y} × %{x}<br><b>ρ = %{z:.2f}</b><extra></extra>", xgap=1, ygap=1,
        colorbar=dict(title="ρ", thickness=10)))
    fig.update_yaxes(autorange="reversed")
    return style(fig, "수치 컬럼 스피어만 상관 (파랑 음, 빨강 양)", height=620, legend=False)


def scatter_trend(df: pd.DataFrame, x: str, xlab: str) -> go.Figure:
    d = df[df["잔차_추세_pct"].abs() < 60].dropna(subset=[x])
    fig = px.scatter(d, x=x, y="잔차_추세_pct", color_discrete_sequence=[C.CAT[0]], opacity=0.7,
                     hover_data={"자치구": True, "행정동_코드_명": True, x: ":.3f", "잔차_추세_pct": ":+.1f"})
    b = np.polyfit(d[x], d["잔차_추세_pct"], 1)
    xs = np.linspace(d[x].min(), d[x].max(), 50)
    fig.add_trace(go.Scatter(x=xs, y=np.polyval(b, xs), mode="lines", line=dict(color=C.INK2, width=2),
                             name="추세선", hoverinfo="skip"))
    rho = d[[x, "잔차_추세_pct"]].corr(method="spearman").iloc[0, 1]
    fig.add_hline(y=0, line_color=C.BASELINE, line_width=1)
    fig.update_traces(marker=dict(size=8, line=dict(color=C.SURFACE, width=1)), selector=dict(mode="markers"))
    fig.update_xaxes(title=xlab)
    fig.update_yaxes(title="잔차 추세 (%p/년)")
    return style(fig, f"{xlab} × 잔차 추세 (ρ = {rho:.2f})", legend=False)


def scatter_quadrant(df: pd.DataFrame) -> go.Figure:
    d = df[(df["기회_유형"] != "데이터점검") & (df["잔차_추세_pct"].abs() < 60)]
    fig = px.scatter(d, x="배율", y="잔차_추세_pct", color="유형", log_x=True,
                     category_orders={"유형": C.TYPE_ORDER}, color_discrete_map=C.TYPE_COLOR, opacity=0.75,
                     hover_data={"자치구": True, "행정동_코드_명": True, "기회_유형": True,
                                 "배율": ":.2f", "잔차_추세_pct": ":+.1f", "유형": False})
    fig.update_traces(marker=dict(size=8, line=dict(color=C.SURFACE, width=1)))
    fig.add_hline(y=0, line_color=C.BASELINE)
    fig.add_vline(x=1, line_color=C.BASELINE)
    for x, y, t in [(0.2, 45, "① 선점형 (좌상)"), (8, 45, "③ 확장형 (우상)"),
                    (0.2, -45, "⑥ 주의 (좌하)"), (8, -45, "⑤ 경고 (우하)")]:
        fig.add_annotation(x=np.log10(x), y=y, text=t, showarrow=False, font=dict(color=C.MUTED, size=11))
    fig.update_xaxes(title="배율 (로그 축)", tickvals=[0.1, 0.25, 0.5, 1, 2, 5, 10, 50],
                     ticktext=["×0.1", "×0.25", "×0.5", "×1", "×2", "×5", "×10", "×50"])
    fig.update_yaxes(title="잔차 추세 (%p/년)")
    return style(fig, "수준 × 추세 사분면 — 기회 유형이 정해지는 방식", height=460)


# ── 자치구 ─────────────────────────────────────────────────────────────
def bar_gu_ratio(gu: pd.DataFrame) -> go.Figure:
    g = gu.sort_values("배율_중앙값")
    colors = [C.CAT[0] if v < 1 else C.DIV_BLUE_RED[6] for v in g["배율_중앙값"]]
    fig = go.Figure(go.Bar(
        x=g["배율_중앙값"] - 1, y=g["자치구"], base=1, orientation="h", marker_color=colors,
        customdata=g[["배율_중앙값", "행정동수", "대표원형"]],
        hovertemplate="<b>%{y}</b><br>배율 중앙값 ×%{customdata[0]:.2f}<br>"
                      "행정동 %{customdata[1]}개 · %{customdata[2]}<extra></extra>"))
    fig.add_vline(x=1, line_color=C.INK2, line_width=1)
    fig.update_xaxes(title="배율 중앙값 (×1 = 기대 수준)")
    return _bar_marks(style(fig, "자치구별 배율 중앙값 — 파랑 기대 미만 · 빨강 기대 이상", height=640, legend=False))


def bar_gu_opp(gu: pd.DataFrame) -> go.Figure:
    long = gu.melt(id_vars="자치구", value_vars=[f"n_{k}" for k in range(1, 7)], var_name="k", value_name="동 수")
    long["기회_유형"] = long["k"].map({f"n_{k}": C.OPP_ORDER[k - 1] for k in range(1, 7)})
    long["비율"] = long["동 수"] / long.groupby("자치구")["동 수"].transform("sum")
    order = (gu.assign(s=(gu["n_1"] + gu["n_3"]) / gu[[f"n_{k}" for k in range(1, 7)]].sum(axis=1))
               .sort_values("s")["자치구"].tolist())
    fig = px.bar(long, x="비율", y="자치구", color="기회_유형", orientation="h",
                 category_orders={"기회_유형": C.OPP_ORDER, "자치구": order[::-1]},
                 color_discrete_map=C.OPP_COLOR, hover_data={"동 수": True, "비율": ":.0%", "k": False})
    fig.update_xaxes(tickformat=".0%", title="행정동 비율")
    fig.update_yaxes(title=None)
    fig = _bar_marks(style(fig, "자치구별 기회 유형 구성 (①+③ 비율 높은 순)", height=700))
    fig.update_layout(legend=dict(orientation="h", y=-0.08, yanchor="top", x=0), margin=dict(b=60))
    return fig


def bar_gu_metric(gu: pd.DataFrame, col: str, label: str, fmt: str) -> go.Figure:
    g = gu.sort_values(col)
    fig = px.bar(g, x=col, y="자치구", orientation="h", color_discrete_sequence=[C.CAT[0]],
                 text=g[col].map(fmt.format))
    fig.update_traces(textposition="outside", textfont_color=C.INK2, cliponaxis=False,
                      hovertemplate="<b>%{y}</b><br>" + label + " %{text}<extra></extra>")
    fig.update_xaxes(title=label)
    fig.update_yaxes(title=None)
    return _bar_marks(style(fig, f"자치구별 {label}", height=640, legend=False))


def scatter_gu(gu: pd.DataFrame) -> go.Figure:
    fig = px.scatter(gu, x="아파트시가_중앙값_억", y="추세_중앙값_pct", size="상주인구_합", text="자치구",
                     color_discrete_sequence=[C.CAT[0]], size_max=40,
                     hover_data={"배율_중앙값": ":.2f", "상주인구_합": ":,.0f"})
    fig.update_traces(textposition="top center", textfont=dict(color=C.INK2, size=11),
                      marker=dict(line=dict(color=C.SURFACE, width=2), opacity=0.75))
    fig.add_hline(y=0, line_color=C.BASELINE)
    fig.update_xaxes(title="아파트 평균 시가 중앙값 (억)")
    fig.update_yaxes(title="잔차 추세 중앙값 (%p/년)")
    return style(fig, "자치구: 자산 수준 × 소비 추세 (원 크기 = 상주인구)", height=480, legend=False)
