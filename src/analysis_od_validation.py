"""01번 노선자료 식별 시점 전후의 관측 비교 및 조건부 기대값.

O/D에 DRT가 빠졌다는 사실이나 '행태 불변'을 입증하지 않는다. 노선 승차
표본 중 선택 구역과 O/D 정의에 대응하는 비율 q를 알 수 없으므로 여러 q의
조건부 기대값을 별도 저장한다. 기관의 수록·환승·공간 귀속 정의 확인이 필요하다.
"""
import pandas as pd
from config import PROCESSED, ZONES

PRE, POST = "2024-03", "2024-05"


def main():
    raw = pd.read_csv(PROCESSED / "od_monthly_raw.csv")
    raw = raw[raw["일자"].isin([PRE, POST]) & raw["시군구(도착)"].eq("수원시")]
    treat = raw[raw["읍면동(출발)"].isin(["이의동", "하동"]) & raw["읍면동(도착)"].isin(ZONES["01"])]
    ctrl = raw[raw["읍면동(출발)"].isin(["정자동", "매탄동"])
               & raw["읍면동(도착)"].eq(raw["읍면동(출발)"])]
    t, c = treat.groupby("일자")["통행량"].sum() / 31, ctrl.groupby("일자")["통행량"].sum() / 31
    summary = pd.read_csv(PROCESSED / "route_period_summary.csv", dtype={"노선": str})
    s = summary[summary["노선"].eq("01") & summary["기간"].eq(POST)].iloc[0]
    drt = float(s["일평균"])
    rows = [{"구분": name, "2024-03": x[PRE], "2024-05": x[POST],
             "변화율(%)": (x[POST] / x[PRE] - 1) * 100}
            for name, x in [("광교선택구역_관측", t), ("정자매탄_동내부_관측", c)]]
    pd.DataFrame(rows).to_csv(PROCESSED / "od_validation_01.csv", index=False, encoding="utf-8-sig")
    base = t[PRE] * c[POST] / c[PRE]
    scenarios = [{"포착률가정_q": q, "조건부기대_일": base + q * drt,
                  "실제관측_일": t[POST], "노선01_관측일평균": drt,
                  "노선01_관측기간": f"{s['관측시작']}~{s['관측끝']}",
                  "주의": "q미확인_행태불변미검증_통행정의미확인_수록여부판정불가"}
                 for q in [0, .25, .5, .75, 1]]
    pd.DataFrame(scenarios).to_csv(PROCESSED / "od_validation_scenarios.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows).round(2).to_string(index=False))
    print(f"비교군 비율 보정 차이 {t[POST] - base:.2f}건/일. O/D 미반영 증명으로 해석하지 않음.")


if __name__ == "__main__":
    main()
