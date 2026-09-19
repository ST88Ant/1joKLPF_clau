# -*- coding: utf-8 -*-
"""
Step 3. 정적 시각화 (Clau_pjt/image/*.png)

색 규칙
- 잔차(기대 대비 실제): 발산형 — 초과(+) = 빨강, 저평가(-) = 파랑, 0 근처 = 회색
- 단일 계열: 파랑 한 가지
- 강조: 관심 대상만 색, 나머지는 회색
"""
import warnings; warnings.filterwarnings("ignore")
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter, NullFormatter

PJT = Path(__file__).resolve().parents[1]
DATA, IMG = PJT / "data", PJT / "image"
IMG.mkdir(exist_ok=True)

# ------------------------------------------------------------------ 스타일
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURF = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, BLUE_L, BLUE_D = "#2a78d6", "#9ec5f4", "#184f95"
RED, RED_L = "#e34948", "#f4b3b2"
GRAY = "#c3c2b7"
NEUTRAL = "#f0efec"
TYPE_COLOR = {"초과달성": RED, "기대수준": GRAY, "저평가": BLUE, "데이터점검": "#52514e"}
DIV = LinearSegmentedColormap.from_list("div", ["#104281", BLUE, "#9ec5f4", NEUTRAL, RED_L, RED, "#9c2322"])

plt.rcParams.update({
    "font.family": "Malgun Gothic", "axes.unicode_minus": False,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlepad": 24, "axes.labelsize": 10,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 9,
    "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
})


def eok(v, _=None):
    """원 → 억/조 표기"""
    if v == 0:
        return "0"
    if abs(v) >= 1e12:
        return f"{v / 1e12:,.1f}조"
    if abs(v) >= 1e8:
        return f"{v / 1e8:,.0f}억"
    return f"{v / 1e4:,.0f}만"


def times(v, _=None):
    return f"×{v:g}" if v >= 1 else f"×{v:.2g}"


