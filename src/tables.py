# -*- coding: utf-8 -*-
"""EDA 표 빌더 — 입력은 pandas DataFrame, 출력은 화면에 바로 쓸 DataFrame"""

from __future__ import annotations

import pandas as pd

from src import config as C

GROUPS = {
    "행정동 기준": ["자치구", "행정동_코드", "행정동_코드_명"],
    "금융MBTI": ["금융MBTI", "군집"],
    "상권 프로파일": ["대표_아파트_단지", "상권_유형", "상권_원형"],
    "정성 키워드": ["접근성_교통_키워드", "상권_장점_키워드", "상권_단점_리스크_키워드", "주요_배후수요_특성"],
    "키워드 태그": ["키워드_접근성인프라", "키워드_소비배후수요", "키워드_환경리스크"],
    "업종 인사이트": ["추천_유망_업종", "비추천_주의_업종", "타깃_업종", "업종_공백", "업종_강점", "상권_한줄평"],
    "상권 기회(모델)": ["유형", "사분면", "기회_유형", "기회점수", "기회순위", "배율", "격차금액_분기",
                    "잔차_추세", "기회_인사이트", "해석주의"],
    "정량 지표": ["상주인구", "직장인구", "직주비", "청년비율", "청년인구비율", "1인가구비율",
              "아파트_평균_시가", "아파트비중순위", "지하철역", "집객시설", "경도", "위도"],
}
DERIVED = ["log10_배율", "기회_코드", "격차금액_억", "아파트시가_억", "잔차_추세_pct", "해석주의_여부"]

MISSING_REASON = {
    "기회점수": "설계상 (①·②만 산정)", "기회순위": "설계상 (①·②만 산정)",
    "해석주의": "해당 없음 (정상 동)", "키워드_소비배후수요": "해당 태그 없음",
    "키워드_환경리스크": "해당 태그 없음", "업종_공백": "공백 업종 없음", "업종_강점": "강점 업종 없음",
    "아파트_평균_시가": "원천 결측 (둔촌1동)", "아파트비중순위": "원천 결측 (둔촌1동)",
}
# 그림 1 범례용 짧은 분류
MISSING_KIND = {"설계상": "설계상 빈 칸", "해당": "해당 없음", "공백": "해당 없음", "강점": "해당 없음",
                "원천": "원천 결측", "키워드": "키워드 파일에 없는 2개 동"}


def overview(df: pd.DataFrame) -> pd.DataFrame:
    raw = df.drop(columns=DERIVED, errors="ignore")
    return pd.DataFrame({
        "항목": ["행 (행정동)", "열 (원본 컬럼)", "자치구", "결측 셀", "결측 있는 컬럼",
               "기본키", "코드 중복", "동명 중복", "해석주의 동", "데이터점검 동"],
        "값": [f"{len(raw):,}", f"{raw.shape[1]}", f"{raw['자치구'].nunique()}",
              f"{int(raw.isna().sum().sum()):,} ({raw.isna().mean().mean():.1%})",
              f"{int((raw.isna().sum() > 0).sum())}", "행정동_코드",
              f"{int(raw['행정동_코드'].duplicated().sum())}",
              ", ".join(raw.loc[raw['행정동_코드_명'].duplicated(keep=False), '행정동_코드_명'].unique()) or "없음",
              f"{int(raw['해석주의'].notna().sum())}", f"{int((raw['기회_유형'] == '데이터점검').sum())}"],
    })


