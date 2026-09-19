# -*- coding: utf-8 -*-
"""
서울시 행정동별 '키워드 분류 × 타깃 업종 × 상권 기회' 인사이트 데이터셋

입력
  - T_PJT2/data/processed/서울시_행정동별_상권분석_키워드.csv   (apt.wiki 정성 키워드, 423동)
  - data/residual_행정동_요약.csv, data/dataset_행정동_분기_2023_2025.csv   (02 실행 결과)
  - T_PJT2/data/raw/OA-22166_소비_행정동.csv (업종별 지출), OA-22163_아파트_행정동.csv

출력
  - data/서울시_행정동별_상권기회_인사이트.csv
  - data/서울시_자치구별_상권기회_요약.csv

핵심 아이디어
  1) 키워드 3축 분류: 접근성·인프라 / 소비·배후수요 / 환경·리스크
     - 수치 피처(분위수 기준) + 기존 정성 키워드 텍스트(정규식) 두 소스를 합친다.
  2) 상권 원형(archetype): 직장/상주 비율, 청년비율, 아파트 비중·시가, 집객시설로 규칙 분류
  3) 업종 공백: 업종별 지출 '비중'을 같은 원형 동들의 중앙값과 비교
     → 비중이 낮은 업종 = 동네 수요가 밖으로 새는(공급이 부족한) 업종 = 진입 후보
  4) 기회 유형: 모델 잔차 수준 × 추세 사분면을 창업 관점 언어로 번역하고 기회점수로 순위화
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

PJT = Path(__file__).resolve().parents[1]          # Clau_pjt
ROOT = PJT.parent                                  # T_PJT2
DATA = PJT / "data"
RAW = ROOT / "data" / "raw"
KW = ROOT / "data" / "processed" / "서울시_행정동별_상권분석_키워드.csv"
RES = DATA / "residual_행정동_요약.csv"
FEAT = DATA / "dataset_행정동_분기_2023_2025.csv"
SPEND = RAW / "OA-22166_소비_행정동.csv"
APT = RAW / "OA-22163_아파트_행정동.csv"
OUT_DONG = DATA / "서울시_행정동별_상권기회_인사이트.csv"
OUT_GU = DATA / "서울시_자치구별_상권기회_요약.csv"

# 업종 지출 카테고리 → 창업 업종 번역 (교통·기타는 창업 업종으로 번역이 어려워 제외)
CAT_TO_BIZ = {
    "음식": "음식점·카페·배달전문점",
    "식료품": "식자재마트·정육·반찬가게",
    "의료비": "의원(내과·소아과·치과)·약국",
    "교육": "학원·스터디카페·키즈교육",
    "여가_문화": "피트니스·필라테스·키즈카페·공방",
    "생활용품": "생활용품·무인점포·세탁",
    "의류_신발": "의류·잡화 편집숍",
    "유흥": "주점·이자카야·노래방",
}
CATS = list(CAT_TO_BIZ)

# 원형별로 권하지 않는 업종 카테고리 (공백이 있어도 추천에서 제외)
ARCHETYPE_EXCLUDE = {
    "학원가·에듀형": {"유흥"},
    "고자산·아파트형": {"유흥"},
    "가족·아파트단지형": {"유흥"},
}

# 현장 키워드의 '비추천_주의_업종'에 걸리면 데이터 공백이 있어도 추천하지 않음
CAUTION_MAP = {
    "유흥": r"유흥|주점|술집|노래",
    "교육": r"학원|교육",
    "의류_신발": r"의류|패션",
}

# 기존 정성 키워드 텍스트 → 태그 (축, 정규식, 태그)
TEXT_RULES = [
    ("접근", r"환승", "#환승요충지"),
    ("접근", r"언덕|경사|고지대", "#언덕지형"),
    ("접근", r"주차", "#주차난"),
    ("접근", r"한강", "#한강변"),
    ("접근", r"몰세권|백화점|아울렛|복합몰|더현대|롯데월드|코엑스|타임스퀘어|디큐브", "#몰세권"),
    ("접근", r"숲세권|공원|녹지|산책|천변|하천", "#공원·숲세권"),
    ("접근", r"GTX|신안산선|경전철|개통|연장", "#교통호재"),
    ("수요", r"학원가|학군|에듀", "#학원가·학군"),
    ("수요", r"외국인|관광", "#관광·외국인"),
    ("수요", r"대학가|대학교|캠퍼스", "#대학가"),
    ("수요", r"고령|어르신|노년", "#고령층"),
    ("수요", r"신혼|맞벌이", "#3040맞벌이"),
    ("수요", r"입주|신축", "#신축입주"),
    ("리스크", r"공실", "#상가공실"),
    ("리스크", r"유흥|취객", "#유흥가소음"),
    ("리스크", r"정체|혼잡|마비", "#교통정체"),
    ("리스크", r"노후|낙후|슬럼", "#노후상권"),
    ("리스크", r"임대료|권리금|분양가", "#고임대료"),
    ("리스크", r"재건축|재개발|공사|이주", "#정비사업·공사"),
    ("리스크", r"공단|준공업|공장|철공", "#공업지대혼재"),
    ("리스크", r"공동화", "#주말공동화"),
    ("리스크", r"과열|경쟁|포화", "#경쟁과열"),
    ("리스크", r"외부 유입 한계|의존도", "#외부유입한계"),
    ("리스크", r"유출", "#소비유출"),
]


def load():
    kw = pd.read_csv(KW)
    res = pd.read_csv(RES)
    feat = pd.read_csv(FEAT)
    spend = pd.read_csv(SPEND, encoding="utf-8-sig")
    return kw, res, feat, spend


def build_features(feat):
    """2025년 4개 분기 평균으로 동 단위 프로필을 만든다."""
    f = feat[feat["연도"] == 2025]
    num = ["총_상주인구_수", "연령대_20_상주인구_수", "연령대_30_상주인구_수", "총_가구_수",
           "아파트_가구_수", "총_직장_인구_수", "총_유동인구_수", "야간유동비율", "주말유동비율",
           "집객시설_수", "지하철_역_수", "버스_정거장_수", "백화점_수", "대학교_수", "종합병원_수",
           "초등학교_수", "중학교_수", "고등학교_수", "아파트_평균_시가"]
    p = f.groupby("행정동_코드")[num].mean()
    p["직주비"] = p["총_직장_인구_수"] / p["총_상주인구_수"].clip(lower=1)
    p["청년비율"] = (p["연령대_20_상주인구_수"] + p["연령대_30_상주인구_수"]) / p["총_상주인구_수"].clip(lower=1)
    # 원천의 아파트_가구_수가 전 기간 0이라, OA-22163(아파트)의 면적대별 세대 합으로 대체한다.
    # OA-22163은 일부 단지만 집계돼 절대 비율은 과소 → 서울 내 상대 순위(0~1)로만 쓴다.
    apt = pd.read_csv(APT, encoding="utf-8-sig")
    apt = apt[apt["기준_년분기_코드"] // 10 == 2025]
    apt_cols = [c for c in apt.columns if "면적" in c and c.endswith("세대_수")]
    apt_hh = apt.assign(세대=apt[apt_cols].sum(axis=1)).groupby("행정동_코드")["세대"].mean()
    p["아파트세대"] = apt_hh.reindex(p.index)
    p["아파트비중순위"] = (p["아파트세대"] / p["총_가구_수"].clip(lower=1)).rank(pct=True)
    p["배후인구"] = p["총_상주인구_수"] + p["총_직장_인구_수"]
    return p


def build_category_share(spend):
    """2025년 업종별 지출 비중."""
    s = spend[spend["기준_년분기_코드"] // 10 == 2025].groupby("행정동_코드").sum(numeric_only=True)
    cols = {c: f"{c}_지출_총금액" for c in CATS}
    total = s[list(cols.values())].sum(axis=1).replace(0, np.nan)
    share = pd.DataFrame({c: s[col] / total for c, col in cols.items()})
    return share


def pct(s):
    return s.rank(pct=True)


def archetype(r, q):
    if r["share_교육"] >= q["교육90"]:
        return "학원가·에듀형"
    if r["직주비"] >= 2.0:
        return "오피스·업무형"
    if r["집객시설_수"] >= q["집객90"] and r["주말유동비율"] >= q["주말60"]:
        return "광역집객·관광형"
    if r["아파트_평균_시가"] >= q["시가90"]:
        return "고자산·아파트형"
    if r["청년비율"] >= q["청년75"] and r["아파트비중순위"] < 0.5:
        return "청년1인·원룸형"
    if r["아파트비중순위"] >= 0.7:
        return "가족·아파트단지형"
    if r["직주비"] >= q["직주85"]:
        return "직주혼합형"
    return "근린주거형"


def data_tags(r, q):
    acc, dem, risk = [], [], []
    # 접근성·인프라
    if r["지하철_역_수"] >= 2:
        acc.append("#다중역세권")
    elif r["지하철_역_수"] >= 1:
        acc.append("#역세권")
    else:
        acc.append("#역세권공백")
    if r["집객시설_수"] >= q["집객80"]:
        acc.append("#집객시설밀집")
    if r["백화점_수"] >= 1:
        acc.append("#몰세권")
    if r["종합병원_수"] >= 1:
        acc.append("#의료허브")
    if r["대학교_수"] >= 10:  # 대학 건물 수 기준(1~9는 단과 시설·분교 수준이 많음)
        acc.append("#대학가")
    # 소비·배후수요
    if r["아파트_평균_시가"] >= q["시가90"]:
        dem.append("#초고자산")
    elif r["아파트_평균_시가"] <= q["시가25"]:
        dem.append("#가성비선호")
    if r["청년비율"] >= q["청년75"]:
        dem.append("#2030청년가구")
    if r["직주비"] >= q["직주85"]:
        dem.append("#직장인밀집")
    if r["아파트비중순위"] >= 0.7 and r["청년비율"] < q["청년50"]:
        dem.append("#가족세대")
    if r["야간유동비율"] >= q["야간80"]:
        dem.append("#야간소비")
    if r["주말유동비율"] >= q["주말80"]:
        dem.append("#주말나들이")
    # 환경·리스크 (모델 결과 기반)
    if r["주말유동비율"] <= q["주말15"] and r["직주비"] >= q["직주85"]:
        risk.append("#주말공동화")
    if r["유형"] == "저평가":
        risk.append("#소비유출")
    if r["잔차_추세"] <= -0.05:
        risk.append("#소비위축추세")
    if r["유형"] == "초과달성":
        risk.append("#경쟁과열가능")
    return acc, dem, risk


def text_tags(r):
    txt = lambda cols: " ".join(str(r.get(c, "")) for c in cols)
    src = {
        "접근": txt(["상권_유형", "접근성_교통_키워드", "상권_장점_키워드", "상권_단점_리스크_키워드"]),
        "수요": txt(["상권_유형", "상권_장점_키워드", "주요_배후수요_특성"]),
        "리스크": txt(["상권_단점_리스크_키워드"]),
    }
    out = {"접근": [], "수요": [], "리스크": []}
    for axis, pat, tag in TEXT_RULES:
        if re.search(pat, src[axis]):
            out[axis].append(tag)
    return out


def merge_tags(*lists):
    seen, out = set(), []
    for lst in lists:
        for t in lst:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return " ".join(out)


# 잔차 사분면 → 창업 관점 기회 유형
OPP = {
    "떠오르는 잠재상권": ("① 선점형 기회", "기대보다 덜 쓰지만 격차가 줄어드는 중 — 임대료 오르기 전 진입 적기"),
    "안정(저평가)": ("② 유출보완형 기회", "수요 대비 소비가 꾸준히 밖으로 샘 — 빠진 필수업종을 채우는 근린형 진입"),
    "성장하는 강세상권": ("③ 확장형", "이미 강하고 더 커지는 중 — 핵심가 대신 2선 입지·배후 골목 공략"),
    "안정(초과)": ("④ 검증·포화형", "수요는 검증됐지만 경쟁 치열 — 차별화 콘셉트 없으면 비추천"),
    "식어가는 강세상권": ("⑤ 경고(둔화)", "강세였으나 식는 중 — 신규 진입 보수적, 업종 전환 수요 관찰"),
    "위축되는 약세상권": ("⑥ 주의(위축)", "기대보다 약하고 더 약해지는 중 — 원인(재건축·공동화) 확인 전 진입 보류"),
    "데이터점검": ("데이터점검", "집계 이상치 — 해석 제외"),
}


def eok(x):
    return f"{abs(x) / 1e8:,.0f}억"


def insight(r):
    if r["사분면"] == "데이터점검":
        return "데이터 집계 이상으로 해석 제외 (현장·원자료 확인 필요)"
    trend = "개선" if r["잔차_추세"] > 0.05 else ("악화" if r["잔차_추세"] < -0.05 else "보합")
    direction = "밑돎" if r["격차금액_분기"] < 0 else "웃돎"
    s = (f"[{r['상권_원형']}] 인구·인프라로 본 기대소비 대비 실제 ×{r['배율']:.2f} "
         f"(분기 약 {eok(r['격차금액_분기'])} 원 {direction}, 추세 {trend}). ")
    if r["업종_공백"]:
        s += f"유사 원형 동 대비 {r['업종_공백']} 비중이 낮아 해당 업종 공급 여지. "
    if r["업종_강점"]:
        s += f"{r['업종_강점']}은 이미 강세라 신규 진입 시 차별화 필요. "
    s += OPP[r["사분면"]][1] + "."
    if r["해석주의"]:
        s += f" ※ {r['해석주의']}"
    return s


def main():
    kw, res, feat, spend = load()
    prof = build_features(feat)
    share = build_category_share(spend).add_prefix("share_")

    df = (res.merge(kw.drop(columns=["자치구", "행정동_코드_명"]), on="행정동_코드", how="left")
             .merge(prof.reset_index(), on="행정동_코드", how="left", suffixes=("", "_2025"))
             .merge(share.reset_index(), on="행정동_코드", how="left"))

    q = {
        "집객90": df["집객시설_수"].quantile(.90), "집객80": df["집객시설_수"].quantile(.80),
        "주말60": df["주말유동비율"].quantile(.60), "주말80": df["주말유동비율"].quantile(.80),
        "주말15": df["주말유동비율"].quantile(.15), "야간80": df["야간유동비율"].quantile(.80),
        "교육90": df["share_교육"].quantile(.90), "직주85": df["직주비"].quantile(.85),
        "청년75": df["청년비율"].quantile(.75), "청년50": df["청년비율"].quantile(.50),
        "시가90": df["아파트_평균_시가"].quantile(.90), "시가85": df["아파트_평균_시가"].quantile(.85),
        "시가25": df["아파트_평균_시가"].quantile(.25),
    }
    df["상권_원형"] = df.apply(archetype, axis=1, q=q)

    # 업종 공백/강점: 같은 원형 동들의 업종 비중 중앙값 대비 비율
    gaps, strengths = [], []
    for _, r in df.iterrows():
        peers = df[df["상권_원형"] == r["상권_원형"]]
        ratio = {c: r[f"share_{c}"] / peers[f"share_{c}"].median() for c in CATS
                 if pd.notna(r[f"share_{c}"]) and peers[f"share_{c}"].median() > 0}
        excl = set(ARCHETYPE_EXCLUDE.get(r["상권_원형"], set()))
        caution = str(r.get("비추천_주의_업종", ""))
        for c, pat in CAUTION_MAP.items():
            if re.search(pat, caution):
                excl.add(c)
        low = sorted((v, c) for c, v in ratio.items() if 0.05 <= v <= 0.75 and c not in excl)[:2]
        high = sorted(((v, c) for c, v in ratio.items() if v >= 1.35), reverse=True)[:2]
        gaps.append(", ".join(f"{c.replace('_', '·')}(×{v:.2f})" for v, c in low))
        strengths.append(", ".join(f"{c.replace('_', '·')}(×{v:.2f})" for v, c in high))
        df.loc[_, "_gap_cats"] = "|".join(c for _, c in low)
    df["업종_공백"] = gaps
    df["업종_강점"] = strengths

    # 태그 3축
    acc_l, dem_l, risk_l = [], [], []
    for _, r in df.iterrows():
        a, d, k = data_tags(r, q)
        t = text_tags(r)
        acc_l.append(merge_tags(a, t["접근"]))
        dem_l.append(merge_tags(d, t["수요"]))
        risk_l.append(merge_tags(t["리스크"], k))
    df["키워드_접근성인프라"] = acc_l
    df["키워드_소비배후수요"] = dem_l
    df["키워드_환경리스크"] = risk_l

    # 해석 주의: 배율 극단치는 본사·대형점 주소 집계나 인접 거대상권 흡수 가능성
    df["해석주의"] = np.select(
        [df["배율"] >= 5, df["배율"] <= 0.25],
        ["배율 극단(×5↑): 대형점·본사 매출 주소 집계 가능성, 현장 확인 필요",
         "배율 극단(×0.25↓): 인접 거대상권 흡수·재건축 이주 가능성, 인접 동과 묶어 해석"], default="")

    # 기회 유형·점수 (선점·유출보완형만 순위 대상)
    df["기회_유형"] = df["사분면"].map(lambda s: OPP.get(s, ("", ""))[0])
    under = pct(-df["잔차_평균"])            # 저평가 정도
    trend = pct(df["잔차_추세"])             # 개선 추세
    base = pct(np.log1p(df["배후인구"]))       # 배후 수요 규모
    df["기회점수"] = (100 * (0.4 * under + 0.3 * trend + 0.3 * base)).round(1)
    eligible = df["기회_유형"].isin(["① 선점형 기회", "② 유출보완형 기회"]) & (df["해석주의"] == "")
    df.loc[~eligible, "기회점수"] = np.nan
    df["기회순위"] = df["기회점수"].rank(ascending=False, method="first")

    # 타깃 업종: 데이터(업종 공백) 기반 + 기존 정성 추천 병기
    def target_biz(r):
        data_biz = [CAT_TO_BIZ[c] for c in str(r["_gap_cats"]).split("|") if c in CAT_TO_BIZ]
        qual = r.get("추천_유망_업종")
        parts = []
        if data_biz:
            parts.append("[데이터] " + " / ".join(data_biz))
        if isinstance(qual, str) and qual:
            parts.append("[현장키워드] " + qual)
        return "  ".join(parts)
    df["타깃_업종"] = df.apply(target_biz, axis=1)
    df["기회_인사이트"] = df.apply(insight, axis=1)

    cols = ["자치구", "행정동_코드", "행정동_코드_명", "상권_원형", "상권_유형", "대표_아파트_단지",
            "키워드_접근성인프라", "키워드_소비배후수요", "키워드_환경리스크",
            "유형", "사분면", "기회_유형", "기회점수", "기회순위",
            "배율", "격차금액_분기", "잔차_추세",
            "업종_공백", "업종_강점", "타깃_업종", "비추천_주의_업종", "기회_인사이트", "해석주의",
            "상주인구", "직장인구", "직주비", "청년비율", "아파트비중순위", "아파트시가", "지하철역", "집객시설",
            "경도", "위도"]
    out = df[cols].sort_values(["기회순위", "자치구"], na_position="last")
    out.to_csv(OUT_DONG, index=False, encoding="utf-8-sig")

    gu = (df.groupby("자치구")
            .agg(행정동수=("행정동_코드", "size"),
                 대표원형=("상권_원형", lambda s: s.value_counts().index[0]),
                 선점형=("기회_유형", lambda s: (s == "① 선점형 기회").sum()),
                 유출보완형=("기회_유형", lambda s: (s == "② 유출보완형 기회").sum()),
                 확장형=("기회_유형", lambda s: (s == "③ 확장형").sum()),
                 포화형=("기회_유형", lambda s: (s == "④ 검증·포화형").sum()),
                 주의형=("기회_유형", lambda s: s.isin(["⑤ 경고(둔화)", "⑥ 주의(위축)"]).sum()),
                 배율_중앙값=("배율", "median"),
                 최고기회동=("기회점수", lambda s: df.loc[s.idxmax(), "행정동_코드_명"] if s.notna().any() else "")))
    gu.round(2).to_csv(OUT_GU, encoding="utf-8-sig")

    print(out["상권_원형"].value_counts().to_string())
    print(out["기회_유형"].value_counts().to_string())
    print(f"saved: {OUT_DONG.name} ({len(out)}), {OUT_GU.name}")


if __name__ == "__main__":
    main()