def subtitle(ax, text):
    ax.text(0, 1.01, text, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def save(fig, name):
    fig.savefig(IMG / name)
    plt.close(fig)
    print("saved", name)


# ------------------------------------------------------------------ 데이터
ds = pd.read_csv(DATA / "dataset_행정동_분기_2023_2025.csv", encoding="utf-8-sig")
rq = pd.read_csv(DATA / "residual_행정동_분기.csv", encoding="utf-8-sig")
dong = pd.read_csv(DATA / "residual_행정동_요약.csv", encoding="utf-8-sig")
gu = pd.read_csv(DATA / "residual_자치구_요약.csv", encoding="utf-8-sig")
perf = pd.read_csv(DATA / "model_performance.csv", encoding="utf-8-sig")
imp = pd.read_csv(DATA / "feature_importance.csv", encoding="utf-8-sig")
coef = pd.read_csv(DATA / "ridge_coefficients.csv", encoding="utf-8-sig")
summary = json.loads((DATA / "model_summary.json").read_text(encoding="utf-8"))
ok = dong[dong["유형"] != "데이터점검"]
q4 = ds[ds["기준_년분기_코드"] == 20254]

# 01. 타깃 분포 ------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
ax = axes[0]
ax.hist(q4["지출_총금액"] / 1e8, bins=60, color=BLUE, edgecolor=SURF, linewidth=1)
ax.set_title("① 원래 금액: 한쪽으로 심하게 쏠림")
subtitle(ax, "2025Q4 행정동 425곳 — 대부분 수십억, 몇 곳만 수천억~조 단위")
ax.set_xlabel("분기 지출 총액 (억 원)"); ax.set_ylabel("행정동 수")
top = q4.nlargest(1, "지출_총금액").iloc[0]
ax.annotate(f"{top['행정동_코드_명']} {eok(top['지출_총금액'])}", (top["지출_총금액"] / 1e8, 1),
            xytext=(-10, 40), textcoords="offset points", ha="right", fontsize=9, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax = axes[1]
ax.hist(q4["지출_총금액"], bins=np.logspace(7, 13, 50), color=BLUE, edgecolor=SURF, linewidth=1)
ax.set_xscale("log"); ax.xaxis.set_major_formatter(FuncFormatter(eok))
ax.set_title("② 로그 척도: 종 모양에 가까워짐")
subtitle(ax, "모델은 이 로그 값을 예측 → 결과를 ‘기대의 몇 배’로 읽는다")
ax.set_xlabel("분기 지출 총액 (로그 축)"); ax.set_ylabel("행정동 수")
save(fig, "01_지출분포_원값vs로그.png")

# 02. 주요 설명변수 vs 지출 ------------------------------------------------
pairs = [("상주인구", "상주인구 (SKT)"), ("총_직장_인구_수", "직장인구"),
         ("총_유동인구_수", "유동인구"), ("집객시설_수", "집객시설 수")]
fig, axes = plt.subplots(1, 4, figsize=(15, 3.9), sharey=True)
for ax, (c, label) in zip(axes, pairs):
    x = q4[c].clip(lower=1)
    r = np.corrcoef(np.log(x), np.log(q4["지출_총금액"]))[0, 1]
    ax.scatter(x, q4["지출_총금액"], s=14, color=BLUE, alpha=0.55, edgecolor=SURF, linewidth=0.5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(eok))
    ax.set_title(label, fontsize=11.5)
    ax.text(0.03, 0.95, f"상관 r = {r:+.2f}", transform=ax.transAxes, va="top", fontsize=10,
            color=INK, fontweight="bold")
    ax.set_xlabel(f"{label} (로그 축)")
    ax.xaxis.set_minor_formatter(NullFormatter())
axes[0].set_ylabel("분기 지출 총액 (로그 축)")
fig.suptitle("무엇이 소비와 함께 움직이나? — 상주인구보다 집객시설·직장인구가 훨씬 강하다 (2025Q4)",
             x=0.01, ha="left", fontsize=13, fontweight="bold", y=1.12)
save(fig, "02_설명변수별_지출관계.png")

# 03. 선형모델 계수 ---------------------------------------------------------
c = coef[~coef["변수"].isin(["시점", "분기"])].head(14).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5.6))
ax.barh(c["변수명"], c["계수"], color=np.where(c["계수"] > 0, RED, BLUE), height=0.62)
ax.axvline(0, color=AXIS, lw=1)
ax.grid(axis="y", visible=False)
ax.set_title("변수별 방향: 늘어나면 소비가 오르나(+) 내리나(-)")
subtitle(ax, "선형회귀 표준화 계수 — 다른 조건이 같을 때 해당 변수 1표준편차 증가의 효과(로그 지출)")
for y_, v in enumerate(c["계수"]):
    ax.text(v + (0.01 if v > 0 else -0.01), y_, f"{v:+.2f}", va="center",
            ha="left" if v > 0 else "right", fontsize=8.5, color=INK2)
ax.set_xlabel("표준화 계수")
lim = c["계수"].abs().max() * 1.25
ax.set_xlim(-lim, lim)
save(fig, "03_선형모델_계수방향.png")

# 04. 모델 성능 --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 3.2))
p = perf.iloc[::-1]
cols = [BLUE if m == summary["best_model"] else GRAY for m in p["모델"]]
ax.barh(p["모델"], p["R2"], xerr=p["R2_std"], color=cols, height=0.55,
        error_kw=dict(ecolor=MUTED, lw=1, capsize=3))
for y_, (r2, e) in enumerate(zip(p["R2"], p["평균오차배율"])):
    ax.text(0.01, y_, f"R² {r2:.3f}  ·  평균 오차 약 {e:.2f}배", va="center", color="white",
            fontsize=9.5, fontweight="bold")
ax.set_xlim(0, 1); ax.grid(axis="y", visible=False)
ax.set_title(f"모델 비교 — ‘{summary['best_model']}’ 채택 (설명력 약 {perf['R2'].max():.0%})")
subtitle(ax, "행정동 단위 5-겹 교차검증: 한 번도 본 적 없는 동의 소비를 맞히는 능력")
ax.set_xlabel("R² (1에 가까울수록 좋음, 막대 끝 = 겹별 편차)")
save(fig, "04_모델성능비교.png")

