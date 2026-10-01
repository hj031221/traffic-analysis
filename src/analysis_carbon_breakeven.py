"""
조건부 탄소 손익분기: DRT 직결 여객·km 중 자가용 대체 비중의 필요치.

자가용 대체율(s)은 현재 공공 데이터로 측정할 수 없다(데이터 사각지대). 대신 s의 '필요 최소치'
(손익분기 대체율 s*)는 차량·운행 특성만으로 계산할 수 있다.

승객 1명이 출발-도착 직접 경로 1km를 이동할 때
  똑버스 배출   E_drt = EF_차량 x 우회계수 x (1 + 공차비율) / 평균 재차인원
  자가용 회피분 E_car = EF_승용 / 승용 재차인원 x 라이드계수
직결 여객·km 중 비율 s가 자가용 통행을 대체했다면(기타 수단의 한계 회피배출은 0으로 가정)
  순감축 = s x E_car - E_drt   ->   s* = E_drt / E_car
s* > 100% 이면 위 가정에서 직결 여객km 전부가 일반 자가용을 대체해도 순감축이 안 된다.

라이드계수: 보호자가 차로 데려다주고 빈 차로 돌아오는 통행(라이드)을 대체하면 회피 거리가 2배.

근거 (괄호 안은 출처, '가정'은 공개 자료가 없어 범위로 둔 값)
- 경유 2.600 kgCO2/L = 20.090 tC/TJ x 44/12 x 35.3 MJ/L (에너지공단 EG-TIPS 국가 고유 배출계수·순발열량)
- 경유 실연비 8~11 km/L, 전기 전비 0.20~0.30 kWh/km는 일반 승합차 시나리오 가정(실제 차종 실측 아님)
- 전력 소비단 0.4173 kgCO2eq/kWh는 2023년도 통계 기반 공식 계수(2025-12 공표)
- 승용차 0.141~0.20 kgCO2/km는 가정
- 거리 가중 유상운행 재차인원 2.43~3.24명은 가정. 선행 시간대별 재차인원과 정의가 다르므로 실측으로 표기하지 않음
- 승용 재차인원 1.0~1.2명, 우회계수 1.1~1.4, 공차비율 0.2~0.6 (가정)

공차비율 = 공차거리/승객 탑승 운행거리. 재차인원은 공차를 제외한 탑승 운행거리로
가중한 값이므로 공차 보정과 중복되지 않는다. 우회계수는 탑승 여객·km/직결 여객·km.
승용 재차인원도 차량거리로 가중한다. 통행별 거리와 이용빈도가 다르면 s를 사람 비율로
바꿀 수 없다. 경유는 연소 CO2, 전기는 소비단 CO2eq를 사용한 운영 배출 근사 비교이다.
경유 연소의 CH4·N2O, 차량 제조·연료 상류는 제외한다.
보호자 라이드 2배는 보호자의 다른 용무와 결합하지 않은 전용 왕복 대체를 가정한다.

출력: data/processed/carbon_breakeven_scenarios.csv, carbon_breakeven_curve.csv
"""

import numpy as np
import pandas as pd

from config import PROCESSED

DIESEL_KG_PER_L = 20.090 * 44 / 12 * 35.3 / 1000   # = 2.600
GRID_KG_PER_KWH = 0.4173  # kgCO2eq/kWh, 2023년도 소비단 계수, 2025-12 공표

# (낙관, 중앙, 비관) - 낙관 = 똑버스에 유리한 값
P = {
    "diesel_kmL":   (11.0, 9.5, 8.0),
    "ev_kWh_km":    (0.20, 0.25, 0.30),
    "car_kg_km":    (0.20, 0.17, 0.141),
    "car_occ":      (1.0, 1.1, 1.2),
    "drt_load":     (3.24, 2.80, 2.43),
    "detour":       (1.10, 1.25, 1.40),
    "deadhead":     (0.20, 0.40, 0.60),
}
SCEN = {"낙관": 0, "중앙": 1, "비관": 2}


def ef_vehicle(fuel, i):
    if fuel not in ["경유", "전기"]:
        raise ValueError(f"알 수 없는 연료: {fuel}")
    if fuel == "경유":
        return DIESEL_KG_PER_L / P["diesel_kmL"][i]
    return P["ev_kWh_km"][i] * GRID_KG_PER_KWH


def breakeven(fuel, i, ride=1.0, load=None, deadhead=None):
    load = P["drt_load"][i] if load is None else load
    deadhead = P["deadhead"][i] if deadhead is None else deadhead
    if load <= 0 or ride <= 0 or deadhead < 0:
        raise ValueError("재차인원·라이드 계수는 양수, 공차 비율은 0 이상이어야 합니다.")
    e_drt = ef_vehicle(fuel, i) * P["detour"][i] * (1 + deadhead) / load
    e_car = P["car_kg_km"][i] / P["car_occ"][i] * ride
    return e_drt, e_car, e_drt / e_car


