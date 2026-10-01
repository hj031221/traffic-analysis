"""
자동차 등록 데이터로 '자가용 이용 변화'를 볼 수 있는가?

수원시 4개 구의 승용 자가용 등록대수를 인구·세대수로 나눠 비교한다.
권선구(똑버스 02·03·04 운행)는 인구가 줄었는데 인구당 자가용이 크게 늘어,
등록대수가 '주민의 실제 이용'이 아니라 등록지(법인·리스 등)를 반영할 가능성을 보여준다.

입력: data/processed/car_registration_sigungu.csv, population_suwon.csv
출력: data/processed/car_per_capita_gu.csv
"""

import pandas as pd

from config import PROCESSED


def main():
    car = pd.read_csv(PROCESSED / "car_registration_sigungu.csv")
    car = car[car["시군구"].str.startswith("수원시 ")]
    pop = pd.read_csv(PROCESSED / "population_suwon.csv", dtype={"코드": str})
    gu = pop[pop["코드"].str.endswith("00000") & (pop["코드"] != "4111000000")]

    df = gu.merge(car[["월", "시군구", "승용_자가용"]], left_on=["월", "지역"],
                  right_on=["월", "시군구"]).drop(columns="시군구")
    df["인구천명당_자가용"] = (df["승용_자가용"] / df["총인구수"] * 1000).round(1)
    df["세대당_자가용"] = (df["승용_자가용"] / df["세대수"]).round(3)
    df.to_csv(PROCESSED / "car_per_capita_gu.csv", index=False, encoding="utf-8-sig")

    first, last = df["월"].min(), df["월"].max()
    a = df[df["월"] == first].set_index("지역")
    b = df[df["월"] == last].set_index("지역")
    out = pd.DataFrame({
        "인구변화(%)": ((b["총인구수"] / a["총인구수"] - 1) * 100).round(1),
        "자가용변화(%)": ((b["승용_자가용"] / a["승용_자가용"] - 1) * 100).round(1),
        f"인구천명당_{first}": a["인구천명당_자가용"],
        f"인구천명당_{last}": b["인구천명당_자가용"],
        "인구천명당변화(%)": ((b["인구천명당_자가용"] / a["인구천명당_자가용"] - 1) * 100).round(1),
    })
    print(out.to_string())


if __name__ == "__main__":
    main()
