"""원자료 목록·검증 결과·실행 환경을 기록한다. 수집 날짜는 추측하지 않는다."""
from hashlib import sha256
from importlib.metadata import version
import json
import platform

import pandas as pd

from config import PROCESSED, RAW, ROOT


def main():
    manifest = [{"파일": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                 "sha256": sha256(p.read_bytes()).hexdigest(), "수집시각": "미기록"}
                for p in sorted(RAW.rglob("*")) if p.is_file() and p.suffix.lower() in [".csv", ".xlsx"]]
    pd.DataFrame(manifest).to_csv(PROCESSED / "source_manifest.csv", index=False, encoding="utf-8-sig")
    d = pd.read_csv(PROCESSED / "route_usage_daily.csv", dtype={"노선": str})
    h = pd.read_csv(PROCESSED / "route_usage.csv", dtype={"노선": str})
    r = pd.read_csv(PROCESSED / "od_monthly_raw.csv")
    from analysis_od_did import PAIR_KEYS
    from merge_route_usage import strict_counts
    strict_counts(h["이용량"])
    if h.duplicated(["노선", "날짜", "시간대"]).any() or r.duplicated(["일자"] + PAIR_KEYS).any():
        raise ValueError("최종 데이터에 중복 키가 있습니다.")
    check = h.groupby(["노선", "날짜"])["이용량"].sum().rename("hourly").to_frame()
    check = check.join(d.set_index(["노선", "날짜"])["이용량"], how="outer", validate="one_to_one")
    if check.isna().any().any() or not check["hourly"].eq(check["이용량"]).all():
        raise ValueError("시간대와 일별 합계 불일치 또는 일자 누락")
    metrics = {"route_files": len(list((RAW / "route_usage").glob("*.xlsx"))),
               "od_files": len(list((RAW / "od_monthly").glob("*.xlsx"))),
               "route_days": len(d), "hourly_rows": len(h), "od_rows": len(r),
               "duplicate_route_keys": 0, "duplicate_od_keys": 0, "daily_sum_mismatch": 0,
               "python": platform.python_version(),
               "packages": {p: version(p) for p in ["pandas", "numpy", "openpyxl", "matplotlib"]}}
    (PROCESSED / "quality_checks.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
