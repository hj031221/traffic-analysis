"""
탄소 손익분기 분석: 똑버스가 탄소를 줄이려면 이용자 중 몇 %가 자가용에서 와야 하는가?

자가용 대체율(s)은 현재 공공 데이터로 측정할 수 없다(데이터 사각지대). 대신 s의 '필요 최소치'
(손익분기 대체율 s*)는 차량·운행 특성만으로 계산할 수 있다.

승객 1명이 직선거리 1km를 이동할 때
  똑버스 배출   E_drt = EF_차량 x 우회계수 x (1 + 공차비율) / 평균 재차인원
  자가용 회피분 E_car = EF_승용 / 승용 재차인원 x 라이드계수
똑버스 이용자 중 비율 s만 자가용에서 왔다면(나머지는 기존 버스·도보·신규 이동 -> 회피 배출 0)
  순감축 = s x E_car - E_drt   ->   s* = E_drt / E_car
s* > 100% 이면 이용자 전원이 자가용에서 와도 배출이 늘어난다.

라이드계수: 보호자가 차로 데려다주고 빈 차로 돌아오는 통행(라이드)을 대체하면 회피 거리가 2배.

근거 (괄호 안은 출처, '가정'은 공개 자료가 없어 범위로 둔 값)
- 경유 2.600 kgCO2/L = 20.090 tC/TJ x 44/12 x 35.3 MJ/L (에너지공단 EG-TIPS 국가 고유 배출계수·순발열량)
- 스타리아 디젤 2.2 공인 복합연비 10.3~12.3 km/L -> 도심 수요응답 운행을 감안해 8~11 km/L (가정)
- 전기 승합: 0.20~0.30 kWh/km (가정) x 전력배출계수 0.4173 tCO2eq/MWh (2023년 공표, 에너지신문)
- 승용차 141.3 g/km (2020 판매차 실제 평균, 정책브리핑) -> 실주행 차이를 감안해 0.141~0.20 kg/km (가정)
- 똑버스 평균 재차인원 2.43~3.24명 (수원시정연구원 2024, 광교)
- 승용 재차인원 1.0~1.2명, 우회계수 1.1~1.4, 공차비율 0.2~0.6 (가정)

출력: data/processed/carbon_breakeven_scenarios.csv, carbon_breakeven_curve.csv
"""

import numpy as np
import pandas as pd

from config import PROCESSED

DIESEL_KG_PER_L = 20.090 * 44 / 12 * 35.3 / 1000   # = 2.600
GRID_KG_PER_KWH = 0.4173

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
    if fuel == "경유":
        return DIESEL_KG_PER_L / P["diesel_kmL"][i]
    return P["ev_kWh_km"][i] * GRID_KG_PER_KWH


def breakeven(fuel, i, ride=1.0, load=None):
    load = P["drt_load"][i] if load is None else load
    e_drt = ef_vehicle(fuel, i) * P["detour"][i] * (1 + P["deadhead"][i]) / load
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
                             "손익분기_자가용대체율(%)": round(sstar * 100)})
    scen = pd.DataFrame(rows)
    scen.to_csv(PROCESSED / "carbon_breakeven_scenarios.csv", index=False, encoding="utf-8-sig")

    # 재차인원에 따른 손익분기 곡선 (중앙값 선 + 낙관~비관 범위)
    curve = []
    for load in np.round(np.arange(1.0, 6.01, 0.1), 2):
        for fuel in ["경유", "전기"]:
            vals = [breakeven(fuel, i, 1.0, load)[2] * 100 for i in range(3)]
            curve.append({"재차인원": load, "차량": fuel, "낙관": round(vals[0], 1),
                          "중앙": round(vals[1], 1), "비관": round(vals[2], 1)})
    pd.DataFrame(curve).to_csv(PROCESSED / "carbon_breakeven_curve.csv", index=False, encoding="utf-8-sig")

    print(f"경유 배출계수 {DIESEL_KG_PER_L:.3f} kgCO2/L")
    print(scen.pivot_table(index=["차량", "대체 통행"], columns="시나리오",
                           values="손익분기_자가용대체율(%)")[["낙관", "중앙", "비관"]].to_string())


if __name__ == "__main__":
    main()