# 05. 실제 vs 기대 -----------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 6.4))
lo, hi = 1e7, 5e12
xx = np.array([lo, hi])
ax.fill_between(xx, xx * 2 / 3, xx * 1.5, color=NEUTRAL, zorder=0, label="기대수준 (±1.5배)")
ax.plot(xx, xx, color=MUTED, lw=1, zorder=1)
for t in ["기대수준", "저평가", "초과달성", "데이터점검"]:
    s = dong[dong["유형"] == t]
    ax.scatter(s["기대지출_분기평균"], s["실제지출_분기평균"], s=22, color=TYPE_COLOR[t],
               edgecolor=SURF, linewidth=0.6, label=f"{t} ({len(s)})", zorder=2,
               marker="x" if t == "데이터점검" else "o")
for _, r in pd.concat([ok.nlargest(4, "잔차_평균"), ok.nsmallest(4, "잔차_평균")]).iterrows():
    off = (-8, 4) if r["행정동_코드_명"] == "구로3동" else (5, 3)
    ax.annotate(r["행정동_코드_명"], (r["기대지출_분기평균"], r["실제지출_분기평균"]),
                xytext=off, textcoords="offset points", fontsize=8.5, color=INK2,
                ha="right" if off[0] < 0 else "left")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
ax.xaxis.set_major_formatter(FuncFormatter(eok)); ax.yaxis.set_major_formatter(FuncFormatter(eok))
ax.set_xlabel("기대 소비 (모델 예측, 분기 평균)"); ax.set_ylabel("실제 소비 (분기 평균)")
ax.set_title("실제 vs 기대: 대각선 위 = 초과달성, 아래 = 저평가")
subtitle(ax, "행정동 425곳, 2023~2025 12분기 평균")
ax.legend(loc="upper left")
save(fig, "05_실제vs기대소비.png")

# 06. 변수 중요도 ------------------------------------------------------------
GROUP_COLOR = {"인구": BLUE, "인프라": "#eb6834", "주거": "#1baf7a", "공간·시간": GRAY}
t = imp.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5.6))
ax.barh(t["변수명"], t["중요도"], color=[GROUP_COLOR[g] for g in t["그룹"]], height=0.62)
ax.grid(axis="y", visible=False)
for y_, v in enumerate(t["중요도"]):
    ax.text(v + 0.003, y_, f"{v:.3f}", va="center", fontsize=8.5, color=INK2)
handles = [plt.Rectangle((0, 0), 1, 1, color=c_) for c_ in GROUP_COLOR.values()]
ax.legend(handles, GROUP_COLOR.keys(), loc="lower right", title="변수 그룹", title_fontsize=9)
ax.set_title("무엇이 ‘기대 소비’를 결정하나 — 변수 중요도 Top 15")
subtitle(ax, "해당 변수를 무작위로 섞었을 때 설명력(R²)이 떨어지는 폭")
ax.set_xlabel("R² 감소폭")
save(fig, "06_변수중요도.png")

# 07. 잔차 분포 --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 3.8))
bins = np.linspace(-2.5, 4.5, 57)
centers = (bins[:-1] + bins[1:]) / 2
cnt, _ = np.histogram(ok["잔차_평균"].clip(-2.5, 4.5), bins=bins)
UP, DN = np.log(1.5), np.log(2 / 3)
ax.bar(centers, cnt, width=bins[1] - bins[0] - 0.02,
       color=[RED if c_ >= UP else BLUE if c_ <= DN else GRAY for c_ in centers])
ax.set_ylim(0, cnt.max() * 1.22)
for v, lab, ha in [(DN, "×0.67 ", "right"), (0, "", "center"), (UP, " ×1.5", "left")]:
    ax.axvline(v, color=MUTED, lw=0.8)
    ax.text(v, cnt.max() * 1.12, lab, ha=ha, fontsize=8.5, color=INK2)
