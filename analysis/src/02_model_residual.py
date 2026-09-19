# -*- coding: utf-8 -*-
"""
Step 2. 기대 소비 예측 모델 + 잔차(갭) 분석

- 타깃: log(지출_총금액)  → 잔차 = log(실제) − log(기대)
  잔차 0.69 = 기대의 2배, −0.69 = 기대의 절반.  배율 = exp(잔차)
- 검증: GroupKFold(행정동). 한 동의 12분기가 학습/검증에 동시에 들어가지 않게 한다.
  (같은 동을 학습하면 모델이 그 동의 '고유 효과'까지 외워 잔차가 사라진다.)
- 모든 잔차는 out-of-fold 예측, 즉 '그 동을 보지 못한 모델'의 기대값 기준이다.
"""
import json, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, mean_absolute_error

PJT = Path(__file__).resolve().parents[1]
DATA = PJT / "data"
df = pd.read_csv(DATA / "dataset_행정동_분기_2023_2025.csv", encoding="utf-8-sig")

FEATURES = {
    # 인구
    "log_상주인구": "상주인구(log)", "log_직장인구": "직장인구(log)", "log_유동인구": "유동인구(log)",
    "청년비율": "20·30대 비율", "야간유동비율": "야간 유동 비율", "주말유동비율": "주말 유동 비율",
    # 인프라
    "log_집객시설": "집객시설 수(log)", "지하철_역_수": "지하철역 수", "철도_역_수": "철도역 수",
    "log_버스정거장": "버스정거장(log)", "백화점_수": "백화점 수", "대학교_수": "대학교 수",
    "숙박_시설_수": "숙박시설 수", "극장_수": "극장 수", "병원_수": "병원 수", "은행_수": "은행 수",
    "관공서_수": "관공서 수", "학교_수": "초중고 수", "슈퍼마켓_수": "슈퍼마켓 수",
    # 주거
    "아파트_단지_수": "아파트 단지 수", "log_아파트가구": "아파트 가구(log)",
    "아파트가구비율": "아파트 가구 비율", "log_아파트시가": "아파트 평균시가(log)",
    "아파트시가_결측": "아파트시가 없음",
    # 공간·시간
    "log_면적": "면적(log)", "시점": "시점(분기)", "분기": "계절(분기)",
}
X = df[list(FEATURES)]
y = df["log_지출"].values
groups = df["행정동_코드"].values

# ------------------------------------------------------------------ 데이터 점검 플래그
# ① 분기 간 log 지출 변화 > 1.4 (약 4배 급변): 아현동↓(2025Q1)·문래동↑(2024Q4)이 맞물려
#    대형 가맹점 소재지 이전 등 집계 기준 변화로 추정 → 동 전체를 학습에서 제외
# ② 분기 지출 1억 미만: 재건축 공실(둔촌1동)
# 제외된 동도 예측·잔차는 계산하고 '데이터점검' 표시만 붙인다.
jump = df.groupby("행정동_코드")["log_지출"].transform(lambda s: s.diff().abs().max())
tiny = df.groupby("행정동_코드")["지출_총금액"].transform("min") < 1e8
df["데이터점검"] = np.select([jump > 1.4, tiny], ["지출 급변(집계 기준 변화 의심)", "지출 거의 없음(재건축 등)"], "")
train_ok = (df["데이터점검"] == "").values
print("학습 제외 동:", df.loc[~train_ok, "행정동_코드_명"].unique().tolist())

MODELS = {
    "선형회귀(Ridge)": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  RidgeCV(alphas=np.logspace(-2, 3, 20))),
    "랜덤포레스트": make_pipeline(SimpleImputer(strategy="median"),
                            RandomForestRegressor(n_estimators=400, min_samples_leaf=3,
                                                  max_features=0.5, n_jobs=-1, random_state=42)),
    "그래디언트부스팅": HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05,
                                                 max_leaf_nodes=31, min_samples_leaf=20,
                                                 l2_regularization=1.0, random_state=42),
}

