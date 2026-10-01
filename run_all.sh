#!/usr/bin/env bash
# 전체 분석 파이프라인: 원본(data/raw) -> 가공(data/processed) -> 그림(figures)
set -e
cd "$(dirname "$0")"
python run_all.py
