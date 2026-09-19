# -*- coding: utf-8 -*-
"""
Folium 지도 — 인증키 없는 타일만 사용 (API KEY REQUIRED 워터마크 없음)

  기본: Esri World Light Gray Canvas (+ 지명 라벨 레이어) · 선택: OpenStreetMap
  ※ CARTO basemaps(CartoDB positron)는 키 없이 쓰면 타일에 'API KEY REQUIRED' 워터마크가 찍힌다(2026-09 확인) → 사용 안 함.

빠른 로딩 전략
  1) 서울 전체 보기: 자치구 25개 경계(27 KB)만 그린다.
  2) 행정동 보기: 사용자가 고른 자치구의 행정동 경계만 Parquet 에서 읽는다.
  3) 경계는 전처리 단계에서 단순화(≈15 m)·좌표 반올림해 두었다.
  4) 색·툴팁 값은 파이썬에서 미리 계산해 GeoJSON properties 에 넣는다 (브라우저 계산 최소화).
  5) GeoJSON 은 (자치구, 지표) 조합별로 st.cache_data 캐시.
"""

from __future__ import annotations

import json

import folium
import numpy as np
import pandas as pd
import streamlit as st
from branca.element import MacroElement, Template

from src import config as C
from src import data as D

ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
ESRI_ATTR = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

TOOLTIP_DONG = ["행정동_코드_명", "자치구", "_value", "기회_유형", "배율_txt", "금융MBTI", "상권_원형"]
TOOLTIP_DONG_ALIAS = ["행정동", "자치구", "선택 지표", "기회 유형", "배율", "금융MBTI", "상권 원형"]


# ── 색 계산 ──────────────────────────────────────────────────────────────
def _bins_seq(v: pd.Series) -> tuple[np.ndarray, list[str]]:
    qs = np.unique(np.nanquantile(v, np.linspace(0, 1, 8)))
    cols = C.SEQ_BLUE[1:][: max(len(qs) - 1, 1)]
    return qs, cols


def colorize(values: pd.Series, scale: str, metric: str,
             ref: pd.Series | None = None) -> tuple[list[str], list[tuple[str, str]]]:
    """값 → 채움색 목록, 범례 항목 [(색, 라벨)]. 구간은 ref(기본 = values) 분포로 정한다."""
    ref = values if ref is None else ref
    if scale == "cat":
        cmap = C.CAT_COLORS[metric]
        fills = [cmap.get(v, C.GRAY) if isinstance(v, str) else C.GRAY for v in values]
        present = [k for k in cmap if k in set(values)]
        legend = [(cmap[k], k) for k in present]
        if values.isna().any():
            legend.append((C.GRAY, "데이터 없음"))
        return fills, legend

    v = values.astype(float)
    if scale == "div_log":
        edges = [-np.inf, np.log10(0.5), np.log10(2 / 3), np.log10(0.9), np.log10(1.1),
                 np.log10(1.5), np.log10(2), np.inf]
        labels = ["×0.5 미만", "×0.5–0.67", "×0.67–0.9", "×0.9–1.1 (기대 수준)", "×1.1–1.5", "×1.5–2", "×2 이상"]
        idx = np.digitize(np.log10(v), edges[1:-1])
        cols = C.DIV_BLUE_RED
    elif scale == "div":
        m = float(np.nanquantile(np.abs(ref.astype(float)), 0.9)) or 1.0
        edges = [-np.inf, -m * 2 / 3, -m / 3, -m / 10, m / 10, m / 3, m * 2 / 3, np.inf]
        labels = [f"{a:+.1f} ~ {b:+.1f}" for a, b in zip([-m] + edges[1:-1], edges[1:-1] + [m])]
        labels[0], labels[-1] = f"{edges[1]:+.1f} 미만", f"{edges[-2]:+.1f} 이상"
        idx = np.digitize(v, edges[1:-1])
        cols = C.DIV_BLUE_RED
    else:
        qs, cols = _bins_seq(ref.astype(float).dropna())
        fmt = C.ALL_METRICS.get(metric, (None, None, "{:,.2f}"))[2] or "{:,.2f}"
        labels = [f"{fmt.format(a)} – {fmt.format(b)}" for a, b in zip(qs[:-1], qs[1:])]
        idx = np.clip(np.digitize(v, qs[1:-1]), 0, len(cols) - 1)
    fills = [C.GRAY if np.isnan(x) else cols[i] for x, i in zip(v, idx)]
    legend = list(zip(cols, labels)) + ([(C.GRAY, "데이터 없음")] if v.isna().any() else [])
    return fills, legend


