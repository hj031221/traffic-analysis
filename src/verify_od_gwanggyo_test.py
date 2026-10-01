"""
검증 테스트: 수원똑버스01(광교)이 교통카드 OD 데이터에 포함되는지 확인.

배경: 01번 똑버스는 2023-06부터 운행했지만 교통카드 데이터에는 2024-04부터 잡히기 시작함.
      2024-03 -> 2024-04 사이 광교 출발 통행이 비교군 대비 하루 ~200건 늘었다면
      똑버스 통행이 OD에 포함되기 시작했다는 증거로 본다.

처치군: 광교 구역 법정동(이의동=광교1동, 하동=광교2동, 원천동) 출발
        -> 광교 + 주변 동 11개 도착 (출발 3 x 도착 11 = 33쌍)
비교군: 장안구 정자동 출발
        -> 정자동 + 주변 동 11개 도착 (1 x 11 = 11쌍)
        (처치군과 도착지 범위를 같은 구조로 맞춰 공정하게 비교)

원천동은 광교1·2동이 아니라 원천동 행정동에 대응되므로 광교와 무관한 통행이 섞일 수 있음
-> 원천동 포함/제외 합계를 둘 다 출력한다.

날짜:
- 3월(포함 전): 2024-03-12, 13, 14 (화~목)
- 4월(포함 후): 2024-04-16, 17, 18 (화~목)

도착지 축소: 기준일(2024-03-12)을 11개 도착지 전부로 받은 뒤, 그룹별로 통행량 상위 도착 동을
누적 90% 이상이 될 때까지만 남기고 나머지 날짜는 그 동들만 받는다(처치군·비교군 같은 기준).
최종 집계도 모든 날짜에서 축소된 도착지 집합만 써서 날짜 간 범위를 일정하게 맞춘다.

stcis API는 짧은 시간에 수십 건 연속 호출하면 연결을 일시 차단하므로:
- OD 쌍 하나 받을 때마다 결과를 CSV에 저장 -> 재실행 시 이미 받은 쌍은 건너뜀
- requests.Session으로 연결 재사용, 호출 사이 3~5초 랜덤 대기
- 연결 실패가 계속되면 5분씩 쉬며 재시도
"""

import os
import random
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

TREATMENT_ORIGINS = {
    "4111710300": "이의동",
    "4111710400": "하동",
    "4111710200": "원천동",
}
TREATMENT_DESTS = {
    "4111710300": "이의동",
    "4111710400": "하동",
    "4111710200": "원천동",
    "4111710100": "매탄동",
    "4111710500": "영통동",
    "4111710700": "망포동",
    "4111514000": "우만동",
    "4111514100": "인계동",
    "4111113700": "연무동",
    "4111113800": "상광교동",
    "4111113900": "하광교동",
}
CONTROL_ORIGINS = {
    "4111113000": "정자동",
}
CONTROL_DESTS = {
    "4111113000": "정자동",
    "4111113300": "천천동",
    "4111113200": "율전동",
    "4111113100": "이목동",
    "4111112900": "파장동",
    "4111113500": "송죽동",
    "4111113600": "조원동",
    "4111113400": "영화동",
    "4111513800": "화서동",
    "4111313100": "서둔동",
    "4111313200": "구운동",
}

DATES_BEFORE = ["20240312", "20240313", "20240314"]
DATES_AFTER = ["20240416", "20240417", "20240418"]

SLEEP_RANGE = (3.0, 5.0)
BLOCK_WAIT_SEC = 300

BASE_DATE = "20240312"
CUM_SHARE = 0.90

PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
PAIRS_PATH = os.path.join(PROCESSED, "od_gwanggyo_pairs.csv")
SUMMARY_PATH = os.path.join(PROCESSED, "od_gwanggyo_test_result.csv")

session = requests.Session()
session.headers.update(HEADERS)


def quarterod(oprat_date: str, stg_emd: str, arr_emd: str) -> int:
    params = {
        "apikey": STCIS_KEY,
        "opratDate": oprat_date,
        "stgEmdCd": stg_emd,
        "arrEmdCd": arr_emd,
    }
    attempt = 0
    while True:
        try:
            r = session.get(
                "https://stcis.go.kr/openapi/quarterod.json",
                params=params,
                timeout=30,
            )
            r.encoding = "utf-8"
            data = r.json()
            time.sleep(random.uniform(*SLEEP_RANGE))
            if data.get("status") != "OK":
                return 0
            return sum(item["useStf"] for item in data["result"])
        except requests.exceptions.RequestException as e:
            attempt += 1
            wait = 2 ** attempt if attempt <= 3 else BLOCK_WAIT_SEC
            print(f"  재시도 {attempt} ({oprat_date} {stg_emd}->{arr_emd}): {type(e).__name__}. {wait}초 대기")
            time.sleep(wait)
            if attempt > 3:
                session.close()


def fetch(jobs, rows):
    print(f"남은 OD 쌍: {len(jobs)}개")
    for i, (date, period, group, o, o_nm, d, d_nm) in enumerate(jobs, 1):
        n = quarterod(date, o, d)
        rows.append({
            "날짜": date, "기간": period, "그룹": group,
            "출발코드": o, "출발동": o_nm, "도착코드": d, "도착동": d_nm, "이용인원": n,
        })
        pd.DataFrame(rows).to_csv(PAIRS_PATH, index=False, encoding="utf-8-sig")
        if i % 10 == 0 or i == len(jobs):
            print(f"  [{i}/{len(jobs)}] {date} {group} {o_nm}->{d_nm}")