tc = summary["type_counts"]
ax.text(-2.4, cnt.max() * 0.8, f"저평가\n{tc['저평가']}곳", color=BLUE_D, fontsize=11, fontweight="bold")
ax.text(3.0, cnt.max() * 0.8, f"초과달성\n{tc['초과달성']}곳", color="#9c2322", fontsize=11, fontweight="bold")
ax.text(0.55, cnt.max() * 0.8, f"기대수준 {tc['기대수준']}곳", color=INK2, fontsize=10)
ax.set_xticks(np.log([0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50]))
ax.set_xticklabels([times(v) for v in [0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50]])
ax.grid(axis="x", visible=False)
ax.set_title("기대 대비 실제 소비 배율 분포 — 대부분은 기대 근처, 양 끝이 발굴 대상")
subtitle(ax, "행정동별 12분기 평균 잔차 (데이터점검 4곳 제외)")
ax.set_xlabel("실제 ÷ 기대 (로그 축)"); ax.set_ylabel("행정동 수")
save(fig, "07_잔차분포.png")

# 08. 잔차 지도 --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 8.2))
norm = TwoSlopeNorm(vmin=-1.5, vcenter=0, vmax=1.5)
size = 12 + 130 * (np.log10(dong["실제지출_분기평균"]) - 7) / 6
sc = ax.scatter(dong["경도"], dong["위도"], c=dong["잔차_평균"].clip(-1.5, 1.5), cmap=DIV, norm=norm,
                s=size, edgecolor=SURF, linewidth=0.8)
fl = dong[dong["유형"] == "데이터점검"]
ax.scatter(fl["경도"], fl["위도"], s=60, marker="x", color=INK, linewidth=1.2, label="데이터점검")
gc = dong.groupby("자치구")[["경도", "위도"]].mean()
for g, r in gc.iterrows():
    ax.text(r["경도"], r["위도"], g, fontsize=9, color=INK, ha="center", va="center", alpha=0.55,
            fontweight="bold")
ax.set_aspect(1 / np.cos(np.radians(37.55)))
ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
for s_ in ax.spines.values():
    s_.set_visible(False)
cb = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.01)
cb.set_ticks(np.log([0.25, 0.5, 1, 2, 4]))
cb.set_ticklabels(["×0.25 저평가", "×0.5", "기대", "×2", "×4 초과"])
cb.outline.set_visible(False)
ax.set_title("서울 소비 잠재력 지도 — 빨강: 기대보다 많이 씀 / 파랑: 기대보다 적게 씀")
subtitle(ax, "점 = 행정동 중심, 크기 = 실제 소비 규모, ×표 = 데이터점검 (12분기 평균)")
ax.legend(loc="lower left")
save(fig, "08_잔차지도_서울.png")

# 09. Top/Bottom 15 ---------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
for ax, data, color, title in [
    (axes[0], ok.nlargest(15, "잔차_평균").iloc[::-1], RED, "초과달성 Top 15 — 인구·인프라에 비해 소비가 몰리는 곳"),
    (axes[1], ok.nsmallest(15, "잔차_평균").iloc[::-1], BLUE, "저평가 Top 15 — 조건에 비해 소비가 덜 일어나는 곳"),
]:
    labels = data["행정동_코드_명"] + " (" + data["자치구"] + ")"
    vals = data["배율"]
    ax.barh(labels, np.log(vals), color=color, height=0.62)
    ax.axvline(0, color=AXIS, lw=1)
    for y_, (v, a, e) in enumerate(zip(vals, data["실제지출_분기평균"], data["기대지출_분기평균"])):
        ax.text(np.log(v) + (0.08 if v > 1 else -0.08), y_, f"×{v:.2f}  (실제 {eok(a)} / 기대 {eok(e)})",
                va="center", ha="left" if v > 1 else "right", fontsize=8.3, color=INK2)
    ax.grid(axis="y", visible=False)
    ax.set_title(title, fontsize=12)
    ticks = [1, 2, 5, 10, 25, 50, 100] if color == RED else [0.1, 0.2, 0.5, 1]
    ax.set_xticks(np.log(ticks)); ax.set_xticklabels([times(t_) for t_ in ticks])
    ax.set_xlabel("실제 ÷ 기대 (로그 축)")
