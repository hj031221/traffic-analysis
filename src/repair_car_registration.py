"""
국토교통 통계누리 '자동차등록대수현황 시군구별' CSV 복원.

원본 CSV는 cp949 인코딩이고, 천 단위 쉼표가 따옴표 없이 들어가 있어
"151,200,545,..." 처럼 숫자 경계가 사라진다.
각 행은 [승용, 승합, 화물, 특수, 총계] x [관용, 자가용, 영업용, 계] = 20개 숫자이므로
아래 두 규칙을 모두 만족하는 분할을 탐색해 원래 숫자를 복원한다.
  1) 관용 + 자가용 + 영업용 = 계  (차종마다)
  2) 승용 + 승합 + 화물 + 특수 = 총계  (구분마다)
쉼표 뒤 조각은 반드시 3자리라는 성질로 후보를 좁히고, 해가 정확히 1개가 아니면 실패로 보고한다.

입력: data/raw/car_registration/*.csv
출력: data/processed/car_registration_sigungu.csv
"""

import csv

import pandas as pd

from config import PROCESSED, RAW

CATS = ["승용", "승합", "화물", "특수", "총계"]
SUBS = ["관용", "자가용", "영업용", "계"]


def solve(tokens):
    solutions = []

    def dfs(i, values):
        n = len(values)
        if n and n % 4 == 0:
            a, b, c, s = values[-4:]
            if a + b + c != s:
                return
        if n == 20:
            if i == len(tokens) and all(
                sum(values[c * 4 + k] for c in range(4)) == values[16 + k] for k in range(4)
            ):
                solutions.append(list(values))
            return
        remaining = 20 - n
        left = len(tokens) - i
        if left < remaining or left > remaining * 3:
            return
        head = tokens[i]
        if not head.isdigit() or len(head) > 3:
            return
        for k in range(1, 4):  # 숫자 하나는 최대 3조각 (999,999,999)
            if i + k > len(tokens):
                break
            if k > 1 and (len(tokens[i + k - 1]) != 3 or head == "0"):
                break
            values.append(int("".join(tokens[i:i + k])))
            dfs(i + k, values)
            values.pop()

    dfs(0, [])
    return solutions


def main():
    src = next((RAW / "car_registration").glob("*.csv"))
    lines = src.read_bytes().decode("cp949").splitlines()

    rows, failed = [], []
    for line in lines[2:]:  # 헤더 2줄
        parts = line.split(",")
        if not parts[0][:2] == "20":
            continue
        sols = solve(parts[3:])
        if len(sols) == 1:
            rows.append(parts[:3] + sols[0])
        else:
            failed.append((len(sols), line[:60]))

    header = ["월", "시도", "시군구"] + [f"{c}_{s}" for c in CATS for s in SUBS]
    out = PROCESSED / "car_registration_sigungu.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    print(f"복원 성공 {len(rows):,}행 / 실패 {len(failed)}행 -> {out.name}")
    for n, l in failed[:10]:
        print(f"  해 {n}개: {l}")


if __name__ == "__main__":
    main()
