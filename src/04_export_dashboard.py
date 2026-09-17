# -*- coding: utf-8 -*-
"""
Step 4. 대시보드 데이터 내보내기

report/dashboard/data.js        ← 분석 결과 (window.DASH = {...})
report/dashboard/lib/plotly.min.js ← 파이썬 plotly 패키지에 포함된 JS를 복사 (오프라인 동작)
"""
import json, shutil
from pathlib import Path
import numpy as np, pandas as pd
import plotly

PJT = Path(__file__).resolve().parents[1]
DATA = PJT / "data"
OUT = PJT / "report" / "dashboard"
(OUT / "lib").mkdir(parents=True, exist_ok=True)

dong = pd.read_csv(DATA / "residual_행정동_요약.csv", encoding="utf-8-sig", dtype={"행정동_코드": str})
rq = pd.read_csv(DATA / "residual_행정동_분기.csv", encoding="utf-8-sig", dtype={"행정동_코드": str})
gu = pd.read_csv(DATA / "residual_자치구_요약.csv", encoding="utf-8-sig")
perf = pd.read_csv(DATA / "model_performance.csv", encoding="utf-8-sig")
imp = pd.read_csv(DATA / "feature_importance.csv", encoding="utf-8-sig")
summary = json.loads((DATA / "model_summary.json").read_text(encoding="utf-8"))

quarters = sorted(rq["분기라벨"].unique())
series = {}
for code, g in rq.sort_values("기준_년분기_코드").groupby("행정동_코드"):
    series[code] = {"a": (g["지출_총금액"] / 1e8).round(2).tolist(),     # 억 원
                    "e": (g["기대_지출"] / 1e8).round(2).tolist()}


def r(v, n=3):
    return None if pd.isna(v) else round(float(v), n)


dongs = [{
    "code": d["행정동_코드"], "name": d["행정동_코드_명"], "gu": d["자치구"],
    "actual": r(d["실제지출_분기평균"] / 1e8, 2), "expected": r(d["기대지출_분기평균"] / 1e8, 2),
    "resid": r(d["잔차_평균"]), "ratio": r(d["배율"]), "trend": r(d["잔차_추세"]),
    "resid_last": r(d["잔차_2025Q4"]), "type": d["유형"], "quad": d["사분면"],
    "flag": d["데이터점검"] if isinstance(d["데이터점검"], str) else "",
    "pop": r(d["상주인구"], 0), "work": r(d["직장인구"], 0), "flow": r(d["유동인구"], 0),
    "fac": r(d["집객시설"], 0), "subway": r(d["지하철역"], 0),
    "apt": r(d["아파트시가"] / 1e8 if pd.notna(d["아파트시가"]) else np.nan, 2),
    "lon": r(d["경도"], 5), "lat": r(d["위도"], 5),
} for _, d in dong.iterrows()]

gus = [{
    "name": g["자치구"], "n": int(g["행정동수"]), "actual": r(g["실제지출"] / 1e8, 1),
    "expected": r(g["기대지출"] / 1e8, 1), "resid": r(g["잔차_평균"]), "ratio": r(g["배율_평균"]),
    "over": int(g["초과달성"]), "normal": int(g["기대수준"]), "under": int(g["저평가"]),
    "flag": int(g["데이터점검"]), "rising": int(g["떠오르는잠재"]),
} for _, g in gu.iterrows()]

payload = {
    "quarters": quarters, "dongs": dongs, "gus": gus, "series": series,
    "perf": perf.round(4).to_dict("records"),
    "importance": imp.head(15).round(4)[["변수명", "중요도", "그룹"]].to_dict("records"),
    "summary": summary,
}
js = "window.DASH = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
(OUT / "data.js").write_text(js, encoding="utf-8")
print(f"data.js  {len(js) / 1024:,.0f} KB  (동 {len(dongs)}, 구 {len(gus)})")

src = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
shutil.copy(src, OUT / "lib" / "plotly.min.js")
print("plotly.min.js 복사:", src)
