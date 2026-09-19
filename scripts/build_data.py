# -*- coding: utf-8 -*-
"""
대시보드용 데이터 전처리: CSV + 행정동 경계 GeoJSON → Parquet

    python scripts/build_data.py            # 경계 파일이 없으면 자동 다운로드
    python scripts/build_data.py --offline  # data/cache 에 받아 둔 경계 파일만 사용

출력 (data/processed/)
  dong.parquet         행정동 425행 × 분석 컬럼 (+ 파생 컬럼)
  dong_geo.parquet     행정동 경계 (단순화 GeoJSON 문자열, 자치구별 조회용)
  gu_geo.parquet       자치구 경계 (행정동 경계 병합)
  gu_summary.parquet   자치구 요약 지표
  tags.parquet         키워드 태그 long 테이블 (행정동 × 축 × 태그)
  biz_gap.parquet      업종 공백·강점 long 테이블 (행정동 × 업종 × 배율)

경계 출처: vuski/admdongkor (행정안전부 행정동 경계, 인증키 불필요)
"""

import argparse
import json
import re
import urllib.request
from pathlib import Path

import polars as pl
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "서울시_행정동별_상권분석_통합.csv"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "processed"

GEO_VERSION = "ver20251231"
GEO_URL = (f"https://raw.githubusercontent.com/vuski/admdongkor/master/"
           f"{GEO_VERSION}/HangJeongDong_{GEO_VERSION}.geojson")

# 데이터(2025년 행정동 체계)와 경계(2025-12) 사이에 바뀐 동: 경계 코드 → 데이터 코드
CODE_REMAP = {
    "11680675": "11680740",  # 개포3동 ← 일원2동 (명칭 변경)
    "11740525": "11740520",  # 상일제1동 ┐ 상일동 분동 → 합쳐서 상일동
    "11740526": "11740520",  # 상일제2동 ┘
    "11230515": "11230536",  # 신설동   ┐ 용신동 분동 → 합쳐서 용신동
    "11230533": "11230536",  # 용두동   ┘
}
SIMPLIFY_TOL = 0.00015   # 약 15 m — 동 경계 모양은 유지하면서 용량을 1/10 수준으로
COORD_DIGITS = 5         # 소수 5자리 ≈ 1 m

OPP_CODE = {"① 선점형 기회": 1, "② 유출보완형 기회": 2, "③ 확장형": 3,
            "④ 검증·포화형": 4, "⑤ 경고(둔화)": 5, "⑥ 주의(위축)": 6, "데이터점검": 9}


def load_geojson(offline: bool) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"HangJeongDong_{GEO_VERSION}.geojson"
    if not path.exists():
        if offline:
            raise SystemExit(f"경계 파일 없음: {path}")
        print(f"download {GEO_URL}")
        urllib.request.urlretrieve(GEO_URL, path)
    return json.loads(path.read_text(encoding="utf-8"))


