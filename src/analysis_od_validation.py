"""
검증: 교통카드 O/D 통계에 똑버스 통행이 포함되는가? (01번 광교 자연실험)

01번은 2023-06부터 운행했지만 STCIS 노선별 이용량에는 2024-04부터 나타난다.
즉 2024-03 -> 2024-05 사이 '실제 이동 행태'는 그대로인데 교통카드 데이터에만
하루 약 212명(2024-05 노선별 이용량)이 새로 들어왔다.
O/D 통계에 똑버스가 포함된다면 광교 구역 내부 통행이 그만큼 늘어야 한다.

비교: 처리군(이의동·하동 출발 -> 01 구역 도착) vs 비교군(정자동·매탄동 출발 -> 같은 동 도착)
입력: data/processed/od_monthly_raw.csv, route_period_summary.csv
출력: data/processed/od_validation_01.csv
"""

import pandas as pd

from config import PROCESSED, ZONES

PRE, POST = "2024-03", "2024-05"
DAYS = {"2024-03": 31, "2024-05": 31}


def main():
    raw = pd.read_csv(PROCESSED / "od_monthly_raw.csv", dtype={"일자": str})
    raw = raw[raw["일자"].isin([PRE, POST]) & (raw["시군구(도착)"] == "수원시")]

    zone = ZONES["01"]
    treat = raw[raw["읍면동(출발)"].isin(["이의동", "하동"]) & raw["읍면동(도착)"].isin(zone)]
    ctrl = raw[raw["읍면동(출발)"].isin(["정자동", "매탄동"])
               & (raw["읍면동(도착)"] == raw["읍면동(출발)"])]

    t = treat.groupby("일자")["통행량"].sum() / 31
    c = ctrl.groupby("일자")["통행량"].sum() / 31

    summary = pd.read_csv(PROCESSED / "route_period_summary.csv", dtype={"노선": str})
    drt = summary[(summary["노선"] == "01") & (summary["기간"] == POST)]["일평균"].iloc[0]

    expected_if_included = t[PRE] * (c[POST] / c[PRE]) + drt
    res = pd.DataFrame([
        {"구분": "처리군 (광교 구역 내부)", "2024-03": t[PRE], "2024-05": t[POST],
         "변화율(%)": (t[POST] / t[PRE] - 1) * 100},
        {"구분": "비교군 (정자·매탄 동 내부)", "2024-03": c[PRE], "2024-05": c[POST],
         "변화율(%)": (c[POST] / c[PRE] - 1) * 100},
        {"구분": "처리군 기대값 (OD에 똑버스 포함 시)", "2024-03": t[PRE], "2024-05": expected_if_included,
         "변화율(%)": (expected_if_included / t[PRE] - 1) * 100},
    ]).round(1)
    res.to_csv(PROCESSED / "od_validation_01.csv", index=False, encoding="utf-8-sig")

    print(f"01번 2024-05 하루 평균 이용: {drt:.0f}명")
    print(res.to_string(index=False))
    gap = t[POST] - t[PRE] * (c[POST] / c[PRE])
    print(f"\n비교군 대비 처리군 변화(하루): {gap:+.0f}건  (포함된다면 약 +{drt:.0f}건 기대)")


if __name__ == "__main__":
    main()
