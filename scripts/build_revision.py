# -*- coding: utf-8 -*-
"""
[수정사항] 페이지용 검증 데이터 만들기

원본(T_PJT2/data/raw, Clau_pjt/data/*.csv)을 읽어 페이지가 바로 쓸 수 있는 두 파일로 굽는다.
저장소에 원본 전체를 넣지 않기 위해, 필요한 값만 추려 낸다.
입력(원본 CSV·모델 산출 CSV)은 저장소에 없다. 출력 2개만 커밋해 두었으므로 페이지는 그대로 돌아간다.

    python scripts/build_revision.py

출력
    data/processed/revision.parquet    행정동 425행 — 항목 구성·1인당 지출·잔차 통계
    data/processed/revision_stats.json 스칼라·소형 표 (모델 성능·변수 중요도·순위 Top)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PJT = Path(__file__).resolve().parents[1]      # Clau_pjt
ROOT = PJT.parent                              # T_PJT2
RAW = ROOT / "data" / "raw"
OUT = PJT / "data" / "processed"

Q = 20254                                      # 모델 학습 구간의 마지막 분기
CATS = ["여가_문화", "기타", "교통", "음식", "식료품", "의료비", "교육", "의류_신발", "유흥", "생활용품"]


def main() -> None:
    # ── 타깃 원본 (소비) ────────────────────────────────────────────────
    sp = pd.read_csv(RAW / "OA-22166_소비_행정동.csv", encoding="utf-8-sig")
    q = sp[sp["기준_년분기_코드"] == Q].copy()
    q["행정동_코드_명"] = q["행정동_코드_명"].str.replace("?", "·", regex=False)

    total = q["지출_총금액"].sum()
    cat_share = {c: float(q[f"{c}_지출_총금액"].sum() / total * 100) for c in CATS}
    q["여가비중"] = q["여가_문화_지출_총금액"] / q["지출_총금액"]
    q["지출_비중"] = q["지출_총금액"] / total * 100

    s = np.sort(q["지출_총금액"].values)[::-1]
    cum = np.cumsum(s) / s.sum() * 100

    # ── 상주인구 (1인당 지출 검증용) ────────────────────────────────────
    rs = pd.read_csv(RAW / "OA-22183_상주인구_행정동.csv", encoding="utf-8-sig")
    pop = rs[rs["기준_년분기_코드"] == Q][["행정동_코드", "총_상주인구_수", "총_가구_수", "아파트_가구_수"]]

    # ── 잔차 (모델 산출물) ──────────────────────────────────────────────
    res = pd.read_csv(PJT / "data" / "residual_행정동_요약.csv", encoding="utf-8-sig")

    dong = (q[["행정동_코드", "행정동_코드_명", "지출_총금액", "지출_비중", "여가비중"]]
            .merge(pop, on="행정동_코드", how="left")
            .merge(res[["행정동_코드", "자치구", "잔차_평균", "잔차_표준편차", "잔차_추세",
                        "배율", "실제지출_분기평균", "기대지출_분기평균", "유형", "데이터점검"]],
                   on="행정동_코드", how="inner"))
    dong["1인당_분기지출_만원"] = dong["지출_총금액"] / dong["총_상주인구_수"] / 1e4
    dong.to_parquet(OUT / "revision.parquet", index=False)

    # ── 스칼라·소형 표 ──────────────────────────────────────────────────
    perf = pd.read_csv(PJT / "data" / "model_performance.csv", encoding="utf-8-sig")
    imp = pd.read_csv(PJT / "data" / "feature_importance.csv", encoding="utf-8-sig")
    coef = pd.read_csv(PJT / "data" / "ridge_coefficients.csv", encoding="utf-8-sig")
    opp = pd.read_csv(PJT / "data" / "서울시_행정동별_상권기회_인사이트.csv", encoding="utf-8-sig")

    res["데이터점검"] = res["데이터점검"].fillna("")
    ok = res[res["데이터점검"] == ""]
    stats = {
        "분기": Q,
        "분기라벨": f"{Q // 10}Q{Q % 10}",
        "항목구성비": cat_share,
        "집중도": {str(k): float(cum[k - 1]) for k in (1, 3, 5, 10, 25, 50, 100)},
        "1인당지출_분위": {str(int(p * 100)): float(dong["1인당_분기지출_만원"].quantile(p))
                       for p in (0.1, 0.25, 0.5, 0.75, 0.9)},
        "1인당지출_최대": float(dong["1인당_분기지출_만원"].max()),
        "아파트가구_합": int(rs["아파트_가구_수"].sum()),
        "신호_동간표준편차": float(ok["잔차_평균"].std()),
        "잡음_동내표준편차_중앙값": float(ok["잔차_표준편차"].median()),
        "실제합_대_기대합": float(res["실제지출_분기평균"].sum() / res["기대지출_분기평균"].sum()),
        "격차합_조": float(res["격차금액_분기"].sum() / 1e12),
        "상관_수준_추세": float(np.corrcoef(ok["잔차_평균"], ok["잔차_추세"])[0, 1]),
        "상관_수준_규모": float(np.corrcoef(ok["잔차_평균"], np.log1p(ok["실제지출_분기평균"]))[0, 1]),
        "성능": perf.to_dict("records"),
        "중요도": imp.head(12)[["변수명", "중요도", "그룹"]].to_dict("records"),
        "계수": coef.head(10)[["변수명", "계수"]].to_dict("records"),
        "기회Top10": (opp[opp["기회순위"] <= 10].sort_values("기회순위")
                    [["자치구", "행정동_코드_명", "기회_유형", "기회점수", "배율", "상주인구"]]
                    .to_dict("records")),
        "저평가Top10": (ok.nsmallest(10, "잔차_평균")[["자치구", "행정동_코드_명", "배율", "실제지출_분기평균"]]
                     .to_dict("records")),
        "초과Top10": (ok.nlargest(10, "잔차_평균")[["자치구", "행정동_코드_명", "배율", "잔차_추세"]]
                    .to_dict("records")),
    }
    (OUT / "revision_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print("revision.parquet", dong.shape)
    print("여가·문화 비중 %.1f%% · 상위3동 %.1f%% · 1인당 중앙 %.1f만원"
          % (cat_share["여가_문화"], cum[2], dong["1인당_분기지출_만원"].median()))


if __name__ == "__main__":
    main()