axes[0].set_xlim(0, np.log(2000)); axes[1].set_xlim(np.log(0.004), 0)
axes[1].yaxis.tick_right()
save(fig, "09_초과달성_저평가_Top15.png")

# 10. 자치구 평균 배율 --------------------------------------------------------
g = gu.sort_values("잔차_평균")
fig, ax = plt.subplots(figsize=(8.5, 7))
ax.barh(g["자치구"], g["잔차_평균"], color=np.where(g["잔차_평균"] > 0, RED, BLUE), height=0.62)
ax.axvline(0, color=AXIS, lw=1)
for y_, (v, n) in enumerate(zip(g["배율_평균"], g["행정동수"])):
    ax.text(np.log(v) + (0.008 if v > 1 else -0.008), y_, f"×{v:.2f}", va="center",
            ha="left" if v > 1 else "right", fontsize=8.5, color=INK2)
ax.grid(axis="y", visible=False)
ax.set_xticks(np.log([0.75, 0.85, 1, 1.15, 1.3])); ax.set_xticklabels(["×0.75", "×0.85", "×1", "×1.15", "×1.3"])
ax.set_xlim(np.log(0.68), np.log(1.45))
ax.set_title("자치구별 평균 소비 배율 (소속 행정동 잔차의 평균)")
subtitle(ax, "오른쪽 = 동네들이 기대보다 많이 쓰는 구 / 왼쪽 = 기대보다 덜 쓰는 구")
save(fig, "10_자치구별_평균배율.png")

# 11. 자치구별 유형 구성 --------------------------------------------------------
g = gu.assign(비율=(gu["초과달성"] - gu["저평가"]) / gu["행정동수"]).sort_values("비율")
fig, ax = plt.subplots(figsize=(9, 7.4))
left = np.zeros(len(g))
for t in ["저평가", "기대수준", "초과달성", "데이터점검"]:
    ax.barh(g["자치구"], g[t], left=left, color=TYPE_COLOR[t], height=0.66, label=t,
            edgecolor=SURF, linewidth=1.5)
    for y_, (l, v) in enumerate(zip(left, g[t])):
        if v >= 2:
            ax.text(l + v / 2, y_, int(v), ha="center", va="center", fontsize=8,
                    color="white" if t != "기대수준" else INK)
    left += g[t].values
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", ncol=4, bbox_to_anchor=(1, -0.12))
ax.set_title("25개 자치구 × 425개 행정동 — 구별 유형 구성")
subtitle(ax, "정렬: (초과달성 - 저평가) 비율 순")
ax.set_xlabel("행정동 수")
save(fig, "11_자치구별_유형구성.png")

# 12. 사분면 --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 7))
T = 0.05
ax.axhline(0, color=AXIS, lw=1); ax.axvline(0, color=AXIS, lw=1)
ax.axhspan(-T, T, color=NEUTRAL, zorder=0)
hl = ok[ok["사분면"] == "떠오르는 잠재상권"]
rest = ok[ok["사분면"] != "떠오르는 잠재상권"]
ax.scatter(rest["잔차_평균"].clip(-2.5, 4.5), rest["잔차_추세"].clip(-0.6, 0.6), s=18, color=GRAY,
           edgecolor=SURF, linewidth=0.5, label="그 외")
ax.scatter(hl["잔차_평균"], hl["잔차_추세"].clip(-0.6, 0.6), s=34, color=BLUE, edgecolor=SURF,
           linewidth=0.8, label=f"떠오르는 잠재상권 ({len(hl)})", zorder=3)
