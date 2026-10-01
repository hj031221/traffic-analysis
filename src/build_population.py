"""
행정안전부 주민등록 인구통계(수원시 구·행정동, 월별) CSV를 long format으로 정리.

입력: data/raw/population/*.csv  (cp949, 열 이름 '2022년01월_총인구수' 형태)
출력: data/processed/population_suwon.csv  (코드, 지역, 월, 총인구수, 세대수)
"""

import io

import pandas as pd

from config import PROCESSED, RAW


def main():
    src = next((RAW / "population").glob("*.csv"))
    df = pd.read_csv(io.StringIO(src.read_bytes().decode("cp949")), thousands=",")

    long = df.melt(id_vars="행정구역", var_name="key", value_name="값")
    parts = long["key"].str.extract(r"(\d{4})년(\d{2})월_(.+)")
    long["월"] = parts[0] + "-" + parts[1]
    long["항목"] = parts[2]
    long["코드"] = long["행정구역"].str.extract(r"\((\d+)\)")[0]
    long["지역"] = (long["행정구역"].str.replace(r"\s*\(\d+\)", "", regex=True)
                    .str.replace("경기도 ", "").str.strip())
    long["값"] = pd.to_numeric(long["값"].astype(str).str.replace(",", ""), errors="coerce")

    out = (long[long["항목"].isin(["총인구수", "세대수"])]
           .pivot_table(index=["코드", "지역", "월"], columns="항목", values="값")
           .reset_index())
    out.columns.name = None
    out.to_csv(PROCESSED / "population_suwon.csv", index=False, encoding="utf-8-sig")
    print(f"{out['지역'].nunique()}개 지역 x {out['월'].nunique()}개월 -> population_suwon.csv")


if __name__ == "__main__":
    main()
