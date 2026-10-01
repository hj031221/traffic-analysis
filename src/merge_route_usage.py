"""
data/raw/route_usage/ 안의 월별 "노선별 이용량" 엑셀 파일들을 모두 읽어
long format(노선, 날짜, 요일, 시간대, 이용량)으로 합쳐 data/processed/route_usage.csv로 저장한다.

입력 파일 형식(시트 1개):
- 1행(헤더): 노선, 기종점, 일, 합계, 6, 7, ..., 23 (6~23시 시간대별 이용량)
- 2행: "일" 컬럼이 "합계"인 전체 합계 행 -> 제외
- 노선/기종점은 각 노선의 첫 행에만 있고 아래는 비어있음 -> forward fill
- "일" 컬럼 형식: "2024-09-01(일)" (날짜 + 괄호 안 요일)
"""

import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "route_usage"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "route_usage.csv"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\((.)\)")


def parse_one_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, header=0)

    df["노선"] = df["노선"].ffill()
    df["기종점"] = df["기종점"].ffill()

    # 전체 합계 행 제외
    df = df[df["일"].astype(str) != "합계"].copy()

    parsed = df["일"].astype(str).str.extract(DATE_RE)
    df["날짜"] = parsed[0]
    df["요일"] = parsed[1]
    df = df[df["날짜"].notna()].copy()

    hour_cols = [c for c in df.columns if str(c).isdigit()]

    long_df = df.melt(
        id_vars=["노선", "날짜", "요일"],
        value_vars=hour_cols,
        var_name="시간대",
        value_name="이용량",
    )
    long_df["이용량"] = pd.to_numeric(long_df["이용량"], errors="coerce").fillna(0).astype(int)
    long_df["시간대"] = long_df["시간대"].astype(int)

    return long_df[["노선", "날짜", "요일", "시간대", "이용량"]]


def main():
    files = sorted(RAW_DIR.glob("*.xlsx"))
    if not files:
        print(f"{RAW_DIR}에 엑셀 파일이 없습니다.")
        return

    frames = []
    for f in files:
        print(f"읽는 중: {f.name}")
        frames.append(parse_one_file(f))

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["노선", "날짜", "시간대"]).reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUT_PATH} ({len(merged)}행)")


if __name__ == "__main__":
    main()
