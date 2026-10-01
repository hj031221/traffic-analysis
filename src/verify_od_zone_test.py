"""
검증 테스트: 수원똑버스02(평동.고색동) 개시 전후, 처치군/비교군 OD 총 이용인원 비교.

처치군: 02번 똑버스 구역 법정동(평동, 고색동, 오목천동) 내부끼리의 OD 합계
        -> {평동, 고색동, 오목천동} 3개 법정동의 모든 순서쌍(자기자신 포함, 3x3=9쌍)
비교군: 장안구 정자동 내부(자기자신) OD 합계
        -> 정자동 1개 법정동의 자기자신 쌍(1쌍)

날짜:
- 도입 전: 2024-09-10, 2024-09-11, 2024-09-12 (수원똑버스02 개시일 2024-10-08 약 4주 전, 화~목)
- 도입 후: 2024-11-12, 2024-11-13, 2024-11-14 (개시일 약 5주 후, 화~목)

각 날짜 x 그룹에 대해 모든 OD쌍의 useStf를 전부 더해 "하루 총 이용인원"을 구한다.

주의: stcis는 공식 문서상 호출 제한이 없다고 되어 있지만, 실제로는 짧은 시간에 수십 건을
연속 호출하면 stcis.go.kr(API 서버, www.stcis.go.kr과는 별도)이 TCP 연결 자체를 일정 시간
막아버리는 현상이 관찰됨(비공식 anti-abuse 추정). 호출 간 2초 간격을 두고, 이미 완료된
(날짜,그룹) 조합은 기존 결과 CSV에서 읽어 건너뛰어 재실행 시 중복 호출을 줄인다.
"""

import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
STCIS_KEY = os.environ["STCIS_API_KEY"]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

TREATMENT_DONGS = {
    "4111312700": "평동",
    "4111312800": "고색동",
    "4111312900": "오목천동",
}
CONTROL_DONGS = {
    "4111113000": "정자동",
}

DATES_BEFORE = ["20240910", "20240911", "20240912"]
DATES_AFTER = ["20241112", "20241113", "20241114"]

SLEEP_SEC = 2.0

OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "od_zone_test_result.csv"
)


def quarterod(oprat_date: str, stg_emd: str, arr_emd: str) -> int:
    params = {
        "apikey": STCIS_KEY,
        "opratDate": oprat_date,
        "stgEmdCd": stg_emd,
        "arrEmdCd": arr_emd,
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(
                "https://stcis.go.kr/openapi/quarterod.json",
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            r.encoding = "utf-8"
            data = r.json()
            time.sleep(SLEEP_SEC)
            if data.get("status") != "OK":
                return 0
            return sum(item["useStf"] for item in data["result"])
        except requests.exceptions.RequestException as e:
            last_err = e
            wait = 2 ** attempt
            print(f"  재시도 {attempt + 1}/4 ({oprat_date} {stg_emd}->{arr_emd}): {e}. {wait}초 후 재시도")
            time.sleep(wait)
    raise last_err


def zone_total(oprat_date: str, dong_codes: dict) -> int:
    codes = list(dong_codes.keys())
    total = 0
    for stg in codes:
        for arr in codes:
            total += quarterod(oprat_date, stg, arr)
    return total


def main():
    if os.path.exists(OUT_PATH):
        done_df = pd.read_csv(OUT_PATH, dtype={"날짜": str})
        rows = done_df.to_dict("records")
        done_pairs = {(r["날짜"], r["그룹"]) for r in rows}
    else:
        rows = []
        done_pairs = set()

    for date in DATES_BEFORE + DATES_AFTER:
        period = "도입전" if date in DATES_BEFORE else "도입후"

        if (date, "처치군(똑버스02 구역)") not in done_pairs:
            treatment_sum = zone_total(date, TREATMENT_DONGS)
            rows.append(
                {"날짜": date, "기간": period, "그룹": "처치군(똑버스02 구역)", "이용인원합계": treatment_sum}
            )
            pd.DataFrame(rows).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
        else:
            treatment_sum = next(r["이용인원합계"] for r in rows if r["날짜"] == date and r["그룹"] == "처치군(똑버스02 구역)")

        if (date, "비교군(정자동)") not in done_pairs:
            control_sum = zone_total(date, CONTROL_DONGS)
            rows.append(
                {"날짜": date, "기간": period, "그룹": "비교군(정자동)", "이용인원합계": control_sum}
            )
            pd.DataFrame(rows).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
        else:
            control_sum = next(r["이용인원합계"] for r in rows if r["날짜"] == date and r["그룹"] == "비교군(정자동)")

        print(f"{date} ({period}) 처치군={treatment_sum} 비교군={control_sum}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    pivot = df.pivot_table(index="그룹", columns="기간", values="이용인원합계", aggfunc="mean")
    pivot["증가율(%)"] = (pivot["도입후"] / pivot["도입전"] - 1) * 100
    print()
    print(pivot)
    print()
    print(f"결과 저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
