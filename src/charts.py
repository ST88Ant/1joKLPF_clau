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


# ── [수정사항] 재검증 ────────────────────────────────────────────────────
#   원 분석의 결론을 뒤집는 증거를 보여주는 그림들. 색은 '문제/정상' 두 정체성만 쓴다.
PROBLEM, NORMAL = C.CAT[1], C.CAT[0]


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
        x=rank, y=cum, mode="lines", line=dict(color=PROBLEM, width=2),
        hovertemplate="상위 %{x}개 동이<br><b>서울 전체 지출의 %{y:.1f}%</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=rank, y=rank / len(s) * 100, mode="lines", name="균등 분포",
                             line=dict(color=C.BASELINE, width=2, dash="dash"), hoverinfo="skip"))
    fig.data[0].name = "실제 누적 비중"
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
    fig = go.Figure(go.Bar(
        x=10 ** ((edges[:-1] + edges[1:]) / 2), y=cnt, width=(hi - lo) * 0.92, marker_color=NORMAL,
        customdata=np.stack([lo, hi], axis=1),
        hovertemplate="1인당 %{customdata[0]:,.0f}–%{customdata[1]:,.0f}만원<br><b>%{y}개 동</b><extra></extra>"))
    fig.add_vline(x=float(pc.median()), line_dash="dash", line_color=C.INK2, line_width=1,
                  annotation_text=f"중앙값 {pc.median():.0f}만원 (월 {pc.median() / 3:.0f}만원)",
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
