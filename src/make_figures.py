"""
보고서용 그림 생성 (PNG, 300dpi). 모든 analysis_*.py 실행 후 사용.

fig1_route_types.png      : 노선별 평일 시간대 패턴, 개학(9월) vs 여름방학(8월)
fig2_data_blindspot.png   : 01번 정식 운행과 STCIS 조회 시작의 시간차
fig3_validation_did.png   : 거리 기준에 따른 분석대상 변경의 민감도
fig4_car_per_capita.png   : 구별 인구 천 명당 승용 자가용 (부록)

색과 직접 라벨·선 모양을 함께 사용한다.
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
        ax.plot(term["시간대"], term["이용량"], color=S1, marker="o", ms=3, label="9월 1~14일")
        ax.plot(vacd["시간대"], vacd["이용량"], color=S2, marker="o", ms=3, ls="--", label="8월 1~14일")

        ratio = summ[(summ["노선"] == route) & (summ["기간"] == "2026-09")]["평일/주말"].iloc[0]
        v = vac[(vac["노선"] == route) & (vac["개학중"] == "2026-09")].iloc[0]
        ax.set_title(f"{label(route)}", loc="left")
        ax.text(0.02, 0.97, f"평일/주말 이용 {ratio:.1f}배\n7·8·16시의 8월/9월 차이 {v['피크_변화율']:+.0f}%",
                transform=ax.transAxes, va="top", fontsize=8, color=INK2)
        ax.set_ylim(0, max(term["이용량"].max(), vacd["이용량"].max()) * 1.35)
    for ax in axes[1]:
        ax.set_xlabel("시각")
        ax.set_xticks(range(6, 24, 2))
    for ax in axes[:, 0]:
        ax.set_ylabel("평일 시간당 승차 집계 (건)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.text(0.5, -0.02, "음영: 7·8·16시. STCIS 노선별 이용량, 휴일 제외 평일 평균. 계절별 관측 차이이며 이용 목적·연령을 확정하지 않음.",
             ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "fig1_route_types.png")


# ---- 그림 2 -----------------------------------------------------------------
def fig2():
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    start = pd.Timestamp(ROUTES["01"]["service_start"])
    observed = pd.Timestamp(ROUTES["01"]["data_start"] + "-01")
    end = pd.Timestamp("2024-06-30")
    ax.axvspan(start, observed, color=S2, alpha=.13, lw=0)
    ax.plot([start, end], [1, 1], color=S1, lw=7, solid_capstyle="butt")
    ax.plot([observed, end], [0, 0], color=S3, lw=7, solid_capstyle="butt")
    ax.scatter([start, observed], [1, 0], color=[S1, S3], s=25, zorder=3)
    ax.text(start, 1.16, "정식 운행 2023-06-07", fontsize=8, color=INK)
    ax.text(observed, .17, "조회 시작 2024-04", fontsize=8, color=INK)
    ax.text(start + (observed - start) / 2, .42, "약 10개월의 조회 공백", ha="center", fontsize=10, weight="bold", color=INK)
    ax.set_yticks([0, 1], ["STCIS 노선 통계\n(작성자 조회 기록)", "01 광교 실제 운행\n(정식 개통 발표)"])
    ax.set_ylim(-.35, 1.4)
    ax.set_xlim(pd.Timestamp("2023-05-20"), end)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m"))
    ax.set_title("보이지 않는 버스: 운행 시작과 노선 통계 조회 시작의 차이", loc="left", pad=12)
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.text(.5, -.05, "운행 시작: 경기도(2023-05-29). 조회 시작: 작성자의 STCIS 확인 기록(소급 수록·원인 확인 전).\n공백은 실제 이용 0건을 뜻하지 않으며, STCIS 표시 구간의 연속 관측을 검증한 그림도 아님.",
             ha="center", fontsize=7, color=INK2)
    fig.tight_layout()
    save(fig, "fig2_data_blindspot.png")


def fig3():
    d = pd.read_csv(PROCESSED / "did_results.csv", dtype={"노선": str})
    d = d[(d["노선"] == "02") & (d["기준월"] == "2024-09")
          & (d["비교월"] == "2025-12") & (d["비교군구성"] == "전체비교군")]
    metrics = ["평균거리3km_가변", "평균거리3km_공통고정"]
    vals = [d[d["지표"] == m]["비교군비율보정차_일"].iloc[0] for m in metrics]
    fig, (ax, detail) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={"width_ratios": [1, 1.25]})
    ax.bar(["매월 대상 변경", "공통 쌍 기준월 고정"], vals, color=[S2, S1], width=.5)
    ax.axhline(0, color=INK2, lw=.8)
    for x, v in enumerate(vals):
        ax.text(x, v + (7 if v >= 0 else -7), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top")
    ax.set_ylim(-210, 100)
    ax.set_ylabel("비교군 비율로 보정한 통행 차이 (건/일)")
    ax.set_title("(a) 대상 정의에 따라 부호 변화", loc="left")
    ax.tick_params(axis="x", labelsize=7.5)
    detail.axis("off")
    detail.set_title("(b) 오목천동 내부 쌍의 사례", loc="left")
    detail.text(.02, .86, "2024-09: 평균거리 2,944m · 6,282건\n2025-12: 평균거리 3,020m · 5,903건\n\n가변 지표에서는 후월 5,903건 전체 제외\n→ 하루 190.4건의 분석대상 변화\n\n3km 미만 개별 통행량으로 해석할 수 없음\n공통 고정 집계도 인과효과·전환율이 아님",
                va="top", fontsize=9, linespacing=1.65)
    fig.text(.5, -.03, "02번 2024-09→2025-12. 고정 지표: 전후 공통 관측 쌍 중 기준월 평균거리<3km. 미관측 쌍은 0으로 대체하지 않음.",
             ha="center", fontsize=7, color=INK2)
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


# ---- 그림 5 -----------------------------------------------------------------
def fig5():
    c = pd.read_csv(PROCESSED / "carbon_breakeven_curve.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.axvspan(2.43, 3.24, color=GRID, alpha=0.7, lw=0)
    ax.text(2.835, 292, "거리 가중\n재차인원 가정 구간\n2.43~3.24명", ha="center", va="top", fontsize=7.5, color=INK2)
    ax.axhline(100, color=INK2, lw=0.9, ls=(0, (4, 3)))
    ax.text(5.95, 104, "자가용 대체 직결 여객km가 100%인 경우", ha="right", va="bottom", fontsize=7.5, color=INK2)
    for fuel, col in [("경유", S1), ("전기", S2)]:
        d = c[c["차량"] == fuel]
        ax.fill_between(d["재차인원"], d["낙관"], d["비관"].clip(upper=300), color=col, alpha=0.15, lw=0)
        ax.plot(d["재차인원"], d["중앙"], color=col, label=f"{fuel} (중앙, 공차 0.4)")
        if fuel == "경유":
            ax.plot(d["재차인원"], d["중앙_공차0"], color=col, ls="--", lw=1.5, label="경유 (중앙, 공차 0)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(1, 6)
    ax.set_ylim(0, 300)
    ax.set_xlabel("공차 제외 거리 평균 재차인원 가정 (명)")
    ax.set_ylabel("손익분기 자가용 대체 여객km 비중 (%)")
    ax.set_title("탄소 손익분기: 운행 조건에 따른 대체 여객km 비중", loc="left")
    fig.text(0.5, -0.04, "음영: 운행 가정 범위(신뢰구간 아님). 전력: 공식 0.4173kgCO2eq/kWh(2023년도, 2025-12 공표).\n공차=공차거리/탑승운행거리. 경유 연소CO2·전력CO2eq 근사 비교이며 실제 노선 성과 아님.",
             ha="center", fontsize=7, color=INK2)
    fig.tight_layout()
    save(fig, "fig5_carbon_breakeven.png")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
