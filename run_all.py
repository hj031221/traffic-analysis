"""Windows/macOS/Linux 공통 재현 진입점. API 키나 네트워크 호출 불필요."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
STEPS = ["merge_route_usage", "repair_car_registration", "build_population", "build_od_monthly",
         "analysis_route_profiles", "analysis_od_validation", "analysis_od_did",
         "analysis_car_registration", "analysis_carbon_breakeven", "analysis_user_type",
         "analysis_quality", "make_figures"]


def main():
    for step in STEPS:
        print(f"실행: {step}", flush=True)
        subprocess.run([sys.executable, str(ROOT / "src" / f"{step}.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