def fmt_value(v, metric: str) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    f = C.ALL_METRICS.get(metric, (None, None, None))[2]
    return f.format(v) if f and not isinstance(v, str) else str(v)


# ── GeoJSON 조립 (캐시) ──────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def dong_featurecollection(gu: tuple[str, ...], metric: str) -> tuple[dict, list]:
    scale = C.MAP_METRICS[metric][1]
    geo = D.dong_geo(gu)
    attrs = D.dong(("행정동_코드", metric, "기회_유형", "배율", "금융MBTI", "상권_원형") if metric not in
                   ("기회_유형", "배율", "금융MBTI", "상권_원형") else
                   ("행정동_코드", "기회_유형", "배율", "금융MBTI", "상권_원형"), gu)
    df = geo.merge(attrs, on="행정동_코드", how="left")
    # 색 척도는 서울 전체 분포 기준으로 고정 (자치구를 바꿔도 같은 값 = 같은 색)
    full = D.dong((metric,))[metric]
    fills, legend = colorize(df[metric], scale, metric, ref=full)
    if scale == "cat":
        legend = colorize(full, scale, metric)[1]
    feats = []
    for (_, r), fill in zip(df.iterrows(), fills):
        props = {k: (None if isinstance(r[k], float) and np.isnan(r[k]) else r[k])
                 for k in ["행정동_코드", "행정동_코드_명", "자치구", "기회_유형", "금융MBTI", "상권_원형"]}
        props.update(_fill=fill, _value=fmt_value(r[metric], metric), 배율_txt=f"×{r['배율']:.2f}")
        feats.append({"type": "Feature", "properties": props, "geometry": json.loads(r["geometry"])})
    return {"type": "FeatureCollection", "features": feats}, legend


@st.cache_data(show_spinner=False)
def gu_featurecollection(metric: str) -> tuple[dict, list]:
    """서울 전체 보기: 자치구 경계 + 자치구 요약 지표"""
    geo, gu = D.gu_geo(), D.gu_summary()
    df = geo.merge(gu, on="자치구")
    fills, legend = colorize(df[metric], C.GU_METRICS[metric][1], metric)
    feats = []
    for (_, r), fill in zip(df.iterrows(), fills):
        feats.append({"type": "Feature", "geometry": json.loads(r["geometry"]), "properties": {
            "자치구": r["자치구"], "_fill": fill, "행정동수": int(r["행정동수"]),
            "배율": f"×{r['배율_중앙값']:.2f}", "추세": f"{r['추세_중앙값_pct']:+.1f}%p/년",
            "선점": int(r["n_1"]), "유출보완": int(r["n_2"]), "최고기회동": r["최고기회동"] or "-",
            "대표원형": r["대표원형"], "_value": fmt_value(r[metric], metric)}})
    return {"type": "FeatureCollection", "features": feats}, legend


