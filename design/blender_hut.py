"""北軽井沢 セルフビルド小屋 ― CG設計ベースのマッシングを Blender 上に生成する。

使い方:
    blender --python design/blender_hut.py
    blender --background --python design/blender_hut.py -- --render out/

寸法はすべて design/spec.json が単一の情報源。座標系は右手系メートル、
原点=敷地南西隅のGL±0、+X=東 / +Y=真北 / +Z=上（Blender標準と一致）。
"""

import json
import math
import os
import sys

import bpy  # noqa: F401  (Blender 内でのみ解決する)
from mathutils import Vector

SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec.json")


# ---------------------------------------------------------------- 下ごしらえ

def load_spec(path=SPEC_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def wipe_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def link(obj, col):
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def hex_to_rgba(srgb, alpha=1.0):
    srgb = srgb.lstrip("#")
    rgb = [int(srgb[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    # sRGB -> linear
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return (*lin, alpha)


def material(name, srgb="#888888", roughness=0.8, metallic=0.0, transmission=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_rgba(srgb)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    for key in ("Transmission Weight", "Transmission"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = transmission
            break
    if transmission > 0:
        mat.blend_method = "BLEND"
    return mat


def build_materials(spec):
    mats = {}
    for key, m in spec["materials"].items():
        mats[key] = material(
            key,
            srgb=m.get("srgb", "#888888"),
            roughness=m.get("roughness", 0.8),
            metallic=m.get("metallic", 0.0),
            transmission=m.get("transmission", 0.0),
        )
    mats["snow"] = material("snow", "#e9eef1", 0.55)
    mats["foliage"] = material("foliage", "#4a5c33", 0.90)
    mats["trunk"] = material("trunk", "#4a3a2c", 0.90)
    return mats


# ---------------------------------------------------------------- ジオメトリ

def mesh_from(name, verts, faces, mat=None, col=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([Vector(v) for v in verts], [], faces)
    me.validate()
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if col:
        link(obj, col)
    return obj


def box(name, x0, y0, z0, x1, y1, z1, mat=None, col=None):
    """軸に沿った直方体。座標は絶対値で与える。"""
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_from(name, v, f, mat, col)


def cylinder(name, x, y, z0, z1, radius, mat=None, col=None, segments=16):
    verts, faces = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((x + radius * math.cos(a), y + radius * math.sin(a), z0))
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((x + radius * math.cos(a), y + radius * math.sin(a), z1))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, j + segments, i + segments))
    faces.append(tuple(range(segments)))
    faces.append(tuple(range(2 * segments - 1, segments - 1, -1)))
    return mesh_from(name, verts, faces, mat, col)


def cone(name, x, y, z0, z1, radius, mat=None, col=None, segments=12):
    verts = [(x, y, z1)]
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((x + radius * math.cos(a), y + radius * math.sin(a), z0))
    faces = [(0, i + 1, (i + 1) % segments + 1) for i in range(segments)]
    faces.append(tuple(range(1, segments + 1)))
    return mesh_from(name, verts, faces, mat, col)


def slab(name, x0, y0, x1, y1, z, thickness, mat=None, col=None):
    return box(name, x0, y0, z - thickness, x1, y1, z, mat, col)


# ---------------------------------------------------------------- 敷地

def ground_z(spec, y):
    return spec["site"]["slope"] * y


def build_terrain(spec, mats, col, divisions=40):
    """北→南に 5% 下る地形。敷地の外周 6m まで延長して描く。"""
    site = spec["site"]
    pad = 6.0
    x0, x1 = -pad, site["width_x"] + pad
    y0, y1 = -pad, site["depth_y"] + pad
    verts, faces = [], []
    for iy in range(divisions + 1):
        y = y0 + (y1 - y0) * iy / divisions
        for ix in range(divisions + 1):
            x = x0 + (x1 - x0) * ix / divisions
            verts.append((x, y, ground_z(spec, y)))
    stride = divisions + 1
    for iy in range(divisions):
        for ix in range(divisions):
            a = iy * stride + ix
            faces.append((a, a + 1, a + stride + 1, a + stride))
    return mesh_from("terrain", verts, faces, mats["terrain"], col)


def build_site_boundary(spec, mats, col):
    """敷地境界を細い立ち上がりで表示（CG上の基準線）。"""
    site = spec["site"]
    w, d, t = site["width_x"], site["depth_y"], 0.06
    objs = []
    for name, (x0, y0, x1, y1) in {
        "boundary_S": (0, 0, w, t),
        "boundary_N": (0, d - t, w, d),
        "boundary_W": (0, 0, t, d),
        "boundary_E": (w - t, 0, w, d),
    }.items():
        ym = (y0 + y1) / 2
        objs.append(box(name, x0, y0, ground_z(spec, ym) - 0.05,
                        x1, y1, ground_z(spec, ym) + 0.25, mats["concrete"], col))
    return objs


def build_road(spec, mats, col):
    site = spec["site"]
    d, rw = site["depth_y"], site["road"]["width"]
    return slab("road", -3.0, d, site["width_x"] + 3.0, d + rw,
                ground_z(spec, d) + 0.02, 0.10, mats["gravel"], col)


# ---------------------------------------------------------------- 主屋

def wall_panels(name, wall, const, u0, u1, z_bottom, z_top, openings, thickness, mat, col):
    """開口を避けて壁を分割生成する。

    wall が 'south'/'north' なら const は y 座標、u は x。
    'east'/'west' なら const は x 座標、u は y。
    """
    horizontal = wall in ("south", "north")
    segs = []
    ops = sorted([o for o in openings if o["wall"] == wall], key=lambda o: o["u0"])

    cursor = u0
    for o in ops:
        if o["u0"] > cursor:
            segs.append((cursor, o["u0"], z_bottom, z_top))       # 開口の脇（袖壁）
        if o["z0"] > z_bottom:
            segs.append((o["u0"], o["u1"], z_bottom, o["z0"]))    # 開口下（腰壁）
        if o["z1"] < z_top:
            segs.append((o["u0"], o["u1"], o["z1"], z_top))       # 開口上（垂れ壁）
        cursor = max(cursor, o["u1"])
    if cursor < u1:
        segs.append((cursor, u1, z_bottom, z_top))

    made = []
    for i, (a, b, zb, zt) in enumerate(segs):
        if b - a < 1e-4 or zt - zb < 1e-4:
            continue
        if horizontal:
            made.append(box(f"{name}_{i}", a, const, zb, b, const + thickness, zt, mat, col))
        else:
            made.append(box(f"{name}_{i}", const, a, zb, const + thickness, b, zt, mat, col))
    return made


def roof_z(hut, y):
    """棟方向の任意 y における屋根下端の高さ。"""
    return hut["eave_z_south"] + (y - hut["y0"]) * hut["roof_pitch"]


def build_hut(spec, mats, col):
    hut = spec["hut"]
    t = 0.14  # 壁厚（構造+仕上げの見えがかり）
    fl = hut["fl"]
    x0, y0, x1, y1 = hut["x0"], hut["y0"], hut["x1"], hut["y1"]

    # 床
    box("hut_floor", x0, y0, fl - 0.25, x1, y1, fl, mats["floor_int"], col)

    ops = hut["openings"]
    # 南北の壁は屋根勾配に合わせて頂部が変わるので、上限を屋根下端に合わせる
    wall_panels("wall_south", "south", y0, x0, x1, fl, roof_z(hut, y0), ops, t, mats["wall_ext"], col)
    wall_panels("wall_north", "north", y1 - t, x0, x1, fl, roof_z(hut, y1), ops, t, mats["wall_ext"], col)

    # 東西の壁は台形。矩形パネルで近似したのち、頂部の三角部分を足す
    for wall, const in (("east", x1 - t), ("west", x0)):
        wall_panels(f"wall_{wall}", wall, const, y0, y1, fl, roof_z(hut, y0), ops, t, mats["wall_ext"], col)
        zs, zn = roof_z(hut, y0), roof_z(hut, y1)
        v = [(const, y0, zs), (const, y1, zs), (const, y1, zn),
             (const + t, y0, zs), (const + t, y1, zs), (const + t, y1, zn)]
        mesh_from(f"wall_{wall}_gable", v,
                  [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)],
                  mats["wall_ext"], col)

    # 屋根（片流れ・軒の出あり）
    ov = hut["overhang"]
    rx0, rx1 = x0 - ov["west"], x1 + ov["east"]
    ry0, ry1 = y0 - ov["south"], y1 + ov["north"]
    zs, zn = roof_z(hut, ry0), roof_z(hut, ry1)
    th = 0.22  # 屋根の見えがかり厚（登り梁+断熱+野地+葺材）
    v = [(rx0, ry0, zs), (rx1, ry0, zs), (rx1, ry1, zn), (rx0, ry1, zn),
         (rx0, ry0, zs + th), (rx1, ry0, zs + th), (rx1, ry1, zn + th), (rx0, ry1, zn + th)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh_from("roof", v, f, mats["roof"], col)

    # 雪止め（南軒先から 0.9m 上がった位置に1段）
    ysnow = ry0 + 0.9
    box("snow_guard", rx0, ysnow, roof_z(hut, ysnow) + th, rx1, ysnow + 0.05,
        roof_z(hut, ysnow) + th + 0.08, mats["sash_alu"], col)

    # 開口のガラスとサッシ枠
    for o in ops:
        glass = mats["glass"]
        frame = mats["sash_wood"] if "木製" in o["kind"] else mats["sash_alu"]
        if o["wall"] in ("south", "north"):
            yc = y0 + t / 2 if o["wall"] == "south" else y1 - t / 2
            box(f"glass_{o['id']}", o["u0"] + 0.06, yc - 0.01, o["z0"] + 0.06,
                o["u1"] - 0.06, yc + 0.01, o["z1"] - 0.06, glass, col)
            box(f"frame_{o['id']}", o["u0"], yc - 0.04, o["z0"],
                o["u1"], yc + 0.04, o["z0"] + 0.06, frame, col)
        else:
            xc = x0 + t / 2 if o["wall"] == "west" else x1 - t / 2
            box(f"glass_{o['id']}", xc - 0.01, o["u0"] + 0.06, o["z0"] + 0.06,
                xc + 0.01, o["u1"] - 0.06, o["z1"] - 0.06, glass, col)
            box(f"frame_{o['id']}", xc - 0.04, o["u0"], o["z0"],
                xc + 0.04, o["u1"], o["z0"] + 0.06, frame, col)

    # 薪ストーブと煙突
    st = hut["stove"]
    box("stove", st["x"] - 0.30, st["y"] - 0.25, fl, st["x"] + 0.30, st["y"] + 0.25, fl + 0.75,
        mats["wall_ext"], col)
    cylinder("flue", st["x"], st["y"], fl + 0.75, st["flue_top_z"], st["flue_d"] / 2,
             mats["sash_alu"], col)

    # 中古の陶器洗面ボウル＋古材カウンター
    wb = hut["washbasin"]
    box("washbasin_counter", wb["x0"], wb["y0"], fl + 0.78, wb["x1"], wb["y1"], fl + 0.83,
        mats["floor_int"], col)
    cylinder("washbasin_bowl", (wb["x0"] + wb["x1"]) / 2, (wb["y0"] + wb["y1"]) / 2,
             fl + 0.83, fl + 0.98, 0.21, mats["wall_int"], col)


def build_deck(spec, mats, col):
    dk = spec["deck"]
    slab("deck", dk["x0"], dk["y0"], dk["x1"], dk["y1"], dk["z"], dk["thickness"], mats["deck"], col)
    # デッキ束
    nx, ny = 4, 3
    for i in range(nx):
        for j in range(ny):
            x = dk["x0"] + (dk["x1"] - dk["x0"]) * i / (nx - 1)
            y = dk["y0"] + (dk["y1"] - dk["y0"]) * j / (ny - 1)
            x = min(x, dk["x1"] - 0.1)
            y = min(y, dk["y1"] - 0.1)
            box(f"deck_pier_{i}_{j}", x, y, ground_z(spec, y), x + 0.10, y + 0.10,
                dk["z"] - dk["thickness"], mats["deck"], col)


def build_foundation(spec, mats, col):
    fd = spec["foundation"]
    top = spec["hut"]["fl"] - fd["top_offset_below_fl"]
    n = 0
    for x in fd["grid_x"]:
        for y in fd["grid_y"]:
            cylinder(f"pier_{n}", x, y, ground_z(spec, y) - fd["embed_depth"], top, 0.15,
                     mats["concrete"], col)
            n += 1
    return n


def build_shed(spec, mats, col):
    sh = spec["shed"]
    fl, ov, t = sh["fl"], sh["overhang"], 0.10
    x0, y0, x1, y1 = sh["x0"], sh["y0"], sh["x1"], sh["y1"]
    box("shed_floor", x0, y0, fl - 0.15, x1, y1, fl, mats["deck"], col)

    def zr(y):
        return sh["eave_z_south"] + (y - y0) * sh["roof_pitch"]

    box("shed_wall_N", x0, y1 - t, fl, x1, y1, zr(y1), mats["wall_ext"], col)
    for wall, const in (("E", x1 - t), ("W", x0)):
        v = [(const, y0, fl), (const, y1, fl), (const, y1, zr(y1)), (const, y0, zr(y0)),
             (const + t, y0, fl), (const + t, y1, fl), (const + t, y1, zr(y1)), (const + t, y0, zr(y0))]
        mesh_from(f"shed_wall_{wall}", v,
                  [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
                  mats["wall_ext"], col)
    # 南面は薪の出し入れのため開放
    rx0, rx1, ry0, ry1 = x0 - ov, x1 + ov, y0 - ov, y1 + ov
    zs, zn = zr(ry0), zr(ry1)
    v = [(rx0, ry0, zs), (rx1, ry0, zs), (rx1, ry1, zn), (rx0, ry1, zn),
         (rx0, ry0, zs + 0.12), (rx1, ry0, zs + 0.12), (rx1, ry1, zn + 0.12), (rx0, ry1, zn + 0.12)]
    mesh_from("shed_roof", v,
              [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)],
              mats["roof"], col)


def build_hardscape(spec, mats, col):
    hs = spec["hardscape"]
    p = hs["parking"]
    ym = (p["y0"] + p["y1"]) / 2
    slab("parking", p["x0"], p["y0"], p["x1"], p["y1"], ground_z(spec, ym) + 0.03, 0.10,
         mats["gravel"], col)

    ap = hs["approach"]
    half = ap["width"] / 2
    pts = ap["polyline"]
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        ym = (ay + by) / 2
        z = ground_z(spec, ym) + 0.03
        if abs(ax - bx) < 1e-6:      # 南北の直線
            slab(f"approach_{i}", ax - half, min(ay, by), ax + half, max(ay, by), z, 0.08,
                 mats["gravel"], col)
        else:                         # 東西の直線
            slab(f"approach_{i}", min(ax, bx), ay - half, max(ax, bx), ay + half, z, 0.08,
                 mats["gravel"], col)

    # 軒先直下の雨落ち
    hut, ov = spec["hut"], spec["hut"]["overhang"]
    w = hs["drip_strip"]["width"]
    rx0, rx1 = hut["x0"] - ov["west"], hut["x1"] + ov["east"]
    ry0, ry1 = hut["y0"] - ov["south"], hut["y1"] + ov["north"]
    for name, (x0, y0, x1, y1) in {
        "drip_S": (rx0 - w, ry0 - w, rx1 + w, ry0),
        "drip_N": (rx0 - w, ry1, rx1 + w, ry1 + w),
        "drip_W": (rx0 - w, ry0, rx0, ry1),
        "drip_E": (rx1, ry0, rx1 + w, ry1),
    }.items():
        ym = (y0 + y1) / 2
        slab(name, x0, y0, x1, y1, ground_z(spec, ym) + 0.02, 0.06, mats["gravel"], col)


def build_vegetation(spec, mats, col, winter=False):
    """カラマツのプレースホルダ。winter=True で落葉させる（幹だけ残す）。"""
    for i, (x, y, h) in enumerate(spec["vegetation"]["trees"]):
        gz = ground_z(spec, y)
        r = 0.125 + (h - 12.0) * 0.02
        cylinder(f"trunk_{i}", x, y, gz, gz + h * 0.35, r, mats["trunk"], col, segments=8)
        if not winter:
            cone(f"crown_{i}", x, y, gz + h * 0.30, gz + h, h * 0.16, mats["foliage"], col)


# ---------------------------------------------------------------- 光とカメラ

def set_sun(spec, preset_id):
    preset = next(p for p in spec["sun_presets"] if p["id"] == preset_id)
    az, alt = preset["azimuth_deg"], preset["altitude_deg"]
    name = "sun"
    if name in bpy.data.objects:
        sun = bpy.data.objects[name]
    else:
        data = bpy.data.lights.new(name, type="SUN")
        sun = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(sun)
    sun.data.angle = math.radians(0.53)
    sun.data.energy = 3.0 + 2.0 * math.sin(math.radians(max(alt, 0)))
    # +Y=北・方位角は北から時計回り。導出は README 参照
    sun.rotation_euler = (math.radians(90.0 - alt), 0.0, math.radians(180.0 - az))
    return sun, preset


def build_cameras(spec, col):
    made = []
    for c in spec["cameras"]:
        data = bpy.data.cameras.new(c["id"])
        data.lens = c["lens"]
        cam = bpy.data.objects.new(c["id"], data)
        bpy.context.scene.collection.objects.link(cam)
        cam.location = Vector(c["loc"])
        target = bpy.data.objects.new(f"{c['id']}_target", None)
        target.location = Vector(c["target"])
        bpy.context.scene.collection.objects.link(target)
        con = cam.constraints.new("TRACK_TO")
        con.target = target
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        link(cam, col)
        link(target, col)
        made.append((cam, c))
    return made


def build_view_proxy(spec, mats, col):
    """浅間山のプロキシ。実距離17.4kmだと扱いにくいので3km地点に高さを合わせて置く。"""
    v = spec["view"]
    proxy_dist = 3000.0
    az = math.radians(v["azimuth_deg"])
    x = spec["site"]["width_x"] / 2 + proxy_dist * math.sin(az)
    y = spec["site"]["depth_y"] / 2 + proxy_dist * math.cos(az)
    h = proxy_dist * math.tan(math.radians(v["apparent_altitude_deg"]))
    return cone("asama_proxy", x, y, 0.0, h, h * 2.4, mats["terrain"], col, segments=24)


# ---------------------------------------------------------------- 実行

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    render_dir = argv[0] if argv else None
    winter = "--winter" in argv

    spec = load_spec()
    wipe_scene()
    mats = build_materials(spec)

    site_col = collection("SITE")
    hut_col = collection("HUT")
    shed_col = collection("SHED")
    land_col = collection("LANDSCAPE")
    cam_col = collection("CAMERAS")

    build_terrain(spec, mats, site_col)
    build_site_boundary(spec, mats, site_col)
    build_road(spec, mats, site_col)
    build_hardscape(spec, mats, site_col)
    piers = build_foundation(spec, mats, hut_col)
    build_hut(spec, mats, hut_col)
    build_deck(spec, mats, hut_col)
    build_shed(spec, mats, shed_col)
    build_vegetation(spec, mats, land_col, winter=winter)
    build_view_proxy(spec, mats, land_col)

    cams = build_cameras(spec, cam_col)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1250

    hut = spec["hut"]
    print("─" * 62)
    print(f"敷地 {spec['site']['width_x']}×{spec['site']['depth_y']}m = {spec['site']['area_m2']}㎡")
    print(f"主屋 {hut['span_x']}×{hut['span_y']}m = {hut['area_m2']}㎡  FL=+{hut['fl']}m")
    print(f"屋根 片流れ {hut['roof_pitch_deg']}°  南軒{hut['roof_edge_z_south']}m → 北軒{hut['roof_edge_z_north']}m")
    print(f"独立基礎 {piers}基  カメラ {len(cams)}台  太陽プリセット {len(spec['sun_presets'])}件")
    print("─" * 62)

    if render_dir:
        os.makedirs(render_dir, exist_ok=True)
        for cam, c in cams:
            set_sun(spec, c["sun"])
            scene.camera = cam
            scene.render.filepath = os.path.join(render_dir, f"{c['id']}.png")
            bpy.ops.render.render(write_still=True)
            print(f"  rendered {c['id']} ({c['label']})")
    else:
        set_sun(spec, spec["cameras"][0]["sun"])
        scene.camera = cams[0][0]


if __name__ == "__main__":
    main()
