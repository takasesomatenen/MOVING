# -*- coding: utf-8 -*-
"""design/spec.json の整合を検算する（ネット不要）。

    python design/check_spec.py

寸法を触ったあとに走らせると、面積・屋根高・軒の出の効き・敷地内への収まり・
開口の位置・太陽の座標変換がすべて辻褄が合っているかを確かめられる。
"""

import json
import math
import os
import sys

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec.json")
FAILED = []


def check(cond, msg):
    print(("  OK  " if cond else "  NG  ") + msg)
    if not cond:
        FAILED.append(msg)


def note(msg):
    print("       " + msg)


def main():
    with open(SPEC, encoding="utf-8") as fh:
        s = json.load(fh)
    hut, site, deck, fd, shed = s["hut"], s["site"], s["deck"], s["foundation"], s["shed"]
    ov, pitch = hut["overhang"], hut["roof_pitch"]

    print("── 寸法 ──")
    check(abs((hut["x1"] - hut["x0"]) - hut["span_x"]) < 1e-9, f'桁行 {hut["span_x"]} m')
    check(abs((hut["y1"] - hut["y0"]) - hut["span_y"]) < 1e-9, f'梁間 {hut["span_y"]} m')
    check(abs(hut["span_x"] * hut["span_y"] - hut["area_m2"]) < 0.01,
          f'延べ面積 {hut["span_x"] * hut["span_y"]:.2f} ＝ {hut["area_m2"]}㎡')
    check(abs(hut["span_x"] / 0.91 - 8) < 1e-6 and abs(hut["span_y"] / 0.91 - 6) < 1e-6,
          "910mmグリッドに整合（8P × 6P）")
    check(hut["area_m2"] <= 200, "延べ200㎡以下＝都市計画区域外なら確認申請不要の新3号に収まる")
    check(abs(site["width_x"] * site["depth_y"] - site["area_m2"]) < 0.01, f'敷地 {site["area_m2"]}㎡')

    print("── 屋根 ──")
    ridge = hut["eave_z_south"] + hut["span_y"] * pitch
    check(abs(ridge - hut["ridge_z_north_wall"]) < 1e-3, f"北軒高 Z+{ridge:.3f}")
    zs = hut["eave_z_south"] - ov["south"] * pitch
    zn = ridge + ov["north"] * pitch
    check(abs(zs - hut["roof_edge_z_south"]) < 1e-3, f"南軒先 Z+{zs:.3f}")
    check(abs(zn - hut["roof_edge_z_north"]) < 1e-3, f"北軒先 Z+{zn:.3f}")
    check(abs(math.degrees(math.atan(pitch)) - hut["roof_pitch_deg"]) < 0.02,
          f'勾配 {hut["roof_pitch_deg"]}°')

    print("── 軒の出の効き ──")
    head = max(o["z1"] for o in hut["openings"] if o["wall"] == "south")
    for lab, alt in (("夏至 南中", 76.9), ("冬至 南中", 30.0)):
        z_shadow = zs - ov["south"] * math.tan(math.radians(alt))
        state = "南壁を全面日陰" if z_shadow <= hut["fl"] else f"窓上端から {head - z_shadow:.2f}m 下まで影"
        note(f"{lab} {alt}° → 影の下端 Z{z_shadow:+.3f} … {state}")
    check(zs - ov["south"] * math.tan(math.radians(76.9)) <= hut["fl"], "夏至南中に南壁が全面日陰になる")
    check(zs > head, f'南軒先 Z+{zs:.3f} が窓上端 Z+{head:.2f} より高い（眺望が軒で切れない）')

    print("── 基礎と床下 ──")
    check(len(fd["grid_x"]) * len(fd["grid_y"]) == fd["count"],
          f'独立基礎 {len(fd["grid_x"])}×{len(fd["grid_y"])} ＝ {fd["count"]}基')
    check(fd["embed_depth"] > site["frost_depth_m"],
          f'根入れ {fd["embed_depth"]}m ＞ 凍結深度 {site["frost_depth_m"]}m')
    clearance = hut["fl"] - site["slope"] * hut["y0"]
    check(clearance >= site["design_snow_m"],
          f'床下クリアランス {clearance:.2f}m ≧ 設計積雪 {site["design_snow_m"]}m')

    print("── 開口 ──")
    for o in hut["openings"]:
        lo, hi = (hut["x0"], hut["x1"]) if o["wall"] in ("south", "north") else (hut["y0"], hut["y1"])
        check(lo <= o["u0"] < o["u1"] <= hi, f'{o["id"]} が {o["wall"]} 面の内側')
        y = {"south": hut["y0"], "north": hut["y1"]}.get(o["wall"], o["u1"])
        top = hut["eave_z_south"] + (y - hut["y0"]) * pitch
        check(hut["fl"] <= o["z0"] < o["z1"] <= top + 1e-9, f'{o["id"]} が床〜屋根下端に収まる')

    print("── 敷地への収まり ──")
    check(hut["x0"] - ov["west"] >= 0 and hut["x1"] + ov["east"] <= site["width_x"],
          "主屋（軒の出込み）が敷地の東西内")
    check(deck["y0"] >= 0 and hut["y1"] + ov["north"] <= site["depth_y"], "主屋＋デッキが敷地の南北内")
    check(abs(deck["y1"] - hut["y0"]) < 1e-9, "デッキ北端が主屋の南壁に接続")
    check(abs((deck["x1"] - deck["x0"]) * (deck["y1"] - deck["y0"]) - deck["area_m2"]) < 0.02,
          f'デッキ {deck["area_m2"]}㎡')
    check(shed["x0"] >= 0 and shed["x1"] <= site["width_x"]
          and shed["y1"] + shed["overhang"] <= site["depth_y"], "別棟が敷地内")
    check(max(x for x, _, _ in s["vegetation"]["trees"]) <= site["width_x"]
          and max(y for _, y, _ in s["vegetation"]["trees"]) <= site["depth_y"], "樹木がすべて敷地内")

    print("── 太陽 ──")
    worst = 0.0
    for p in s["sun_presets"]:
        az, alt = math.radians(p["azimuth_deg"]), math.radians(p["altitude_deg"])
        rx, rz = math.radians(90 - p["altitude_deg"]), math.radians(180 - p["azimuth_deg"])
        got = (-math.sin(rx) * math.sin(rz), math.sin(rx) * math.cos(rz), -math.cos(rx))
        want = (-math.sin(az) * math.cos(alt), -math.cos(az) * math.cos(alt), -math.sin(alt))
        worst = max(worst, max(abs(a - b) for a, b in zip(got, want)))
    check(worst < 1e-9, f"Blenderのeuler変換が全{len(s['sun_presets'])}プリセットで方位・高度に一致")

    print("── カメラ ──")
    for c in s["cameras"]:
        check(any(p["id"] == c["sun"] for p in s["sun_presets"]),
              f'{c["id"]} の太陽プリセット <{c["sun"]}> が存在する')

    print()
    if FAILED:
        print(f"NG {len(FAILED)} 件: " + " / ".join(FAILED))
        return 1
    print("すべて整合。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
