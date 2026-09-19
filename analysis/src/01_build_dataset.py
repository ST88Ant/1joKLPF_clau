# -*- coding: utf-8 -*-
"""
Step 1. 분석용 데이터셋 구축 (행정동 425 × 분기 12 = 5,100행)

타깃 : 지출_총금액 (OA-22166, 소비가 '일어난 장소' 기준)
설명 : 인구(상주·직장·유동) + 인프라(집객시설·교통·아파트) + 면적 + 분기

원본(T_PJT2/data/raw, data/processed)은 읽기만 하고 수정하지 않는다.
결과는 Clau_pjt/data/ 에 저장한다.

상주인구 주의: 상권분석 상주인구는 재건축 지역에서 갱신이 늦다(둔촌1동 16명 vs SKT 22,127명).
→ 팀 패널(data/processed)의 SKT_총인구를 우선 쓰고, 결측일 때만 상권분석 값으로 채운다.
"""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from pyproj import Transformer

PJT = Path(__file__).resolve().parents[1]          # Clau_pjt
ROOT = PJT.parent                                  # T_PJT2
RAW = ROOT / "data" / "raw"
OUT = PJT / "data"
OUT.mkdir(exist_ok=True)

Q_FROM, Q_TO = 20231, 20254
KEY = ["기준_년분기_코드", "행정동_코드"]


def load(fname, cols):
    df = pd.read_csv(RAW / fname, encoding="utf-8-sig")
    df = df[df["기준_년분기_코드"].between(Q_FROM, Q_TO)]
    return df[KEY + cols]


# ------------------------------------------------------------------ 원본 로드
spend = load("OA-22166_소비_행정동.csv", ["행정동_코드_명", "지출_총금액"])

resid = load("OA-22183_상주인구_행정동.csv",
             ["총_상주인구_수", "연령대_20_상주인구_수", "연령대_30_상주인구_수",
              "총_가구_수", "아파트_가구_수"])

work = load("OA-22184_직장인구_행정동.csv", ["총_직장_인구_수"])

flow_cols = ["총_유동인구_수", "시간대_17_21_유동인구_수", "시간대_21_24_유동인구_수",
             "토요일_유동인구_수", "일요일_유동인구_수"]
flow = load("OA-22178_길단위인구_행정동.csv", flow_cols)

fac_cols = ["집객시설_수", "관공서_수", "은행_수", "종합병원_수", "일반_병원_수", "약국_수",
            "초등학교_수", "중학교_수", "고등학교_수", "대학교_수", "백화점_수", "슈퍼마켓_수",
            "극장_수", "숙박_시설_수", "철도_역_수", "지하철_역_수", "버스_정거장_수"]
fac = load("OA-22169_집객시설_행정동.csv", fac_cols)

apt = load("OA-22163_아파트_행정동.csv", ["아파트_단지_수", "아파트_평균_시가"])

area = pd.read_csv(RAW / "OA-22160_영역_행정동.csv", encoding="utf-8-sig")
area = area[["행정동_코드", "엑스좌표_값", "와이좌표_값", "영역_면적"]]

gu = pd.read_csv(RAW / "OA-22182_상주인구_자치구.csv", encoding="utf-8-sig",
                 dtype={"자치구_코드": str})
gu_map = dict(zip(gu["자치구_코드"], gu["자치구_코드_명"]))

# 팀 패널: SKT 총인구 (거주 인구의 최신 대리값)
panel = pd.read_csv(ROOT / "data" / "processed" / "panel_행정동_분기_2023_2025.csv",
                    encoding="utf-8-sig")
panel = panel.rename(columns={"분기": "기준_년분기_코드"})[KEY + ["SKT_총인구"]]

# ------------------------------------------------------------------ 결합
df = spend
for part in (resid, work, flow, fac, apt, panel):
    df = df.merge(part, on=KEY, how="left")
df = df.merge(area, on="행정동_코드", how="left")

