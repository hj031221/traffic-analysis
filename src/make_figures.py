"""
보고서용 그림 생성 (PNG, 300dpi). 모든 analysis_*.py 실행 후 사용.

fig1_route_types.png      : 노선별 평일 시간대 패턴, 개학(9월) vs 여름방학(8월)
fig2_data_blindspot.png   : 운행 기간 vs 데이터 수록 기간 타임라인
fig3_validation_did.png   : (a) 01 자연실험 (b) 기존 대중교통 잠식률 민감도
fig4_car_per_capita.png   : 구별 인구 천 명당 승용 자가용 (부록)

색: 범주형 슬롯 1~4 (검증된 팔레트, 인접 쌍 CVD ΔE >= 9.1). 대비가 낮은 슬롯은 직접 라벨 병기.
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

from config import FIGURES, PROCESSED, ROUTES

# ---- 스타일 -----------------------------------------------------------------
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if any(k in f for k in ["NotoSansCJK-Regular", "NanumGothic", "malgun", "AppleGothic"]):
        font_manager.fontManager.addfont(f)
KFONTS = ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]  # Windows·Mac·Linux 순

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e1e0d9"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
ROUTE_COLOR = {"01": S1, "02": S2, "03": S3, "04": S4}

plt.rcParams.update({
    "font.family": KFONTS, "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "lines.linewidth": 2, "legend.frameon": False,
})


def save(fig, name):
    fig.savefig(FIGURES / name, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("저장:", name)


def label(route):
    return f"{route} {ROUTES[route]['name']}"


# ---- 그림 1 -----------------------------------------------------------------
def fig1():
    wk = pd.read_csv(PROCESSED / "route_hourly_weekday.csv", dtype={"노선": str})
    vac = pd.read_csv(PROCESSED / "vacation_comparison.csv", dtype={"노선": str})
    summ = pd.read_csv(PROCESSED / "route_period_summary.csv", dtype={"노선": str})

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), sharex=True)
    for ax, route in zip(axes.flat, ["01", "02", "03", "04"]):
        term = wk[(wk["노선"] == route) & (wk["기간"] == "2026-09")]
        vacd = wk[(wk["노선"] == route) & (wk["기간"] == "2026-08")]
        ax.axvspan(6.5, 8.5, color=GRID, alpha=0.5, lw=0)
        ax.axvspan(15.5, 16.5, color=GRID, alpha=0.5, lw=0)
        ax.plot(term["시간대"], term["이용량"], color=S1, marker="o", ms=3, label="개학 중 (2026-09)")
        ax.plot(vacd["시간대"], vacd["이용량"], color=S2, marker="o", ms=3, ls="--", label="여름방학 (2026-08)")

        ratio = summ[(summ["노선"] == route) & (summ["기간"] == "2026-09")]["평일/주말"].iloc[0]
        v = vac[(vac["노선"] == route) & (vac["개학중"] == "2026-09")].iloc[0]
        ax.set_title(f"{label(route)}", loc="left")
        ax.text(0.02, 0.97, f"평일/주말 이용 {ratio:.1f}배\n등하교 시간대 방학 중 {v['피크_변화율']:+.0f}%",
                transform=ax.transAxes, va="top", fontsize=8, color=INK2)
        ax.set_ylim(0, max(term["이용량"].max(), vacd["이용량"].max()) * 1.35)
    for ax in axes[1]:
        ax.set_xlabel("시각")
        ax.set_xticks(range(6, 24, 2))
    for ax in axes[:, 0]:
        ax.set_ylabel("평일 시간당 이용 (명)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.text(0.5, -0.02, "음영: 등하교 시간대(7·8시, 16시). 자료: STCIS 노선별 이용량(각 월 1~14일, 공휴일 제외 평일 평균)",
             ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "fig1_route_types.png")


# ---- 그림 2 -----------------------------------------------------------------
def fig2():
    end = pd.Timestamp("2026-09-30")
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    routes = ["01", "02", "03", "04"]
    for i, route in enumerate(routes):
        y = len(routes) - 1 - i
        s = pd.Timestamp(ROUTES[route]["service_start"])
        d = pd.Timestamp(ROUTES[route]["data_start"] + "-01")
        d = max(d, s)
        # 운행 기간 (회색 테두리 막대)
        ax.barh(y + 0.18, (end - s).days, left=s, height=0.3, color=SURFACE, edgecolor=MUTED, lw=1)
        # 노선 통계 수록 기간
        ax.barh(y + 0.18, (end - d).days, left=d, height=0.3, color=S1, edgecolor=SURFACE, lw=1)
        # OD·정류장 통계: 반영 확인 안 됨
        ax.barh(y - 0.18, (end - s).days, left=s, height=0.3, color="none", edgecolor=S2,
                hatch="////", lw=1)
        if (d - s).days > 60:
            ax.annotate(f"교통카드 데이터 미수록\n약 {round((d - s).days / 30)}개월",
                        xy=(s + (d - s) / 2, y + 0.18), xytext=(0, 14), textcoords="offset points",
                        ha="center", fontsize=7.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_yticks(range(len(routes)))
    ax.set_yticklabels([label(r) for r in reversed(routes)])
    ax.set_xlim(pd.Timestamp("2023-04-01"), end + pd.Timedelta(days=20))
    ax.set_ylim(-0.6, len(routes) - 0.2)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m"))
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=SURFACE, edgecolor=MUTED, label="실제 운행 기간"),
        Patch(facecolor=S1, edgecolor=SURFACE, label="노선별 이용량 통계에 수록"),
        Patch(facecolor="none", edgecolor=S2, hatch="////", label="O/D·정류장 통계: 반영 확인 안 됨"),
    ], loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=3, fontsize=8)
    fig.text(0.5, -0.04, "자료: STCIS 노선별 이용량·이용객 O/D·정류장별 이용량, 경기도·수원시 보도자료(운행 개시일)",
             ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    save(fig, "fig2_data_blindspot.png")


# ---- 그림 3 -----------------------------------------------------------------
def fig3():
    val = pd.read_csv(PROCESSED / "od_validation_01.csv")
    did = pd.read_csv(PROCESSED / "did_results.csv", dtype={"노선": str})
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw={"width_ratios": [1, 1.45]})

    # (a) 01 자연실험
    names = ["비교군\n실제", "광교 구역\n실제", "광교 구역\n기대값*"]
    vals = [val.iloc[1]["변화율(%)"], val.iloc[0]["변화율(%)"], val.iloc[2]["변화율(%)"]]
    colors = [MUTED, S1, "none"]
    bars = a.bar(names, vals, color=colors, edgecolor=[MUTED, S1, S1], width=0.55, lw=1.2,
                 hatch=["", "", "////"])
    for r, v in zip(bars, vals):
        a.text(r.get_x() + r.get_width() / 2, v + (0.4 if v >= 0 else -0.4), f"{v:+.1f}%",
               ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5, color=INK)
    a.axhline(0, color=INK2, lw=0.8)
    a.set_ylim(-3, 11)
    a.set_ylabel("2024-03 → 05 통행 변화율")
    a.set_title("(a) 똑버스 01 카드데이터 편입 전후", loc="left")
    a.grid(axis="x", visible=False)

    # (b) 잠식률 민감도
    d = did[did["지표"].isin(["구역내부", "단거리3km"])].copy()
    d["라벨"] = d["노선"] + " " + d["지표"].str.replace("단거리3km", "3km미만") + "  " + d["개통전"].str[2:].str.replace("-", ".") + "→" + d["개통후"].str[2:].str.replace("-", ".")
    d = d.sort_values(["노선", "기준월_부적합", "지표", "개통전"]).reset_index(drop=True)
    ok = d[~d["기준월_부적합"]]
    lo, hi = ok["잠식률(%)"].clip(lower=0).min(), ok["잠식률(%)"].clip(lower=0).max()
    b.axvspan(lo, hi, color=GRID, alpha=0.7, lw=0)
    b.axvline(0, color=INK2, lw=0.8)
    for i, r in d.iterrows():
        c = ROUTE_COLOR[r["노선"]]
        if r["기준월_부적합"]:
            b.scatter(r["잠식률(%)"], i, s=36, facecolor=SURFACE, edgecolor=MUTED, zorder=3, lw=1.2)
        else:
            b.scatter(r["잠식률(%)"], i, s=36, color=c, edgecolor=SURFACE, zorder=3, lw=1.5)
    b.set_yticks(range(len(d)))
    b.set_yticklabels(d["라벨"], fontsize=7)
    b.set_xlabel("잠식률 (%) = 기존 대중교통 감소분 ÷ 똑버스 이용")
    b.set_title("(b) 기존 대중교통 잠식률 민감도", loc="left")
    b.set_ylim(len(d) - 0.5, -1.3)
    b.text((lo + hi) / 2, -0.85, f"기준월 적합 조합 범위 {lo}~{hi}%", ha="center", va="center", fontsize=7.5, color=INK)
    b.grid(axis="y", visible=False)
    fig.text(0.5, -0.06, "* O/D 통계에 똑버스가 포함됐을 경우의 기대값(비교군 추세 + 2024-05 똑버스 01 일평균 212명). "
             "(b) 속 빈 점: 연휴가 많은 2025-05를 비교 시점으로 쓴 조합(참고용). 음수 = 기존 통행 증가",
             ha="center", fontsize=7, color=MUTED, wrap=True)
    fig.tight_layout()
    save(fig, "fig3_validation_did.png")


# ---- 그림 4 (부록) -----------------------------------------------------------
def fig4():
    df = pd.read_csv(PROCESSED / "car_per_capita_gu.csv")
    df["월"] = pd.to_datetime(df["월"])
    order = ["수원시 권선구", "수원시 영통구", "수원시 팔달구", "수원시 장안구"]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    for gu, c in zip(order, [S1, S2, S3, S4]):
        s = df[df["지역"] == gu].sort_values("월")
        ax.plot(s["월"], s["인구천명당_자가용"], color=c, label=gu.replace("수원시 ", ""))
        ax.text(s["월"].iloc[-1] + pd.Timedelta(days=15), s["인구천명당_자가용"].iloc[-1],
                gu.replace("수원시 ", ""), va="center", fontsize=8, color=INK)
    ax.set_ylabel("인구 천 명당 승용 자가용 (대)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m"))
    ax.legend(loc="upper left", ncol=4, fontsize=8)
    ax.set_xlim(df["월"].min(), df["월"].max() + pd.Timedelta(days=120))
    fig.text(0.5, -0.04, "권선구: 인구 -1.7%인데 인구당 자가용 +15.3% (2022.01→2026.08). 자료: 국토교통부 자동차등록현황, 행정안전부 주민등록인구",
             ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    save(fig, "fig4_car_per_capita.png")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