def column_dict(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for g, cols in GROUPS.items():
        for c in cols:
            s = df[c]
            ex = s.dropna()
            rows.append({"그룹": g, "컬럼": c, "타입": "수치" if pd.api.types.is_numeric_dtype(s) else "문자",
                         "결측": int(s.isna().sum()), "고유값": int(s.nunique()),
                         "예시": str(ex.iloc[0])[:40] if len(ex) else ""})
    return pd.DataFrame(rows)


def missing(df: pd.DataFrame) -> pd.DataFrame:
    raw = df.drop(columns=DERIVED, errors="ignore")
    n = raw.isna().sum()
    out = pd.DataFrame({"컬럼": n.index, "결측 수": n.values, "결측 비율": (n / len(raw)).values})
    two = set(raw.loc[raw["금융MBTI"].isna(), "행정동_코드_명"])
    out["원인"] = out["컬럼"].map(MISSING_REASON).fillna(
        f"키워드 파일에 없는 동 ({', '.join(sorted(two))})")
    out["분류"] = out["원인"].map(lambda r: next(v for k, v in MISSING_KIND.items() if r.startswith(k)))
    return out[out["결측 수"] > 0].sort_values("결측 수", ascending=False).reset_index(drop=True)


def describe(df: pd.DataFrame) -> pd.DataFrame:
    d = df[C.NUM_COLS].describe(percentiles=[.25, .5, .75]).T
    d["왜도"] = df[C.NUM_COLS].skew()
    d = d.rename(columns={"count": "개수", "mean": "평균", "std": "표준편차", "min": "최소",
                          "25%": "25%", "50%": "중앙값", "75%": "75%", "max": "최대"})
    d["로그 권장"] = d["왜도"].abs() >= 2
    return d.reset_index(names="컬럼")


def dist_with_median(df: pd.DataFrame, col: str, order: list[str]) -> pd.DataFrame:
    g = (df.dropna(subset=[col]).groupby(col)
           .agg(동수=("행정동_코드", "size"), 배율_중앙값=("배율", "median"),
                추세_중앙값=("잔차_추세_pct", "median"), 시가_중앙값_억=("아파트시가_억", "median"),
                청년인구비율=("청년인구비율", "median"), 일인가구비율=("1인가구비율", "median"))
           .reindex(order).dropna(how="all").reset_index())
    g["비율"] = g["동수"] / g["동수"].sum()
    return g.rename(columns={"일인가구비율": "1인가구비율", "추세_중앙값": "추세_중앙값(%p)"})


def opp_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("기회_유형").agg(동수=("행정동_코드", "size"), 배율_중앙값=("배율", "median"),
                                   추세_중앙값=("잔차_추세_pct", "median"), 점수_중앙값=("기회점수", "median"))
    g = g.reindex(C.OPP_ORDER + ["데이터점검"]).reset_index()
    g["의미"] = g["기회_유형"].map(C.OPP_DESC).fillna("집계 이상치 — 해석 제외")
    g["비율"] = g["동수"] / g["동수"].sum()
    return g.rename(columns={"추세_중앙값": "추세_중앙값(%p)"})


def top_pairs(df: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    cols = [c for c in C.CORR_COLS]
    corr = df[cols].corr(method="spearman")
    pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(cols) for b in cols[i + 1:]]
    out = pd.DataFrame(pairs, columns=["변수 A", "변수 B", "ρ"])
    out["|ρ|"] = out["ρ"].abs()
    out["강도"] = pd.cut(out["|ρ|"], [0, .3, .5, .7, 1], labels=["약함", "보통", "강함", "매우 강함"])
    return out.nlargest(n, "|ρ|").drop(columns="|ρ|").reset_index(drop=True)


def tag_top(t: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    g = t.groupby(["축", "태그"]).size().reset_index(name="동 수")
    g["순위"] = g.groupby("축")["동 수"].rank(ascending=False, method="first").astype(int)
    g = g[g["순위"] <= n].sort_values(["축", "순위"])
    return g.pivot(index="순위", columns="축", values="태그").join(
        g.pivot(index="순위", columns="축", values="동 수"), rsuffix=" (동)")


def gu_table(gu: pd.DataFrame) -> pd.DataFrame:
    out = gu.rename(columns={f"n_{k}": C.OPP_ORDER[k - 1][:2] for k in range(1, 7)})
    keep = ["자치구", "행정동수", "대표원형", "대표MBTI", "배율_중앙값", "추세_중앙값_pct",
            "아파트시가_중앙값_억", "1인가구비율_중앙값"] + [o[:2] for o in C.OPP_ORDER] + ["최고기회동"]
    return out[keep].sort_values("배율_중앙값", ascending=False).reset_index(drop=True)


def ranking(df: pd.DataFrame, opp: str, n: int = 10) -> pd.DataFrame:
    d = df[(df["기회_유형"] == opp) & df["해석주의"].isna()].nsmallest(n, "기회순위")
    return d[["기회순위", "자치구", "행정동_코드_명", "상권_원형", "배율", "격차금액_억",
              "업종_공백", "기회점수"]].reset_index(drop=True)


def caution(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["해석주의"].notna()].sort_values("배율", ascending=False)
    d = d.assign(구분=d["배율"].map(lambda v: "×5 이상" if v >= 5 else "×0.25 이하"))
    return d[["구분", "자치구", "행정동_코드_명", "배율", "격차금액_억", "기회_유형"]].reset_index(drop=True)