def make_jobs(dates, groups, done):
    jobs = []
    for date in dates:
        period = "3월" if date in DATES_BEFORE else "4월"
        for group, origins, dests in groups:
            for o, o_nm in origins.items():
                for d, d_nm in dests.items():
                    if (date, o, d) not in done:
                        jobs.append((date, period, group, o, o_nm, d, d_nm))
    return jobs


def top_dests(df: pd.DataFrame, group: str, dests: dict) -> dict:
    """기준일 도착 동별 통행량 상위부터 누적 CUM_SHARE 이상이 될 때까지의 도착 동."""
    base = df[(df["날짜"] == BASE_DATE) & (df["그룹"] == group)]
    by_dest = base.groupby("도착코드")["이용인원"].sum().sort_values(ascending=False)
    cum = by_dest.cumsum() / by_dest.sum()
    n_keep = int((cum < CUM_SHARE).sum()) + 1
    keep = list(by_dest.index[:n_keep])

    table = pd.DataFrame({
        "도착동": [dests[c] for c in by_dest.index],
        "통행": by_dest.values,
        "비중%": (by_dest / by_dest.sum() * 100).round(1).values,
        "누적%": (cum * 100).round(1).values,
    })
    print(f"\n{group} 기준일({BASE_DATE}) 도착 동 비중 — 상위 {n_keep}개 유지(누적 {cum.iloc[n_keep - 1] * 100:.1f}%)")
    print(table.to_string(index=False))
    return {c: dests[c] for c in keep}


def main():
    if os.path.exists(PAIRS_PATH):
        rows = pd.read_csv(PAIRS_PATH, dtype={"날짜": str, "출발코드": str, "도착코드": str}).to_dict("records")
    else:
        rows = []
    done = {(r["날짜"], r["출발코드"], r["도착코드"]) for r in rows}

    full_groups = [
        ("처치군(광교)", TREATMENT_ORIGINS, TREATMENT_DESTS),
        ("비교군(정자동)", CONTROL_ORIGINS, CONTROL_DESTS),
    ]
    # 1) 기준일은 전체 도착지로 받기
    fetch(make_jobs([BASE_DATE], full_groups, done), rows)

    # 2) 기준일 비중으로 도착지 축소
    df = pd.DataFrame(rows)
    t_dests = top_dests(df, "처치군(광교)", TREATMENT_DESTS)
    c_dests = top_dests(df, "비교군(정자동)", CONTROL_DESTS)
    reduced_groups = [
        ("처치군(광교)", TREATMENT_ORIGINS, t_dests),
        ("비교군(정자동)", CONTROL_ORIGINS, c_dests),
    ]

    # 3) 나머지 날짜는 축소된 도착지만
    done = {(r["날짜"], r["출발코드"], r["도착코드"]) for r in rows}
    other_dates = [d for d in DATES_BEFORE + DATES_AFTER if d != BASE_DATE]
    fetch(make_jobs(other_dates, reduced_groups, done), rows)

    # 4) 집계: 모든 날짜에서 축소된 도착지만 사용
    df = pd.DataFrame(rows)
    keep_t = (df["그룹"] == "처치군(광교)") & df["도착코드"].isin(t_dests)
    keep_c = (df["그룹"] == "비교군(정자동)") & df["도착코드"].isin(c_dests)
    df = df[keep_t | keep_c]
    no_wc = df[~((df["그룹"] == "처치군(광교)") & (df["출발동"] == "원천동"))].copy()
    no_wc["그룹"] = no_wc["그룹"].replace({"처치군(광교)": "처치군(광교, 원천동 제외)"})
    daily = pd.concat([
        df.groupby(["날짜", "기간", "그룹"], as_index=False)["이용인원"].sum(),
        no_wc[no_wc["그룹"] != "비교군(정자동)"].groupby(["날짜", "기간", "그룹"], as_index=False)["이용인원"].sum(),
    ])
    daily.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")

    print()
    print(daily.pivot_table(index="날짜", columns="그룹", values="이용인원").to_string())

    pivot = daily.pivot_table(index="그룹", columns="기간", values="이용인원", aggfunc="mean")
    pivot["증감(건)"] = pivot["4월"] - pivot["3월"]
    pivot["증감률(%)"] = (pivot["4월"] / pivot["3월"] - 1) * 100
    print()
    print(pivot.round(1).to_string())

    ctrl = pivot.loc["비교군(정자동)"]
    print()
    for g in ["처치군(광교)", "처치군(광교, 원천동 제외)"]:
        t = pivot.loc[g]
        did_abs = t["증감(건)"] - ctrl["증감(건)"]
        # 비교군 증감률을 처치군 3월 수준에 적용했을 때 기대되는 증감 대비 초과분
        did_scaled = t["4월"] - t["3월"] * (ctrl["4월"] / ctrl["3월"])
        print(f"{g}: DiD(단순 차) = {did_abs:+.1f}건/일, 비교군 증감률 보정 초과분 = {did_scaled:+.1f}건/일")

    print()
    print(f"쌍별 원자료: {PAIRS_PATH}")
    print(f"일별 요약: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