def main():
    rows = []
    for fuel in ["경유", "전기"]:
        for ride_name, ride in [("일반 자가용 대체", 1.0), ("라이드(보호자 왕복) 대체", 2.0)]:
            for s, i in SCEN.items():
                e_drt, e_car, sstar = breakeven(fuel, i, ride)
                rows.append({"차량": fuel, "대체 통행": ride_name, "시나리오": s,
                             "똑버스_kg/인km": round(e_drt, 3), "자가용회피_kg/인km": round(e_car, 3),
                             "손익분기_자가용대체율(%)": round(sstar * 100),
                             "대체율정의": "직결여객km중자가용대체비중_이용자비율아님",
                             "공차율정의": "공차거리/탑승운행거리",
                             "재차인원정의": "공차제외_거리평균_시나리오가정",
                             "전력환산계수_kgCO2eqkWh": GRID_KG_PER_KWH,
                             "주의": "경유연소계수와공식전력계수외운행변수는가정_실제노선성과아님"})
    scen = pd.DataFrame(rows)
    scen.to_csv(PROCESSED / "carbon_breakeven_scenarios.csv", index=False, encoding="utf-8-sig")

    no_deadhead = []
    for fuel in ["경유", "전기"]:
        for s, i in SCEN.items():
            e_drt, e_car, sstar = breakeven(fuel, i, deadhead=0)
            no_deadhead.append({"차량": fuel, "시나리오": s, "공차거리/탑승운행거리": 0,
                                "손익분기_pct": sstar * 100,
                                "주의": "공차0가정_실제전체배출실측아님_나머지조건동일"})
    pd.DataFrame(no_deadhead).to_csv(PROCESSED / "carbon_no_deadhead.csv", index=False, encoding="utf-8-sig")

    # 재차인원에 따른 손익분기 곡선 (중앙값 선 + 낙관~비관 범위)
    curve = []
    for load in np.round(np.arange(1.0, 6.01, 0.1), 2):
        for fuel in ["경유", "전기"]:
            vals = [breakeven(fuel, i, 1.0, load)[2] * 100 for i in range(3)]
            curve.append({"재차인원": load, "차량": fuel, "낙관": round(vals[0], 1),
                          "중앙": round(vals[1], 1), "비관": round(vals[2], 1),
                          "중앙_공차0": breakeven(fuel, 1, load=load, deadhead=0)[2] * 100})
    pd.DataFrame(curve).to_csv(PROCESSED / "carbon_breakeven_curve.csv", index=False, encoding="utf-8-sig")

    sensitivity = []
    for name, values in P.items():
        for index, value in enumerate(values):
            for fuel in ["경유", "전기"]:
                P[name] = (value, value, value)
                sstar = breakeven(fuel, 1)[2] * 100
                sensitivity.append({"변수": name, "선택값": value, "수준": index,
                                    "차량": fuel, "손익분기_pct": sstar})
        P[name] = values
    pd.DataFrame(sensitivity).to_csv(PROCESSED / "carbon_parameter_sensitivity.csv", index=False, encoding="utf-8-sig")
    parameters = []
    units = {"diesel_kmL": "km/L", "ev_kWh_km": "kWh/km", "car_kg_km": "kgCO2/차량km",
             "car_occ": "거리평균 명", "drt_load": "공차제외 거리평균 명",
             "detour": "탑승여객km/직결여객km", "deadhead": "공차거리/탑승운행거리"}
    for name, values in P.items():
        parameters.append({"변수": name, "낙관": values[0], "중앙": values[1], "비관": values[2],
                           "종류": "시나리오가정_노선실측아님", "단위": units[name], "출처": "분석자 시나리오"})
    parameters.extend([
        {"변수": "grid_kg_kWh", "낙관": GRID_KG_PER_KWH, "중앙": GRID_KG_PER_KWH,
         "비관": GRID_KG_PER_KWH, "종류": "공식_2023년도소비단_2025년12월공표",
         "단위": "kgCO2eq/kWh", "출처": "https://tips.energy.or.kr/carbon/Ggas_tatistics03.do"},
        {"변수": "diesel_kg_L", "낙관": DIESEL_KG_PER_L, "중앙": DIESEL_KG_PER_L,
         "비관": DIESEL_KG_PER_L, "종류": "공개 연소계수 환산", "단위": "kgCO2/L",
         "출처": "https://tips.energy.or.kr/carbon/Ggas_tatistics03.do"},
    ])
    pd.DataFrame(parameters).to_csv(PROCESSED / "carbon_parameters.csv", index=False, encoding="utf-8-sig")

    print(f"경유 배출계수 {DIESEL_KG_PER_L:.3f} kgCO2/L")
    print(scen.pivot_table(index=["차량", "대체 통행"], columns="시나리오",
                           values="손익분기_자가용대체율(%)")[["낙관", "중앙", "비관"]].to_string())


if __name__ == "__main__":
    main()
