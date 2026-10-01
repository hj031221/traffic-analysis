#!/usr/bin/env bash
# 전체 분석 파이프라인: 원본(data/raw) -> 가공(data/processed) -> 그림(figures)
set -e
cd "$(dirname "$0")/src"
python merge_route_usage.py
python repair_car_registration.py
python build_population.py
python build_od_monthly.py
python analysis_route_profiles.py
python analysis_od_validation.py
python analysis_od_did.py
python analysis_car_registration.py
python analysis_carbon_breakeven.py
python make_figures.py
