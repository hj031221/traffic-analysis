"""O/D 탐색적 비교: 개인의 전환율이나 인과효과는 산출하지 않는다.

비교군 비율 변화로 보정한 일 통행량 차이와 수준 차분을 함께 저장한다.
월별 평균거리로 대상이 바뀌는 지표와 전후 공통 관측 쌍을 고정한 지표를
비교한다. 미관측 O/D 쌍을 0으로 간주하지 않고 포착률을 별도 기록한다.
"""
import calendar
import pandas as pd
from config import CONTROLS, PROCESSED, ZONES

SPECS = [("02", "2024-09", "2025-04"), ("02", "2024-09", "2025-05"),
         ("02", "2024-09", "2025-12"), ("03", "2024-09", "2025-12"),
         ("03", "2025-04", "2025-12"), ("03", "2025-05", "2025-12")]
PAIR_KEYS = ["시도(출발)", "시군구(출발)", "읍면동(출발)",
             "시도(도착)", "시군구(도착)", "읍면동(도착)"]


def days(month):
    return calendar.monthrange(int(month[:4]), int(month[5:]))[1]


def corrected_difference(t0, t1, c0, c1):
    if min(t0, c0) <= 0:
        raise ValueError("기준월 통행량은 양수여야 합니다.")
    return t1 - t0 * c1 / c0


def common_pairs(pre, post):
    return pre.merge(post, on=PAIR_KEYS, how="inner", suffixes=("_전", "_후"), validate="one_to_one")


def selected(frame, origins, metric, route):
    d = frame[frame["읍면동(출발)"].isin(origins)]
    if metric == "평균거리3km_가변":
        return d[d["통행거리"] < 3000]
    if metric == "전체":
        return d
    d = d[d["시군구(도착)"] == "수원시"]
    if metric == "수원내":
        return d
    if metric == "동내부" or route is None:
        return d[d["읍면동(출발)"] == d["읍면동(도착)"]]
    return d[d["읍면동(도착)"].isin(ZONES[route])]


def denominator_metadata(summary, route, post):
    s = summary[(summary["노선"] == route) & (summary["기간"] == post)]
    if s.empty:
        return {"똑버스_표본일평균": None, "똑버스_관측일수": 0,
                "똑버스_관측기간": "자료없음_보간안함"}
    r = s.iloc[0]
    return {"똑버스_표본일평균": float(r["일평균"]), "똑버스_관측일수": int(r["일수"]),
            "똑버스_관측기간": f"{r['관측시작']}~{r['관측끝']}"}


def make_row(route, pre, post, metric, control, t0, t1, c0, c1, metadata):
    return {"노선": route, "기준월": pre, "비교월": post, "지표": metric, "비교군구성": control,
            "처리군_전": t0, "처리군_후": t1, "비교군_전": c0, "비교군_후": c1,
            "비교군비율보정차_일": corrected_difference(t0, t1, c0, c1) if min(t0, c0) > 0 else None,
            "수준차분차_일": (t1 - t0) - (c1 - c0),
            "비교군변화율_pct": (c1 / c0 - 1) * 100 if c0 > 0 else None,
            "계산상태": "계산가능" if min(t0, c0) > 0 else "기준월대상통행0_비율보정불가",
            "5월포함": pre.endswith("-05") or post.endswith("-05"),
            "해석": "탐색적비교_전환율아님", **metadata}


def main():
    raw = pd.read_csv(PROCESSED / "od_monthly_raw.csv")
    summary = pd.read_csv(PROCESSED / "route_period_summary.csv", dtype={"노선": str})
    rows, coverage, crossings = [], [], []
    control_sets = {"전체비교군": CONTROLS}
    control_sets.update({f"{x}제외": [d for d in CONTROLS if d != x] for x in CONTROLS})
    for route, before, after in SPECS:
        pre, post = raw[raw["일자"] == before], raw[raw["일자"] == after]
        needed = set(ZONES[route] + CONTROLS)
        for month, frame in [(before, pre), (after, post)]:
            missing = needed - set(frame["읍면동(출발)"])
            if missing:
                raise ValueError(f"{month} 출발동 자료 누락: {missing}")
        common = common_pairs(pre, post)
        metadata = denominator_metadata(summary, route, after)
        for control_name, controls in control_sets.items():
            for metric in ["구역내부", "동내부", "평균거리3km_가변", "수원내", "전체"]:
                vals = [selected(f, o, metric, rt)["통행량"].sum() / days(m)
                        for f, m in [(pre, before), (post, after)]
                        for o, rt in [(ZONES[route], route), (controls, None)]]
                t0, c0, t1, c1 = vals
                rows.append(make_row(route, before, after, metric, control_name, t0, t1, c0, c1, metadata))
            for km in [2, 3, 4]:
                fixed = common[common["통행거리_전"] < km * 1000]
                vals = [fixed[fixed["읍면동(출발)"].isin(o)][f"통행량_{suffix}"].sum() / days(m)
                        for m, suffix in [(before, "전"), (after, "후")]
                        for o in [ZONES[route], controls]]
                t0, c0, t1, c1 = vals
                rows.append(make_row(route, before, after, f"평균거리{km}km_공통고정",
                                     control_name, t0, t1, c0, c1, metadata))
        for group, origins in [(route, ZONES[route]), ("비교군", CONTROLS)]:
            for km in [2, 3, 4]:
                p0 = pre[pre["읍면동(출발)"].isin(origins) & (pre["통행거리"] < km * 1000)]
                fixed = common[common["읍면동(출발)"].isin(origins) & (common["통행거리_전"] < km * 1000)]
                coverage.append({"노선": route, "기준월": before, "비교월": after, "그룹": group,
                                 "기준거리km": km, "기준월_대상쌍": len(p0), "공통관측_대상쌍": len(fixed),
                                 "후월미관측_쌍": len(p0) - len(fixed),
                                 "기준월통행_포착비율": (fixed["통행량_전"].sum() / p0["통행량"].sum()
                                                       if p0["통행량"].sum() > 0 else None),
                                 "포착률상태": "계산가능" if p0["통행량"].sum() > 0 else "기준월대상없음"})
        changed = common[((common["통행거리_전"] < 3000) != (common["통행거리_후"] < 3000))
                         & common["읍면동(출발)"].isin(needed)].copy()
        changed["분석노선"], changed["기준월"], changed["비교월"] = route, before, after
        crossings.extend(changed.to_dict("records"))
    result = pd.DataFrame(rows)
    result.to_csv(PROCESSED / "did_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage).to_csv(PROCESSED / "od_pair_coverage.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(crossings).to_csv(PROCESSED / "od_distance_crossings.csv", index=False, encoding="utf-8-sig")
    display = result[(result["노선"] == "02") & (result["기준월"] == "2024-09")
                     & (result["비교월"] == "2025-12") & (result["비교군구성"] == "전체비교군")]
    print(display[["지표", "비교군비율보정차_일", "수준차분차_일", "똑버스_관측기간"]].to_string(index=False))
    print("탐색적 통행 비교이며 수단전환율·인과효과로 해석하지 않습니다.")


if __name__ == "__main__":
    main()
