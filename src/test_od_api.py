"""
15분단위OD API 테스트 스크립트 (대량 수집 아님 — 확인용)

확인된 사항:
1. 지역 단위: stgEmdCd/arrEmdCd 둘 다 10자리 읍면동 코드 필수 -> 읍면동 단위까지 세분화됨 (확인 완료)
2. 과거 데이터 범위: 수원시 권선구 평동(4111312700) -> 고색동(4111312800) 쌍으로 테스트
   - 2023-05-01: 데이터 있음 (20건)
   - 2022-06-15: 데이터 있음 (31건)
   - 2021-06-15: 데이터 있음 (31건)
   - 2021-01-01: 데이터 있음 (6건)
   - 2020-09-01: NOT_FOUND
   - 2020-06-15: NOT_FOUND
   - 2019-01-01: NOT_FOUND
   => 데이터는 대략 2020년 하반기~2021년 초 사이부터 제공되는 것으로 보임.
      공모전에서 쓸 2023-06-07(똑버스01 개시일) 전후 데이터는 문제없이 확보 가능.
3. 중요: requests로 호출 시 User-Agent 헤더 없으면 서버가 응답을 주지 않고 타임아웃됨
   (간단한 봇 차단으로 추정). 반드시 브라우저 User-Agent를 헤더에 포함할 것.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["STCIS_API_KEY"]
BASE = "https://stcis.go.kr/openapi"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def call(service, **params):
    params["apikey"] = API_KEY
    r = requests.get(f"{BASE}/{service}.json", params=params, headers=HEADERS, timeout=30)
    r.encoding = "utf-8"
    return r.json()


if __name__ == "__main__":
    import json

    data = call(
        "quarterod",
        opratDate="20230501",
        stgEmdCd="4111312700",
        arrEmdCd="4111312800",
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))