# 원본 CSV는 가운뎃점(·)을 '?'로 저장한다 (예: 종로5?6가동)
df["행정동_코드_명"] = df["행정동_코드_명"].str.replace("?", "·", regex=False)
df["자치구_코드"] = df["행정동_코드"].astype(str).str[:5]
df["자치구"] = df["자치구_코드"].map(gu_map)
df["연도"] = df["기준_년분기_코드"] // 10
df["분기"] = df["기준_년분기_코드"] % 10
df["분기라벨"] = df["연도"].astype(str) + "Q" + df["분기"].astype(str)
df["시점"] = (df["연도"] - 2023) * 4 + df["분기"] - 1          # 0 … 11

# 시설 결측 = 해당 시설 없음
df[fac_cols] = df[fac_cols].fillna(0)
df["아파트_단지_수"] = df["아파트_단지_수"].fillna(0)
df["총_직장_인구_수"] = df["총_직장_인구_수"].fillna(0)

# 좌표 없는 동(원본 424개 vs 425동)은 같은 자치구 평균으로 대체 — 지도 표시용
for c in ["엑스좌표_값", "와이좌표_값"]:
    df[c] = df[c].fillna(df.groupby("자치구_코드")[c].transform("mean"))
df["영역_면적"] = df["영역_면적"].fillna(df["영역_면적"].median())
tr = Transformer.from_crs("EPSG:5181", "EPSG:4326", always_xy=True)
df["경도"], df["위도"] = tr.transform(df["엑스좌표_값"].values, df["와이좌표_값"].values)

# ------------------------------------------------------------------ 파생 변수
df["상주인구"] = df["SKT_총인구"].fillna(df["총_상주인구_수"])
df["청년비율"] = ((df["연령대_20_상주인구_수"] + df["연령대_30_상주인구_수"])
              / df["총_상주인구_수"].replace(0, np.nan)).fillna(0).clip(0, 1)
df["아파트가구비율"] = (df["아파트_가구_수"] / df["총_가구_수"].replace(0, np.nan)).fillna(0).clip(0, 1)
df["야간유동비율"] = ((df["시간대_17_21_유동인구_수"] + df["시간대_21_24_유동인구_수"])
                / df["총_유동인구_수"].replace(0, np.nan))
df["주말유동비율"] = ((df["토요일_유동인구_수"] + df["일요일_유동인구_수"])
                / df["총_유동인구_수"].replace(0, np.nan))
df["아파트시가_결측"] = df["아파트_평균_시가"].isna().astype(int)
df["병원_수"] = df["종합병원_수"] + df["일반_병원_수"]
df["학교_수"] = df["초등학교_수"] + df["중학교_수"] + df["고등학교_수"]

# 로그 변환 (극단값 완화: 소공동처럼 큰 동의 영향력을 줄임)
LOG = {"상주인구": "log_상주인구", "총_직장_인구_수": "log_직장인구",
       "총_유동인구_수": "log_유동인구", "집객시설_수": "log_집객시설",
       "버스_정거장_수": "log_버스정거장", "영역_면적": "log_면적",
       "아파트_가구_수": "log_아파트가구", "지출_총금액": "log_지출"}
for src, dst in LOG.items():
    df[dst] = np.log1p(df[src].clip(lower=0))
df["log_아파트시가"] = np.log(df["아파트_평균_시가"])       # 결측 유지 → 모델 단계에서 처리

df = df.sort_values(["자치구_코드", "행정동_코드", "기준_년분기_코드"]).reset_index(drop=True)
df.to_csv(OUT / "dataset_행정동_분기_2023_2025.csv", index=False, encoding="utf-8-sig")

print(f"저장: dataset_행정동_분기_2023_2025.csv  {df.shape}")
print(f"자치구 {df['자치구'].nunique()}개 / 행정동 {df['행정동_코드'].nunique()}개 / "
      f"분기 {df['기준_년분기_코드'].nunique()}개")
print("결측 확인:", df[["상주인구", "총_유동인구_수", "아파트_평균_시가", "자치구", "엑스좌표_값"]]
      .isna().sum().to_dict())
print(df[["지출_총금액", "상주인구", "총_직장_인구_수", "총_유동인구_수", "집객시설_수"]]
      .describe().T[["mean", "50%", "max"]].to_string(float_format=lambda x: f"{x:,.0f}"))
