"""변경된 분석의 위험 지점에 대한 작은 회귀 검증. 네트워크 호출 없음."""
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_od_did import PAIR_KEYS, common_pairs, corrected_difference, denominator_metadata
from analysis_carbon_breakeven import breakeven
from merge_route_usage import deduplicate, strict_counts


class IntegrityTests(unittest.TestCase):
    def test_parse_failure_is_not_zero(self):
        for values in [[1, None], [1, "오류"], [1, -1], [1, 2.5]]:
            with self.assertRaises((ValueError, TypeError)):
                strict_counts(pd.Series(values))

    def test_conflicting_duplicate_is_rejected(self):
        d = pd.DataFrame({"노선": ["01", "01"], "날짜": ["2026-09-01"] * 2,
                          "시간대": [7, 7], "이용량": [10, 11]})
        with self.assertRaises(ValueError): deduplicate(d)
        d["이용량"] = 10
        self.assertEqual(len(deduplicate(d)), 1)

    def test_distance_boundary_does_not_drop_fixed_pair(self):
        key = dict(zip(PAIR_KEYS, ["경기도", "수원시", "오목천동", "경기도", "수원시", "오목천동"]))
        pre = pd.DataFrame([{**key, "통행거리": 2944, "통행량": 100}])
        post = pd.DataFrame([{**key, "통행거리": 3020, "통행량": 90},
                             {**key, "읍면동(도착)": "다른동", "통행거리": 1000, "통행량": 5}])
        common = common_pairs(pre, post)
        self.assertEqual(common.loc[common["통행거리_전"] < 3000, "통행량_후"].sum(), 90)
        self.assertEqual(len(common), 1)  # 미관측 쌍을 0으로 채우지 않음

    def test_missing_denominator_is_not_interpolated(self):
        s = pd.DataFrame({"노선": ["02"], "기간": ["2025-10"]})
        m = denominator_metadata(s, "02", "2025-12")
        self.assertIsNone(m["똑버스_표본일평균"])
        self.assertEqual(m["똑버스_관측일수"], 0)
        self.assertGreater(corrected_difference(100, 110, 100, 100), 0)

    def test_carbon_units_and_positive_inputs(self):
        base = breakeven("경유", 1, load=2.8)[2]
        self.assertAlmostEqual(breakeven("경유", 1, load=5.6)[2], base / 2)
        self.assertAlmostEqual(breakeven("경유", 1, ride=2, load=2.8)[2], base / 2)
        self.assertAlmostEqual(breakeven("경유", 1, deadhead=0)[2], base / 1.4)
        self.assertEqual(round(breakeven("경유", 1, deadhead=0)[2] * 100), 79)
        self.assertEqual(round(breakeven("전기", 1)[2] * 100), 42)
        with self.assertRaises(ValueError): breakeven("경유", 1, load=0)
        with self.assertRaises(ValueError): breakeven("경유", 1, deadhead=-1)


if __name__ == "__main__": unittest.main()