# ── 지도 조립 ────────────────────────────────────────────────────────────
def base_map(center=C.SEOUL_CENTER, zoom: int = 11) -> folium.Map:
    m = folium.Map(location=center, zoom_start=zoom, tiles=None, prefer_canvas=True, control_scale=True)
    folium.TileLayer(ESRI.format("World_Light_Gray_Base"), attr=ESRI_ATTR, name="회색 지도 (Esri)",
                     max_zoom=16).add_to(m)
    folium.TileLayer(OSM, attr=OSM_ATTR, name="일반 지도 (OpenStreetMap)", max_zoom=19, show=False).add_to(m)
    # 지명 라벨은 폴리곤보다 위 pane 에 올린다 (클릭은 통과)
    folium.map.CustomPane("labels", z_index=650, pointer_events=False).add_to(m)
    folium.TileLayer(ESRI.format("World_Light_Gray_Reference"), attr=ESRI_ATTR, name="지명 라벨",
                     overlay=True, control=True, max_zoom=16, pane="labels").add_to(m)
    return m


def _layer_control(m: folium.Map) -> None:
    folium.LayerControl(collapsed=True).add_to(m)


def _style(f):
    return {"fillColor": f["properties"]["_fill"], "color": "#ffffff", "weight": 1, "fillOpacity": 0.78}


def _highlight(_):
    return {"color": C.INK, "weight": 2.5, "fillOpacity": 0.9}


def add_legend(m: folium.Map, title: str, items: list[tuple[str, str]]) -> None:
    rows = "".join(f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0">'
                   f'<span style="width:14px;height:14px;background:{c};border-radius:3px;'
                   f'border:1px solid rgba(0,0,0,.1)"></span><span>{t}</span></div>' for c, t in items)
    html = f"""{{% macro html(this, kwargs) %}}
    <div style="position:absolute;bottom:24px;left:12px;z-index:9999;background:rgba(255,255,255,.94);
         padding:10px 12px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.2);
         font:12px 'Malgun Gothic',sans-serif;color:{C.INK2};max-width:220px">
      <div style="font-weight:700;color:{C.INK};margin-bottom:4px">{title}</div>{rows}</div>
    {{% endmacro %}}"""
    el = MacroElement()
    el._template = Template(html)
    m.get_root().add_child(el)


def seoul_map(metric: str, label: str) -> folium.Map:
    fc, legend = gu_featurecollection(metric)
    m = base_map()
    folium.GeoJson(fc, name="자치구", style_function=_style, highlight_function=_highlight,
                   tooltip=folium.GeoJsonTooltip(
                       fields=["자치구", "_value", "행정동수", "추세", "선점", "유출보완", "최고기회동", "대표원형"],
                       aliases=["자치구", label, "행정동 수", "추세 중앙값", "① 선점형", "② 유출보완형",
                                "최고 기회 동", "대표 원형"], sticky=True)).add_to(m)
    add_legend(m, label, legend)
    _layer_control(m)
    return m


def dong_map(gu: tuple[str, ...], metric: str, top_markers: pd.DataFrame | None = None) -> folium.Map:
    fc, legend = dong_featurecollection(gu, metric)
    label = C.MAP_METRICS[metric][0]
    m = base_map()
    layer = folium.GeoJson(fc, name="행정동", style_function=_style, highlight_function=_highlight,
                           tooltip=folium.GeoJsonTooltip(fields=TOOLTIP_DONG, aliases=[
                               a if a != "선택 지표" else label for a in TOOLTIP_DONG_ALIAS], sticky=True))
    layer.add_to(m)
    m.fit_bounds(layer.get_bounds())
    if top_markers is not None and len(top_markers):
        grp = folium.FeatureGroup(name="기회 Top 동")
        for _, r in top_markers.iterrows():
            folium.CircleMarker(
                (r["위도"], r["경도"]), radius=7, color="#ffffff", weight=2, fill=True,
                fill_color=C.INK, fill_opacity=0.9,
                tooltip=f"#{int(r['기회순위'])} {r['행정동_코드_명']} · {r['기회_유형']} · 점수 {r['기회점수']:.1f}",
            ).add_to(grp)
        grp.add_to(m)
    add_legend(m, label, legend)
    _layer_control(m)
    return m
