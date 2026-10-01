"""
청소년 이용 비중 비교: 똑버스는 일반 버스보다 청소년이 많이 타는가?

STCIS '수단통행량(이용자유형별)' 수원시 읍면동 전체, 2025-09-01~14 평일로
일반 버스(시내+마을)의 청소년 비중을 동·구역별로 구하고,
수원시정연구원(2024) 보고서의 광교 똑버스 이용자 중 청소년 비중 20.3%와 비교한다.

주의: 보고서 수치는 2023-06~2024-06 전체 요일 기준이고, 여기서는 2025-09 평일 기준이다.
기간·요일 기준이 달라 배수 차이는 동일 모집단의 효과나 추세가 아니다.

입력: data/raw/user_type/수단통행량_이용자유형_수원_읍면동_*.xlsx
출력: data/processed/teen_share_bus.csv
"""

import pandas as pd

from config import CONTROLS, HOLIDAYS, PROCESSED, RAW, ZONES

DRT_TEEN_SHARE_GWANGGYO = 20.3  # 수원시정연구원(2024), 2023-06~2024-06 광교 똑버스


def main():
    src = next((RAW / "user_type").glob("*읍면동*.xlsx"))
    d = pd.read_excel(src)
    d = d[d["시도코드"].astype(str) != "합계"].copy()
    for c in ["읍면동", "일", "이용자유형"]:
        d[c] = d[c].replace(0, pd.NA).ffill()
    dates = pd.to_datetime(d["일"].str[:10], errors="raise")
    d = d[dates.dt.dayofweek.lt(5) & ~dates.dt.strftime("%Y-%m-%d").isin(HOLIDAYS)]
    bus = d[d["교통수단"].isin(["시내", "마을"])]

    group = {dong: route for route, dongs in ZONES.items() for dong in dongs}
    group.update({dong: "비교군" for dong in CONTROLS})

    by_dong = bus.pivot_table(index="읍면동", columns="이용자유형", values="발생량", aggfunc="sum").fillna(0)
    by_dong["전체"] = by_dong.sum(axis=1)
    by_dong["구역"] = by_dong.index.map(lambda x: group.get(x, "기타"))

    rows = [{"구분": "수원시 전체", "청소년": by_dong["청소년"].sum(), "전체": by_dong["전체"].sum()}]
    for g, sub in by_dong.groupby("구역"):
        rows.append({"구분": f"구역 {g}" if g[0].isdigit() else g, "청소년": sub["청소년"].sum(), "전체": sub["전체"].sum()})
    out = pd.DataFrame(rows)
    out["청소년비중(%)"] = (out["청소년"] / out["전체"] * 100).round(1)
    out["똑버스 광교 대비(배)"] = (DRT_TEEN_SHARE_GWANGGYO / out["청소년비중(%)"]).round(1)
    out["주의"] = "똑버스2023-06~2024-06전요일_vs_버스2025-09-01~14평일_비동시비교"
    out.to_csv(PROCESSED / "teen_share_bus.csv", index=False, encoding="utf-8-sig")

    print(f"광교 똑버스 청소년 비중(보고서): {DRT_TEEN_SHARE_GWANGGYO}%")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
