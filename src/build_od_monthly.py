"""
STCIS 웹 '이용객 O/D'(출발 읍면동 1개 -> 도착 전국 읍면동, 1개월 합계) 엑셀을 병합하고
출발 동·월별 지표(하루 평균)를 계산한다.

입력: data/raw/od_monthly/od_{출발동}_{YYYY-MM}.xlsx
      열: 일자, 시도(출발), 시군구(출발), 읍면동(출발), 시도(도착), 시군구(도착), 읍면동(도착),
          통행량, 통행시간(분), 통행거리(m)
출력:
- data/processed/od_monthly_raw.csv     : 병합 원자료
- data/processed/od_monthly_metrics.csv : 출발 동·월별 하루 평균 지표
    전체      : 모든 도착지
    수원내    : 도착지가 수원시
    구역내부  : 도착지가 같은 똑버스 구역(처리군) 또는 같은 동(비교군)
    평균거리3km_가변 : 월평균 통행거리 3km 미만인 OD 쌍 (개별 통행거리 아님)
"""

import calendar

import pandas as pd

from config import CONTROLS, PROCESSED, RAW, ZONES


def zone_of(dong):
    for route, dongs in ZONES.items():
        if dong in dongs:
            return route, set(dongs)
    return ("비교군" if dong in CONTROLS else "기타"), {dong}


def main():
    files = sorted((RAW / "od_monthly").glob("*.xlsx"))
    raw = pd.concat([pd.read_excel(f) for f in files], ignore_index=True)
    raw["일자"] = raw["일자"].astype(str)
    keys = ["일자", "시도(출발)", "시군구(출발)", "읍면동(출발)",
            "시도(도착)", "시군구(도착)", "읍면동(도착)"]
    if raw[keys].isna().any().any() or raw.duplicated(keys).any():
        raise ValueError("O/D 키에 결측 또는 중복이 있습니다.")
    for col in ["통행량", "통행거리"]:
        raw[col] = pd.to_numeric(raw[col], errors="raise")
        if raw[col].isna().any() or (raw[col] < 0).any():
            raise ValueError(f"O/D {col} 결측 또는 음수입니다.")
    raw.to_csv(PROCESSED / "od_monthly_raw.csv", index=False, encoding="utf-8-sig")

    rows = []
    for (origin, month), g in raw.groupby(["읍면동(출발)", "일자"]):
        group, zone = zone_of(origin)
        days = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
        in_suwon = g[g["시군구(도착)"] == "수원시"]
        rows.append({
            "출발동": origin, "그룹": group, "월": month, "일수": days,
            "전체": g["통행량"].sum() / days,
            "수원내": in_suwon["통행량"].sum() / days,
            "구역내부": in_suwon[in_suwon["읍면동(도착)"].isin(zone)]["통행량"].sum() / days,
            "동내부": in_suwon[in_suwon["읍면동(도착)"] == origin]["통행량"].sum() / days,
            "평균거리3km_가변": g[g["통행거리"] < 3000]["통행량"].sum() / days,
        })
    metrics = pd.DataFrame(rows).round(1)
    metrics.to_csv(PROCESSED / "od_monthly_metrics.csv", index=False, encoding="utf-8-sig")

    print(f"{len(files)}개 파일 병합 ({len(raw):,}행)")
    print(metrics.pivot(index="출발동", columns="월", values="구역내부").to_string())


if __name__ == "__main__":
    main()
