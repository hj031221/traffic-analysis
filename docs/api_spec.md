# STCIS Open API 사양 정리

출처: https://www.stcis.go.kr/wps/openapi/devsvc/openApiDevList.do (로그인 후 각 API 상세 페이지)

공통사항:
- Base URL: `https://stcis.go.kr/openapi/`
- 모든 요청에 `apikey` 필수
- 응답은 JSON. 공통 응답 필드: `count`(건수), `status`(`OK`/`NOT_FOUND`/`ERROR`)
- 에러 시 `error.level`, `error.code`, `error.text` 반환 (예: `INVALID_KEY`, `PARAM_REQUIRED`, `INVALID_TYPE`, `INVALID_RANGE`)
- **주의**: Python `requests`로 호출 시 `User-Agent` 헤더가 없으면 서버가 응답하지 않고 타임아웃됨 (간단한 봇 차단으로 추정). 반드시 브라우저 User-Agent 헤더를 포함해서 요청할 것 (`src/test_od_api.py` 참고).

---

## 1. 지역코드 (areacode)

```
GET https://stcis.go.kr/openapi/areacode.json?apikey={key}&sdCd={시도코드}&sggCd={시군구코드}
```

| 파라미터 | 필수/선택 | 설명 | 유효값 |
|---|---|---|---|
| apikey | 필수 | 발급받은 API key | - |
| sdCd | 선택 | 시/도 코드 | 2자리 |
| sggCd | 선택 | 시/군/구 코드 | 5자리 |

- 파라미터를 지정하지 않으면 시/도 목록 반환
- `sdCd` 지정 시 해당 시/도의 시/군/구 목록 반환 (`sggCd`, `sggNm`)
- `sggCd` 지정 시 해당 시/군/구의 읍/면/동 목록 반환 (`emdCd`, `emdNm`)

응답 필드: `sdCd`, `sdNm`, `sggCd`, `sggNm`, `emdCd`, `emdNm` (요청 파라미터 지정 단계에 따라 응답 필드가 달라짐)

---

## 2. 버스 정류장정보 (bussttn)

```
GET https://stcis.go.kr/openapi/bussttn.json?apikey={key}&sdCd={시도코드}&sggCd={시군구코드}&emdCd={읍면동코드}&sttnArsno={정류장ARS번호}
```

| 파라미터 | 필수/선택 | 설명 | 유효값 |
|---|---|---|---|
| apikey | 필수 | API key | - |
| sdCd/sggCd/emdCd | 이 중 하나는 필수 | 지역 범위 | sdCd 2자리 / sggCd 5자리 / emdCd 10자리 |
| sttnArsno | 선택 | 정류장 ARS번호 | - |

응답 필드: `sttnId`(정류장ID), `bimsId`, `sttnNm`(정류장명), `sttnArsno`, `sdCd`, `sggCd`, `emdCd`

**주의: 위도/경도 필드가 응답에 없음.** 좌표가 필요하면 별도 API(국가대중교통정보센터 TAGO 등) 또는 BIMS/정류장 좌표 데이터를 따로 구해야 함. (4번 작업 전에 반드시 확인 필요 — 아래 "진행 전 확인사항" 참고)

---

## 3. 버스 노선별 경유정류장정보 (busroutesttn)

```
GET https://stcis.go.kr/openapi/busroutesttn.json?apikey={key}&sdCd={시도코드}&sggCd={시군구코드}&emdCd={읍면동코드}&routeId={노선ID}
```

| 파라미터 | 필수/선택 | 설명 | 유효값 |
|---|---|---|---|
| apikey | 필수 | API key | - |
| sdCd/sggCd/emdCd | 이 중 하나는 필수 | 지역 범위 | sdCd 2자리 / sggCd 5자리 / emdCd 10자리 |
| routeId | 필수 | 노선ID | - |

응답 필드: `routeId`, `routeNo`(노선번호), `routeNm`(노선명), `sttnSeq`(정류장 순번), `sttnId`, `sttnNm`, `sdCd`, `sggCd`, `emdCd`, `sdNm`, `sggNm`, `emdNm`

**주의: 여기도 위도/경도 필드 없음.** `routeId`가 먼저 필요하므로, 버스 노선정보 API(4번, 이번 공모전에서 안 쓰기로 한 것)로 노선 목록을 먼저 조회해 똑버스 노선의 routeId를 찾아야 함.

---

## 4. 15분단위OD (quarterod) — 가장 중요

```
GET https://stcis.go.kr/openapi/quarterod.json?apikey={key}&opratDate={운행일자}&stgEmdCd={출발 읍면동코드}&arrEmdCd={도착 읍면동코드}
```

| 파라미터 | 필수/선택 | 설명 | 유효값 |
|---|---|---|---|
| apikey | 필수 | API key | - |
| opratDate | 필수 | 운행일자 | 8자리 (YYYYMMDD) |
| stgEmdCd | 필수 | 출발지 읍/면/동 코드 | 10자리 |
| arrEmdCd | 필수 | 도착지 읍/면/동 코드 | 10자리 |

응답 필드: `opratDate`, `stgSdCd/stgSdNm`(출발 시도), `stgSggCd/stgSggNm`(출발 시군구), `stgEmdCd/stgEmdNm`(출발 읍면동), `arrSdCd/arrSdNm`, `arrSggCd/arrSggNm`, `arrEmdCd/arrEmdNm`, `tzon`(시간대), `quater`(15분단위), `useStf`(이용인원수), `useTm`(평균 통행시간)

