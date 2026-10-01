"""
똑버스 노선별 이용 규모·정착 추이·시간대 패턴·방학 비교.

입력: data/processed/route_usage.csv, route_usage_daily.csv (merge_route_usage.py 실행 결과)
출력:
- data/processed/route_period_summary.csv : 노선·기간별 하루 평균(전체/평일/주말)
- data/processed/route_hourly_weekday.csv : 노선·기간·시간대별 평일 평균
- data/processed/vacation_comparison.csv  : 개학 중 vs 방학 중 등하교 피크 비교
"""

import pandas as pd

from config import PROCESSED, SCHOOL_PEAK_HOURS, VACATION_PAIRS


def main():
    hourly = pd.read_csv(PROCESSED / "route_usage.csv", dtype={"노선": str})
    daily = pd.read_csv(PROCESSED / "route_usage_daily.csv", dtype={"노선": str})
    hourly = hourly.merge(daily[["노선", "날짜", "평일", "기간"]], on=["노선", "날짜"])

    summary = daily.groupby(["노선", "기간"]).apply(lambda g: pd.Series({
        "일수": len(g),
        "일평균": g["이용량"].mean(),
        "평일평균": g.loc[g["평일"], "이용량"].mean(),
        "주말평균": g.loc[g["주말"], "이용량"].mean(),
    }), include_groups=False).round(1).reset_index()
    summary["평일/주말"] = (summary["평일평균"] / summary["주말평균"]).round(2)
    summary.to_csv(PROCESSED / "route_period_summary.csv", index=False, encoding="utf-8-sig")

    wk = (hourly[hourly["평일"]].groupby(["노선", "기간", "시간대"])["이용량"].mean()
          .round(1).reset_index())
    wk.to_csv(PROCESSED / "route_hourly_weekday.csv", index=False, encoding="utf-8-sig")

    rows = []
    for route, term, vac in VACATION_PAIRS:
        a = wk[(wk["노선"] == route) & (wk["기간"] == term)].set_index("시간대")["이용량"]
        b = wk[(wk["노선"] == route) & (wk["기간"] == vac)].set_index("시간대")["이용량"]
        if a.empty or b.empty:
            print(f"건너뜀: {route} {term} vs {vac} (데이터 없음)")
            continue
        peak = SCHOOL_PEAK_HOURS
        rest = [h for h in a.index if h not in peak]
        rows.append({
            "노선": route, "개학중": term, "방학": vac,
            "개학_일평균": round(a.sum()), "방학_일평균": round(b.sum()),
            "개학_피크": round(a[peak].sum()), "방학_피크": round(b[peak].sum()),
            "피크_변화율": round((b[peak].sum() / a[peak].sum() - 1) * 100, 1),
            "나머지_변화율": round((b[rest].sum() / a[rest].sum() - 1) * 100, 1),
            "피크_감소량": round(a[peak].sum() - b[peak].sum()),
        })
    vac = pd.DataFrame(rows)
    vac.to_csv(PROCESSED / "vacation_comparison.csv", index=False, encoding="utf-8-sig")

    print(summary.to_string(index=False))
    print()
    print(vac.to_string(index=False))


if __name__ == "__main__":
    main()
