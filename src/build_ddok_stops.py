"""
수원 똑버스 01~04 노선의 등록 지점(기종점) 목록 + 좌표를 모아 data/processed/ddok_stops.csv로 저장한다.

주의: stcis "버스 노선별 경유정류장정보" API에는 똑버스 노선당 2개 지점(기점/종점 역할의
고정 앵커 포인트)만 등록되어 있고, 실제 DRT가 운행하며 들르는 중간 정류장들은 포함되어
있지 않다. 즉 이 CSV는 "노선이 지나는 정류장 네트워크"가 아니라 "각 노선의 서비스 거점
좌표" 정도로만 활용 가능하다.

파이프라인:
1. stcis 버스노선정보(busroute)로 routeNo -> routeId 조회
2. stcis 버스노선별경유정류장정보(busroutesttn)로 routeId -> 지점 목록(sttnId, sttnNm, emdCd 등) 조회
3. stcis 버스정류장정보(bussttn)로 emdCd 단위 정류장 목록을 받아 sttnId -> bimsId/sttnArsno 매핑
4. TAGO(getSttnNoList, cityCode=31010)에서 정류소명으로 후보를 검색하고,
   nodeid == "GGB" + bimsId 인 항목을 찾아 위도/경도 확보
"""

import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
STCIS_KEY = os.environ["STCIS_API_KEY"]
TAGO_KEY = os.environ["TAGO_API_KEY"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

SUWON_SD_CD = "41"
SUWON_TAGO_CITY_CODE = "31010"

DDOK_ROUTES = ["수원똑버스01", "수원똑버스02", "수원똑버스03", "수원똑버스04"]

OUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "ddok_stops.csv"
)


def stcis_get(service, **params):
    params["apikey"] = STCIS_KEY
    r = requests.get(
        f"https://stcis.go.kr/openapi/{service}.json",
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    r.encoding = "utf-8"
    return r.json()


def tago_get(operation, **params):
    params["serviceKey"] = TAGO_KEY
    params["_type"] = "json"
    r = requests.get(
        f"https://apis.data.go.kr/1613000/BusSttnInfoInqireService/{operation}",
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    r.encoding = "utf-8"
    return r.json()


def get_route_id(route_no: str) -> str:
    data = stcis_get("busroute", sdCd=SUWON_SD_CD, routeNo=route_no)
    return data["result"][0]["routeId"]


def get_route_stops(route_id: str) -> list[dict]:
    data = stcis_get("busroutesttn", sdCd=SUWON_SD_CD, routeId=route_id)
    return data.get("result", [])


def get_bims_lookup(emd_codes: set[str]) -> dict:
    lookup = {}
    for emd in emd_codes:
        data = stcis_get("bussttn", emdCd=emd)
        for item in data.get("result", []):
            lookup[item["sttnId"]] = item
    return lookup


def find_coords(sttn_nm: str, bims_id: str | None):
    if not bims_id:
        return None, None
    target_nodeid = "GGB" + bims_id
    data = tago_get(
        "getSttnNoList",
        cityCode=SUWON_TAGO_CITY_CODE,
        nodeNm=sttn_nm,
        numOfRows=50,
        pageNo=1,
    )
    items = data.get("response", {}).get("body", {}).get("items", {})
    item_list = items.get("item", []) if items else []
    if isinstance(item_list, dict):
        item_list = [item_list]
    for it in item_list:
        if it.get("nodeid") == target_nodeid:
            return it.get("gpslati"), it.get("gpslong")
    return None, None


def main():
    all_stops = []
    for route_no in DDOK_ROUTES:
        route_id = get_route_id(route_no)
        stops = get_route_stops(route_id)
        all_stops.extend(stops)

    emd_codes = {s["emdCd"] for s in all_stops}
    bims_lookup = get_bims_lookup(emd_codes)

    rows = []
    for s in all_stops:
        info = bims_lookup.get(s["sttnId"], {})
        bims_id = info.get("bimsId")
        lat, lon = find_coords(s["sttnNm"], bims_id)
        rows.append(
            {
                "노선": s["routeNo"],
                "정류장ID": s["sttnId"],
                "정류장명": s["sttnNm"],
                "위도": lat,
                "경도": lon,
                "법정동코드": s["emdCd"],
            }
        )

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUT_PATH} ({len(df)}행)")
    missing = df[df["위도"].isna()]
    if len(missing):
        print(f"좌표 매칭 실패: {len(missing)}건")
        print(missing[["노선", "정류장ID", "정류장명"]].to_string(index=False))


if __name__ == "__main__":
    main()