**핵심 포인트:**
- `stgEmdCd`와 `arrEmdCd`가 둘 다 **필수**이며 10자리 읍/면/동 코드다. 즉 지역 단위는 **읍면동까지 내려감** — 시군구 단위로만 집계된 API가 아니라, 특정 출발 읍면동 ↔ 특정 도착 읍면동 "OD 쌍"을 지정해서 조회하는 구조.
- 이는 대량 수집 시 "모든 읍면동 쌍의 조합"을 순회해야 함을 의미 — 수원시만 해도 읍면동이 수십 개이므로 쌍의 수가 많아질 수 있음 (조합 수 계획 필요).

**실제 테스트 결과 (2026-10-01 확인, 권선구 평동↔고색동 쌍):**
- 지역 단위: 읍면동 단위 확인됨 (응답에 `stgEmdNm`/`arrEmdNm` 등 읍면동명이 정확히 매핑되어 옴)
- 과거 데이터 범위:
  - 2023-05-01 → 데이터 있음 (20건)
  - 2022-06-15 → 데이터 있음 (31건)
  - 2021-06-15 → 데이터 있음 (31건)
  - 2021-01-01 → 데이터 있음 (6건)
  - 2020-09-01 → `NOT_FOUND`
  - 2020-06-15 → `NOT_FOUND`
  - 2019-01-01 → `NOT_FOUND`
  - **결론: 대략 2020년 하반기~2021년 초 사이부터 데이터 제공.** 수원똑버스01 개시일(2023-06-07) 전후 데이터는 문제없이 확보 가능.
  - (참고: 이 결과는 특정 읍면동 쌍 기준이라 다른 지역 쌍에서는 경계가 약간 다를 수 있음 — 트래픽이 적은 쌍은 NOT_FOUND가 "데이터 없음"이 아니라 "그날 해당 쌍의 통행이 0건"일 수도 있음)

---

## 진행 전 확인사항 (요약)

1. **좌표(위도/경도) 미제공**: 정류장정보/노선별경유정류장정보 API 모두 위경도 필드가 없음 → 아래 TAGO 연동으로 해결.
2. **OD 읍면동 단위**: 15분단위OD는 읍면동 단위 OD 쌍 조회이므로, 대량 수집 시 수원시 읍면동 목록 x 읍면동 목록 조합 설계가 필요함.

---

## 5. TAGO (국토교통부 버스정류소정보) — stcis 좌표 보완용

출처: https://www.data.go.kr/data/15098534/openapi.do (공공데이터포털, 별도 인증키 필요, `.env`의 `TAGO_API_KEY`)

Base URL: `https://apis.data.go.kr/1613000/BusSttnInfoInqireService`

주의: 이 API도 `User-Agent` 헤더 없이 호출하면 응답이 느리거나 실패할 수 있음 — stcis와 동일하게 브라우저 User-Agent 헤더 포함 권장.

### 5-1. 정류소번호 목록조회 (getSttnNoList)

```
GET https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnNoList
    ?serviceKey={key}&_type=json&cityCode={도시코드}&nodeNm={정류소명 검색어}&numOfRows=&pageNo=
```

| 파라미터 | 필수/선택 | 설명 |
|---|---|---|
| serviceKey | 필수 | 공공데이터포털 인증키 |
| cityCode | 필수 | TAGO 도시코드 (수원시 = `31010`) |
| nodeNm | 선택 | 정류소명 검색어 (부분일치) |
| numOfRows / pageNo | 선택 | 페이징 |

응답 필드: `nodeid`(정류소ID), `nodenm`(정류소명), `nodeno`(정류소번호=ARS번호), `gpslati`(위도), `gpslong`(경도)

### 5-2. 도시코드 목록조회 (getCtyCodeList)

경기도 시군별 코드 목록. 확인 결과 **수원시 = `31010`**.

### stcis ↔ TAGO 매칭 방법 (검증 완료)

stcis `버스정류장정보` API가 주는 `bimsId`와 TAGO의 `nodeid`는 아래 관계로 연결된다 (경기도 기준):

```
TAGO nodeid = "GGB" + stcis bimsId
```

실제 검증 (수원시 장안구 "교육청사거리" 정류장):

| stcis (bussttn) | TAGO (getSttnNoList) |
|---|---|
| `bimsId`: `200000191`, `sttnArsno`: `01176` | `nodeid`: `GGB200000191`, `nodeno`: `1176` |
| `bimsId`: `200000083`, `sttnArsno`: `01174` | `nodeid`: `GGB200000083`, `nodeno`: `1174` |

즉 `sttnArsno`(앞의 0 제거) == `nodeno`, `bimsId` == `nodeid`에서 `GGB` 제외 부분. 두 값 모두 일치하므로 교차검증 가능.

**권장 매칭 절차** (ddok_stops.csv 생성용):
1. stcis `버스 노선별 경유정류장정보`로 똑버스 노선의 정류장 목록(`sttnId`, `sttnNm`) 확보
2. stcis `버스 정류장정보`(`emdCd` 또는 `sttnArsno` 단위 조회)로 각 정류장의 `bimsId`, `sttnArsno` 확보
3. TAGO `getSttnNoList`를 `cityCode=31010` + `nodeNm={sttnNm}`으로 호출해 후보 목록을 받고, `nodeid == "GGB" + bimsId`인 항목을 정확히 매칭해 `gpslati`/`gpslong` 획득
   (이름 검색만으로는 동명 정류장이 여러 개 나올 수 있어 `bimsId` 매칭으로 명확히 특정해야 함)