gkf = GroupKFold(n_splits=5)
folds = list(gkf.split(X, y, groups))
oof = {name: np.zeros(len(y)) for name in MODELS}
perf = []
for name, model in MODELS.items():
    fold_r2 = []
    for tr, te in folds:
        tr = tr[train_ok[tr]]
        model.fit(X.iloc[tr], y[tr])
        oof[name][te] = model.predict(X.iloc[te])
        fold_r2.append(r2_score(y[te][train_ok[te]], oof[name][te][train_ok[te]]))
    ok = train_ok   # 성능은 정상 동 기준
    perf.append({"모델": name, "R2": r2_score(y[ok], oof[name][ok]),
                 "R2_std": float(np.std(fold_r2)),
                 "MAE_log": mean_absolute_error(y[ok], oof[name][ok]),
                 # MAE 0.5 → 평균적으로 exp(0.5)=1.65배 수준 오차
                 "평균오차배율": float(np.exp(mean_absolute_error(y[ok], oof[name][ok])))})
    print(f"{name:12s} R²={perf[-1]['R2']:.3f} (±{perf[-1]['R2_std']:.3f})  MAE(log)={perf[-1]['MAE_log']:.3f}")

perf = pd.DataFrame(perf).sort_values("R2", ascending=False)
best = perf.iloc[0]["모델"]
print(f"\n선택 모델: {best}")
perf.to_csv(DATA / "model_performance.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 변수 중요도
# 전체 데이터로 재학습 후 permutation importance (R² 하락폭)
final = MODELS[best].fit(X[train_ok], y[train_ok])
pi = permutation_importance(final, X[train_ok], y[train_ok], n_repeats=5, random_state=42, n_jobs=-1)
imp = (pd.DataFrame({"변수": list(FEATURES), "변수명": list(FEATURES.values()),
                     "중요도": pi.importances_mean, "표준편차": pi.importances_std})
       .sort_values("중요도", ascending=False))
imp["그룹"] = imp["변수"].map(lambda v: "인구" if v in list(FEATURES)[:6]
                           else "인프라" if v in list(FEATURES)[6:19]
                           else "주거" if v in list(FEATURES)[19:24] else "공간·시간")
imp.to_csv(DATA / "feature_importance.csv", index=False, encoding="utf-8-sig")

# 선형모델 계수 (해석용: 표준화 1단위 증가 시 log 지출 변화)
ridge = MODELS["선형회귀(Ridge)"].fit(X[train_ok], y[train_ok])
coef = (pd.DataFrame({"변수": list(FEATURES), "변수명": list(FEATURES.values()),
                      "계수": ridge[-1].coef_}).sort_values("계수", key=abs, ascending=False))
coef.to_csv(DATA / "ridge_coefficients.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 잔차 (분기 단위)
df["log_기대지출"] = oof[best]
df["기대_지출"] = np.expm1(df["log_기대지출"])
df["잔차"] = df["log_지출"] - df["log_기대지출"]
df["배율"] = np.exp(df["잔차"])
for name in MODELS:
    df[f"oof_{name}"] = oof[name]
qcols = ["기준_년분기_코드", "분기라벨", "시점", "자치구", "자치구_코드", "행정동_코드", "행정동_코드_명",
         "지출_총금액", "기대_지출", "log_지출", "log_기대지출", "잔차", "배율", "데이터점검"] + [f"oof_{n}" for n in MODELS]
df[qcols].to_csv(DATA / "residual_행정동_분기.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 동 단위 요약
def slope(g):
    return np.polyfit(g["시점"], g["잔차"], 1)[0] * 4       # 연간 잔차 변화

agg = df.groupby(["자치구", "자치구_코드", "행정동_코드", "행정동_코드_명"]).agg(
    실제지출_분기평균=("지출_총금액", "mean"), 기대지출_분기평균=("기대_지출", "mean"),
    잔차_평균=("잔차", "mean"), 잔차_표준편차=("잔차", "std"),
    상주인구=("상주인구", "mean"), 직장인구=("총_직장_인구_수", "mean"),
    유동인구=("총_유동인구_수", "mean"), 집객시설=("집객시설_수", "mean"),
    지하철역=("지하철_역_수", "max"), 아파트시가=("아파트_평균_시가", "mean"),
    경도=("경도", "first"), 위도=("위도", "first"),
    x=("엑스좌표_값", "first"), y=("와이좌표_값", "first"), 데이터점검=("데이터점검", "first"),
).reset_index()
agg["잔차_추세"] = df.groupby("행정동_코드").apply(slope).reindex(agg["행정동_코드"]).values
last = df[df["기준_년분기_코드"] == 20254].set_index("행정동_코드")
agg["잔차_2025Q4"] = last.loc[agg["행정동_코드"], "잔차"].values
agg["실제지출_2025Q4"] = last.loc[agg["행정동_코드"], "지출_총금액"].values
agg["기대지출_2025Q4"] = last.loc[agg["행정동_코드"], "기대_지출"].values
agg["배율"] = np.exp(agg["잔차_평균"])
agg["격차금액_분기"] = agg["실제지출_분기평균"] - agg["기대지출_분기평균"]

# 유형: 기대 대비 1.5배 이상 = 초과, 2/3배 이하 = 저평가
UP, DN = np.log(1.5), np.log(2 / 3)
agg["유형"] = np.select([agg["잔차_평균"] >= UP, agg["잔차_평균"] <= DN],
                       ["초과달성", "저평가"], "기대수준")
# 사분면: 수준(잔차 평균) × 방향(잔차 추세). 추세 임계 ±0.05/년 이내는 '안정'
T = 0.05
def quad(r):
    lvl = "저평가" if r["잔차_평균"] < 0 else "초과"
    if r["잔차_추세"] > T:
        return "떠오르는 잠재상권" if lvl == "저평가" else "성장하는 강세상권"
    if r["잔차_추세"] < -T:
        return "위축되는 약세상권" if lvl == "저평가" else "식어가는 강세상권"
    return "안정(" + lvl + ")"
agg["사분면"] = agg.apply(quad, axis=1)
flag = agg["데이터점검"] != ""
agg.loc[flag, ["유형", "사분면"]] = "데이터점검"
agg["잠재순위"] = agg["잔차_평균"].where(~flag).rank(method="first")    # 1 = 가장 저평가 (점검 동 제외)
agg = agg.sort_values(["자치구_코드", "잔차_평균"]).reset_index(drop=True)
agg.to_csv(DATA / "residual_행정동_요약.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 자치구 요약
gu = agg.groupby(["자치구", "자치구_코드"]).agg(
    행정동수=("행정동_코드", "count"), 실제지출=("실제지출_분기평균", "sum"),
    기대지출=("기대지출_분기평균", "sum"), 잔차_평균=("잔차_평균", "mean"),
    초과달성=("유형", lambda s: (s == "초과달성").sum()),
    기대수준=("유형", lambda s: (s == "기대수준").sum()),
    저평가=("유형", lambda s: (s == "저평가").sum()),
    데이터점검=("유형", lambda s: (s == "데이터점검").sum()),
    떠오르는잠재=("사분면", lambda s: (s == "떠오르는 잠재상권").sum()),
).reset_index()
gu["배율_평균"] = np.exp(gu["잔차_평균"])
gu = gu.sort_values("잔차_평균", ascending=False)
gu.to_csv(DATA / "residual_자치구_요약.csv", index=False, encoding="utf-8-sig")

summary = {
    "best_model": best,
    "performance": perf.to_dict("records"),
    "n_dong": int(agg.shape[0]), "n_gu": int(gu.shape[0]), "n_rows": int(df.shape[0]),
    "type_counts": agg["유형"].value_counts().to_dict(),
    "quad_counts": agg["사분면"].value_counts().to_dict(),
}
(DATA / "model_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n유형:", summary["type_counts"])
print("사분면:", summary["quad_counts"])
print("\n변수 중요도 Top10\n", imp.head(10)[["변수명", "중요도"]].to_string(index=False))
cols = ["자치구", "행정동_코드_명", "배율", "잔차_추세", "실제지출_분기평균", "기대지출_분기평균"]
ok = agg[agg["유형"] != "데이터점검"]
print("\n초과달성 Top10\n", ok.nlargest(10, "잔차_평균")[cols].to_string(index=False))
print("\n저평가 Top10\n", ok.nsmallest(10, "잔차_평균")[cols].to_string(index=False))
print("\n자치구\n", gu[["자치구", "배율_평균", "초과달성", "기대수준", "저평가", "떠오르는잠재"]].to_string(index=False))
