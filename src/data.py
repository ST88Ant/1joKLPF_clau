# -*- coding: utf-8 -*-
"""
데이터 접근 계층 — Parquet 을 DuckDB(SQL 필터·컬럼 선택)와 Polars(집계)로 읽는다.

- 페이지는 필요한 컬럼·자치구만 요청한다 → 전체 테이블을 매번 올리지 않는다.
- 결과는 st.cache_data 로 캐시한다 (같은 요청은 두 번째부터 즉시 반환).
"""

from __future__ import annotations

import duckdb
import pandas as pd
import polars as pl
import streamlit as st

from src import config as C


@st.cache_resource
def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for name, path in {"dong": C.P_DONG, "dong_geo": C.P_DONG_GEO, "gu_geo": C.P_GU_GEO,
                       "gu_summary": C.P_GU, "tags": C.P_TAGS, "biz_gap": C.P_GAP}.items():
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path.as_posix()}')")
    return con


def sql(query: str, params: list | None = None) -> pl.DataFrame:
    """DuckDB SQL → Polars. 파라미터 바인딩(?)으로 값만 넘긴다."""
    return _con().execute(query, params or []).pl()


def _cols(columns: tuple[str, ...] | None) -> str:
    return "*" if not columns else ", ".join(f'"{c}"' for c in columns)


@st.cache_data(show_spinner=False)
def dong(columns: tuple[str, ...] | None = None, gu: tuple[str, ...] | None = None) -> pd.DataFrame:
    """행정동 테이블. columns·gu 를 주면 그 부분만 읽는다 (DuckDB projection/filter pushdown)."""
    where = f"WHERE 자치구 IN ({', '.join('?' * len(gu))})" if gu else ""
    return sql(f"SELECT {_cols(columns)} FROM dong {where} ORDER BY 자치구, 행정동_코드",
               list(gu or [])).to_pandas()


@st.cache_data(show_spinner=False)
def gu_list() -> list[str]:
    return sql("SELECT DISTINCT 자치구 FROM dong ORDER BY 1")["자치구"].to_list()


@st.cache_data(show_spinner=False)
def dong_names(gu: str) -> pd.DataFrame:
    return sql("SELECT 행정동_코드, 행정동_코드_명 FROM dong WHERE 자치구 = ? ORDER BY 2", [gu]).to_pandas()


@st.cache_data(show_spinner=False)
def dong_one(code: str) -> dict:
    return sql("SELECT * FROM dong WHERE 행정동_코드 = ?", [code]).to_dicts()[0]


@st.cache_data(show_spinner=False)
def gu_summary() -> pd.DataFrame:
    return sql("SELECT * FROM gu_summary ORDER BY 자치구").to_pandas()


@st.cache_data(show_spinner="경계 불러오는 중…")
def dong_geo(gu: tuple[str, ...]) -> pd.DataFrame:
    """선택한 자치구의 행정동 경계만 읽는다."""
    return sql(f"SELECT * FROM dong_geo WHERE 자치구 IN ({', '.join('?' * len(gu))})",
               list(gu)).to_pandas()


@st.cache_data(show_spinner=False)
def gu_geo() -> pd.DataFrame:
    return sql("SELECT * FROM gu_geo").to_pandas()


@st.cache_data(show_spinner=False)
def tags(axis: str | None = None) -> pd.DataFrame:
    where, p = ("WHERE 축 = ?", [axis]) if axis else ("", [])
    return sql(f"SELECT * FROM tags {where}", p).to_pandas()


@st.cache_data(show_spinner=False)
def biz_gap() -> pd.DataFrame:
    return sql("SELECT * FROM biz_gap").to_pandas()


# ── Polars 집계 (lazy scan → 필요한 컬럼만 읽고 집계 후 수집) ─────────────
def _lf() -> pl.LazyFrame:
    return pl.scan_parquet(C.P_DONG)


@st.cache_data(show_spinner=False)
def crosstab(row: str, col: str, exclude_check: bool = True) -> pd.DataFrame:
    lf = _lf()
    if exclude_check:
        lf = lf.filter(pl.col("기회_유형") != "데이터점검")
    out = (lf.select(row, col).drop_nulls().group_by(row, col).len()
             .collect().pivot(on=col, index=row, values="len").fill_null(0))
    return out.to_pandas().set_index(row)


@st.cache_data(show_spinner=False)
def group_median(by: str, cols: tuple[str, ...]) -> pd.DataFrame:
    return (_lf().filter(pl.col(by).is_not_null())
              .group_by(by).agg(pl.len().alias("동 수"), *[pl.col(c).median() for c in cols])
              .sort("동 수", descending=True).collect().to_pandas())