# 라벨이 뭉치지 않도록: 가장 저평가된 2곳 + 추세가 가장 가파른 4곳에 지시선
lab = pd.concat([hl.nsmallest(2, "잔차_평균"), hl.drop(hl.nsmallest(2, "잔차_평균").index).nlargest(4, "잔차_추세")])
offsets = [(8, 6), (8, 6), (-70, 30), (30, 25), (-95, -5), (25, -30)]
for (_, r), off in zip(lab.iterrows(), offsets):
    ax.annotate(f"{r['행정동_코드_명']} ({r['자치구']})", (r["잔차_평균"], min(r["잔차_추세"], 0.6)),
                xytext=off, textcoords="offset points", fontsize=8.5, color=BLUE_D,
                arrowprops=dict(arrowstyle="-", color=BLUE_L, lw=0.8))
qc = summary["quad_counts"]
for (x_, y_, name, ha) in [(-2.4, 0.55, "떠오르는 잠재상권", "left"), (4.4, 0.55, "성장하는 강세상권", "right"),
                           (-2.4, -0.55, "위축되는 약세상권", "left"), (4.4, -0.55, "식어가는 강세상권", "right")]:
    ax.text(x_, y_, f"{name}\n{qc.get(name, 0)}곳", ha=ha, va="center", fontsize=10.5,
            fontweight="bold", color=BLUE_D if name.startswith("떠오르") else INK2)
ax.set_xticks(np.log([0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50]))
ax.set_xticklabels([times(v) for v in [0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50]])
ax.set_xlim(-2.5, 4.5); ax.set_ylim(-0.65, 0.65)
ax.set_xlabel("현재 수준: 실제 ÷ 기대 (12분기 평균, 로그 축)")
ax.set_ylabel("변화 방향: 잔차의 연간 변화 (+ = 격차가 좁혀지며 소비가 따라붙는 중)")
ax.set_title("수준 × 추세 사분면 — 아직 저평가지만 소비가 빠르게 따라붙는 동네")
subtitle(ax, "회색 띠(±0.05/년) 안은 ‘안정’으로 분류")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 0.02))
save(fig, "12_수준x추세_사분면.png")

# 13. 대표 동 시계열 ----------------------------------------------------------
cols3 = [ok.nlargest(2, "잔차_평균")["행정동_코드"].tolist(),
         ok[ok["사분면"] == "떠오르는 잠재상권"].nsmallest(2, "잔차_평균")["행정동_코드"].tolist(),
         ok[ok["사분면"] == "위축되는 약세상권"].nsmallest(2, "잔차_평균")["행정동_코드"].tolist()]
picks = [cols3[c][r] for r in range(2) for c in range(3)]      # 열: 초과 / 떠오르는 / 위축
fig, axes = plt.subplots(2, 3, figsize=(14, 6.6), sharex=True)
for ax, code in zip(axes.flat, picks):
    s = rq[rq["행정동_코드"] == code]
    d = dong[dong["행정동_코드"] == code].iloc[0]
    ax.plot(s["분기라벨"], s["기대_지출"], color=MUTED, lw=2, label="기대")
    ax.plot(s["분기라벨"], s["지출_총금액"], color=BLUE, lw=2, marker="o", ms=4, label="실제")
    ax.fill_between(range(len(s)), s["기대_지출"], s["지출_총금액"],
                    color=RED if d["잔차_평균"] > 0 else BLUE, alpha=0.12)
    ax.yaxis.set_major_formatter(FuncFormatter(eok))
    ax.set_ylim(bottom=0)
    ax.set_title(f"{d['행정동_코드_명']} ({d['자치구']})", fontsize=11)
    subtitle(ax, f"{d['사분면']} · 평균 실제/기대 ×{d['배율']:.2f}")
    ax.tick_params(axis="x", rotation=45)
    ax.set_xticks(range(0, 12, 2))
axes[0, 1].legend(loc="center right")
fig.suptitle("대표 동네의 실제 vs 기대 소비 추이 (왼쪽: 초과달성 / 가운데: 떠오르는 잠재 / 오른쪽: 위축)",
             x=0.01, ha="left", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "13_대표동_시계열.png")
