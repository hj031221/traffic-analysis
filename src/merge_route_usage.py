"""
STCIS 웹 '노선별 이용량' 엑셀(data/raw/route_usage/*.xlsx)을 모두 읽어
long format(노선, 날짜, 요일, 시간대, 이용량)으로 합친다.

입력 파일 형식(시트 1개)
- 헤더: 노선, 기종점, 일, 합계, 6, 7, ..., 23 (6~23시 시간대별 이용량)
- '합계' 행은 제외
- 노선/기종점은 각 노선의 첫 행에만 있고 아래 행은 비어 있거나 0 -> forward fill
- '일' 형식: "2024-09-01(일)"

출력
- data/processed/route_usage.csv          : 노선·날짜·시간대별 이용량
- data/processed/route_usage_daily.csv    : 노선·날짜별 합계 (평일/공휴일 표시)
"""

import re

import pandas as pd

from config import HOLIDAYS, PROCESSED, RAW

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\((.)\)")


def parse_one_file(path):
    df = pd.read_excel(path, sheet_name=0, header=0)
    df = df[df["노선"].astype(str) != "합계"].copy()
    for col in ["노선", "기종점"]:
        df[col] = df[col].replace(0, pd.NA).ffill()

    parsed = df["일"].astype(str).str.extract(DATE_RE)
    df["날짜"], df["요일"] = parsed[0], parsed[1]
    df = df[df["날짜"].notna()]

    hour_cols = [c for c in df.columns if str(c).isdigit()]
    long_df = df.melt(id_vars=["노선", "기종점", "날짜", "요일"], value_vars=hour_cols,
                      var_name="시간대", value_name="이용량")
    long_df["시간대"] = long_df["시간대"].astype(int)
    long_df["이용량"] = pd.to_numeric(long_df["이용량"], errors="coerce").fillna(0).astype(int)
    return long_df


def main():
    files = sorted((RAW / "route_usage").glob("*.xlsx"))
    if not files:
        raise SystemExit("data/raw/route_usage/ 에 파일이 없습니다. README의 다운로드 방법을 참고하세요.")

    df = pd.concat([parse_one_file(f) for f in files], ignore_index=True)
    df["노선"] = df["노선"].str[-2:]  # '수원똑버스01' -> '01'
    df = df.drop_duplicates(["노선", "날짜", "시간대"]).sort_values(["노선", "날짜", "시간대"])
    df.to_csv(PROCESSED / "route_usage.csv", index=False, encoding="utf-8-sig")

    daily = df.groupby(["노선", "날짜", "요일"], as_index=False)["이용량"].sum()
    daily["주말"] = daily["요일"].isin(["토", "일"])
    daily["공휴일"] = daily["날짜"].isin(HOLIDAYS)
    daily["평일"] = ~daily["주말"] & ~daily["공휴일"]
    daily["기간"] = daily["날짜"].str[:7]
    daily.to_csv(PROCESSED / "route_usage_daily.csv", index=False, encoding="utf-8-sig")

    print(f"{len(files)}개 파일 -> {len(df):,}행, 노선별 날짜 수:")
    print(daily.groupby("노선")["날짜"].nunique().to_string())


if __name__ == "__main__":
    main()