def round_coords(geom: dict) -> dict:
    def r(c):
        return [round(v, COORD_DIGITS) for v in c] if isinstance(c[0], float) else [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def geo_json_str(geom) -> str:
    return json.dumps(round_coords(mapping(geom.simplify(SIMPLIFY_TOL, preserve_topology=True))),
                      separators=(",", ":"))


def build_dong(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("행정동_코드").cast(pl.Utf8),
        pl.col("군집").cast(pl.Int8),
        pl.col("배율").log10().alias("log10_배율"),
        pl.col("기회_유형").replace_strict(OPP_CODE, default=9).cast(pl.Int8).alias("기회_코드"),
        (pl.col("격차금액_분기") / 1e8).alias("격차금액_억"),
        (pl.col("아파트_평균_시가") / 1e8).alias("아파트시가_억"),
        (pl.col("잔차_추세") * 100).alias("잔차_추세_pct"),
        pl.col("해석주의").is_not_null().alias("해석주의_여부"),
    )


def build_geo(dong: pl.DataFrame, gj: dict):
    shapes: dict[str, list] = {}
    for f in gj["features"]:
        p = f["properties"]
        if p["sido"] != "11":
            continue
        code = p["adm_cd2"][:8]
        code = CODE_REMAP.get(code, code)
        shapes.setdefault(code, []).append(shape(f["geometry"]))

    info = dong.select("행정동_코드", "자치구", "행정동_코드_명", "위도", "경도")
    missing = set(info["행정동_코드"]) - set(shapes)
    assert not missing, f"경계 없는 행정동: {missing}"

    rows, by_gu = [], {}
    for code, gu, name, lat, lon in info.iter_rows():
        g = unary_union(shapes[code]).buffer(0)
        by_gu.setdefault(gu, []).append(g)
        rows.append({"행정동_코드": code, "자치구": gu, "행정동_코드_명": name,
                     "위도": lat, "경도": lon, "geometry": geo_json_str(g)})
    dong_geo = pl.DataFrame(rows)

    gu_rows = []
    for gu, gs in by_gu.items():
        u = unary_union(gs)
        c = u.representative_point()
        gu_rows.append({"자치구": gu, "위도": c.y, "경도": c.x,
                        "geometry": geo_json_str(u.simplify(0.0005))})
    return dong_geo, pl.DataFrame(gu_rows)


def build_gu_summary(dong: pl.DataFrame) -> pl.DataFrame:
    ok = dong.filter(pl.col("기회_코드") != 9)
    best = (ok.filter(pl.col("기회순위").is_not_null())
              .sort("기회순위").group_by("자치구", maintain_order=True).first()
              .select("자치구", pl.col("행정동_코드_명").alias("최고기회동")))
    agg = ok.group_by("자치구").agg(
        pl.len().alias("행정동수"),
        pl.col("배율").median().alias("배율_중앙값"),
        pl.col("잔차_추세_pct").median().alias("추세_중앙값_pct"),
        pl.col("격차금액_억").sum().alias("격차금액_합_억"),
        pl.col("상주인구").sum().alias("상주인구_합"),
        pl.col("직장인구").sum().alias("직장인구_합"),
        pl.col("아파트시가_억").median().alias("아파트시가_중앙값_억"),
        pl.col("1인가구비율").median().alias("1인가구비율_중앙값"),
        *[(pl.col("기회_코드") == k).sum().alias(f"n_{k}") for k in range(1, 7)],
        pl.col("상권_원형").mode().first().alias("대표원형"),
        pl.col("금융MBTI").drop_nulls().mode().first().alias("대표MBTI"),
    )
    return agg.join(best, on="자치구", how="left").sort("자치구")


def build_tags(dong: pl.DataFrame) -> pl.DataFrame:
    axes = {"키워드_접근성인프라": "접근성·인프라", "키워드_소비배후수요": "소비·배후수요",
            "키워드_환경리스크": "환경·리스크"}
    frames = [dong.select("행정동_코드", "자치구", pl.col(c).str.split(" ").alias("태그"))
                  .explode("태그", empty_as_null=True).drop_nulls("태그").with_columns(pl.lit(ax).alias("축"))
              for c, ax in axes.items()]
    return pl.concat(frames).filter(pl.col("태그") != "")


def build_biz_gap(dong: pl.DataFrame) -> pl.DataFrame:
    pat = re.compile(r"([^,(]+)\(×([\d.]+)\)")
    rows = []
    for code, gu, arch, gap, strong in dong.select(
            "행정동_코드", "자치구", "상권_원형", "업종_공백", "업종_강점").iter_rows():
        for kind, text in (("공백", gap), ("강점", strong)):
            for name, v in pat.findall(text or ""):
                rows.append({"행정동_코드": code, "자치구": gu, "상권_원형": arch,
                             "구분": kind, "업종": name.strip(), "배율": float(v)})
    return pl.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    dong = build_dong(pl.read_csv(RAW, encoding="utf8-lossy", infer_schema_length=1000))
    dong_geo, gu_geo = build_geo(dong, load_geojson(args.offline))

    outputs = {
        "dong": dong, "dong_geo": dong_geo, "gu_geo": gu_geo,
        "gu_summary": build_gu_summary(dong), "tags": build_tags(dong), "biz_gap": build_biz_gap(dong),
    }
    for name, frame in outputs.items():
        path = OUT / f"{name}.parquet"
        frame.write_parquet(path, compression="zstd")
        print(f"{path.relative_to(ROOT)}  {frame.shape}  {path.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
