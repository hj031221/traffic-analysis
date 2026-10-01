"""
이중차분(DiD): 똑버스 개통 후 운행 구역의 '기존 대중교통(버스·전철)' 통행이 줄었는가?

전제(가정) - 결과는 아래 가정이 성립할 때만 해석 가능하다.
  A1. O/D 통계에 똑버스 통행은 포함되지 않는다 (analysis_od_validation.py 참고)
  A2. 비교군(정자·조원·매탄·세류동)이 처리군의 '똑버스가 없었을 경우' 추세를 대표한다
  A3. 똑버스가 대체하는 기존 통행은 '구역 내부' 또는 '3km 미만' 통행에 나타난다

잠식률 = (비교군 대비 기존 대중교통 감소분) / (똑버스 하루 이용)
  -> "똑버스 이용 중 기존 버스·전철에서 넘어온 비율"의 대략적 추정치

기준월 선택에 결과가 민감하므로 여러 조합을 모두 계산한다(민감도 분석).
2025-05는 연휴(근로자의날·어린이날·대체공휴일·대선)로 비교군 통행이 크게 줄어
비교 시점(전·후 모두)으로 부적합하다는 표시를 남긴다.

입력: data/processed/od_monthly_metrics.csv, route_period_summary.csv
출력: data/processed/did_results.csv
"""

import pandas as pd

from config import PROCESSED

SPECS = [  # (노선, 개통 전, 개통 후)
    ("02", "2024-09", "2025-04"),
    ("02", "2024-09", "2025-05"),
    ("02", "2024-09", "2025-12"),
    ("03", "2024-09", "2025-12"),
    ("03", "2025-04", "2025-12"),
    ("03", "2025-05", "2025-12"),
]
METRICS = ["구역내부", "단거리3km", "수원내", "전체"]
UNSUITABLE_BASE = {"2025-05"}


def drt_daily(summary, route, month):
    """해당 월의 똑버스 하루 평균 이용. 그 달 자료가 없으면 앞뒤 가장 가까운 두 달 평균."""
    s = summary[summary["노선"] == route].set_index("기간")["일평균"]
    if month in s.index:
        return s[month]
    before = s[s.index < month]
    after = s[s.index > month]
    vals = [x for x in [before.iloc[-1] if len(before) else None,
                        after.iloc[0] if len(after) else None] if x is not None]
    return sum(vals) / len(vals)


def main():
    m = pd.read_csv(PROCESSED / "od_monthly_metrics.csv", dtype={"그룹": str})
    summary = pd.read_csv(PROCESSED / "route_period_summary.csv", dtype={"노선": str})
    g = m.groupby(["그룹", "월"])[METRICS].sum()

    rows = []
    for route, pre, post in SPECS:
        a = drt_daily(summary, route, post)
        for met in METRICS:
            t0, t1 = g.loc[(route, pre), met], g.loc[(route, post), met]
            c0, c1 = g.loc[("비교군", pre), met], g.loc[("비교군", post), met]
            counterfactual = t0 * c1 / c0
            effect = t1 - counterfactual
            rows.append({
                "노선": route, "개통전": pre, "개통후": post, "지표": met,
                "처리군_전": round(t0), "처리군_후": round(t1),
                "처리군_변화율": round((t1 / t0 - 1) * 100, 1),
                "비교군_변화율": round((c1 / c0 - 1) * 100, 1),
                "효과_일": round(effect), "똑버스_일이용": round(a),
                "잠식률(%)": round(-effect / a * 100),
                "기준월_부적합": pre in UNSUITABLE_BASE or post in UNSUITABLE_BASE,
            })
    res = pd.DataFrame(rows)
    res.to_csv(PROCESSED / "did_results.csv", index=False, encoding="utf-8-sig")

    main_view = res[res["지표"].isin(["구역내부", "단거리3km"])]
    print(main_view.to_string(index=False))
    ok = main_view[~main_view["기준월_부적합"]]
    lo, hi = ok["잠식률(%)"].clip(lower=0).min(), ok["잠식률(%)"].clip(lower=0).max()
    print(f"\n기준월 적합 조합의 잠식률 범위(음수는 0으로): {lo}% ~ {hi}%")


if __name__ == "__main__":
    main()
