# -*- coding: utf-8 -*-
"""Gera a animação 3D inclinada da cena B1_cena3d diretamente no .aprx (Pro fechado).
Câmara oblíqua que acompanha a frente da onda ao longo do eixo do Guadiana (como o vídeo 2D).
Uso: python anim3d.py entrada.aprx saida.aprx eixo.npy frente_1m.npy
"""
import sys, json, math, zipfile, copy
import numpy as np

src, dst, eixo_p, frente_p = sys.argv[1:5]
e = np.load(eixo_p); FR = np.load(frente_p)
REG = np.arange(0, 1441, 10)
T0 = 1767258000000                     # 01/01/2026 09:00 (ms, UTC)
KMAX = e[-1, 2]


def xy(km):
    km = float(np.clip(km, 0, KMAX))
    return float(np.interp(km, e[:, 2], e[:, 0])), float(np.interp(km, e[:, 2], e[:, 1]))


def rumo(km, a=6.0, b=10.0):
    x0, y0 = xy(km - a); x1, y1 = xy(km + b)
    return math.degrees(math.atan2(x1 - x0, y1 - y0)) % 360     # bússola: 0 = norte, horário


def camara(tx, ty, rumo_c, pitch, dist):
    p = math.radians(abs(pitch)); h = dist * math.cos(p)
    cx = tx - math.sin(math.radians(rumo_c)) * h
    cy = ty - math.cos(math.radians(rumo_c)) * h
    return cx, cy, dist * math.sin(p), pitch, (360 - rumo_c) % 360   # heading no CIM = 360 - rumo


# ---------------- guião (segundos de vídeo -> minutos simulados + câmara)
kfs = []
xb, yb = xy(0)
kfs.append((0.0, 0, camara(xb - 2000, yb + 6000, 200, -42, 38000)))          # albufeira inteira
kfs.append((3.0, 0, camara(*xy(3), rumo(3), -38, 17000)))                  # barragem, a olhar para jusante
for s in np.arange(7.0, 47.01, 4.0):
    u = (s - 3.0) / 44.0
    mins = 720.0 * u ** 1.25
    f = float(np.interp(mins, REG, FR))
    alvo = min(f + 2.0, 141.0)                 # não passar da foz (senão a câmara olha para o mar)
    pitch, dist = (-38, 17000) if alvo < 128 else (-55, 19000)   # na foz, mais de cima: sapais e VRSA/Ayamonte
    kfs.append((float(s), mins, camara(*xy(alvo), rumo(min(alvo, 135)), pitch, dist)))
fim = camara(632000, 4165000, 352, -34, 95000)                             # vale inteiro, de sul
kfs.append((54.0, 1440, fim))
kfs.append((59.0, 1440, fim))

# ---------------- escrever no aprx
zin = zipfile.ZipFile(src)
zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
CENA = "B1_cena3d/B1_cena3d.json"
TOPO = "aca1396d79e24652b1945bb4272e4bb5.json"
WE3D = "B1_cena3d/WorldElevation3D_Terrain3D.json"
IMG = "B1_cena3d/Image.json"
FIREFLY = "B1_cena3d/World_Imagery__Firefly_.json"
nomes = zipfile.ZipFile(src).namelist()
TEM_FF = FIREFLY in nomes
print("Firefly no projeto:", TEM_FF)
for it in zin.infolist():
    b = zin.read(it.filename)
    if it.filename in (CENA, TOPO, WE3D, IMG):
        bom = b.startswith(b"\xef\xbb\xbf")
        d = json.loads(b.decode("utf-8-sig"))
        if it.filename == CENA:
            tr = d["animationViewTracks"][0]
            mod = tr["keyframes"][0]
            novos = []
            for s, mins, (cx, cy, cz, pt, hd) in kfs:
                k = copy.deepcopy(mod)
                k["trackTime"] = s
                c = k["camera"]["camera"]
                c.update(x=cx, y=cy, z=cz, pitch=pt, heading=hd)
                k["camera"]["transitionScale"] = 0.3
                for kk in ("headingTransition", "pitchTransition", "rollTransition", "scaleTransition",
                           "xTransition", "yTransition", "zTransition", "fieldOfViewTransition"):
                    k["camera"][kk] = "AdjustableArc"
                ini = int(T0 + round(mins) * 60000)
                k["time"]["time"].update(start=ini, end=ini + 2 * 60000)
                k["time"]["startTimeTransition"] = k["time"]["endTimeTransition"] = "Linear"
                for l in k["layers"]:
                    if l["layerURI"].endswith(TOPO):
                        l["visible"] = not TEM_FF          # com o Firefly, o Topographic fica desligado
                if TEM_FF and not any(l["layerURI"].endswith(FIREFLY) for l in k["layers"]):
                    k["layers"].append({"type": "CIMKeyframeLayer", "layerURI": "CIMPATH=" + FIREFLY,
                                        "transparencyTransition": "Linear", "visible": True,
                                        "swipeDirection": "Right", "verticalExaggeration": 1})
                for sf in k.get("surfaces", []):
                    sf["verticalExaggeration"] = 3
                    for bs in sf.get("baseSources", []):
                        bs["visible"] = True
                novos.append(k)
            tr["keyframes"] = novos
            tr["endFrameTime"] = kfs[-1][0]
            if TEM_FF:      # Firefly por baixo de tudo (senão tapa a água)
                ff = "CIMPATH=" + FIREFLY
                d["layers"] = [u for u in d["layers"] if u != ff] + [ff]
            # sol a noroeste, 38° de altitude (relevo com volume)
            az, alt = math.radians(315), math.radians(38)
            d["illumination"].update(sunAzimuth=315, sunAltitude=38, sunPositionX=math.cos(alt) * math.sin(az),
                                     sunPositionY=math.cos(alt) * math.cos(az), sunPositionZ=math.sin(alt))
            print("camadas:", d["layers"])
            ts = d["timeSliderSettings"]
            ts.update(windowValue=2, stepIntervalValue=2)
            d["timeDisplay"]["timeValue"] = {"type": "TimeExtent", "start": T0, "end": T0 + 120000, "empty": False}
            print("keyframes:", len(novos), "duração:", tr["endFrameTime"], "s")
        elif it.filename == IMG:
            # duas imagens na janela de 2 min -> mostrar o máximo (evita alternar entre a mais antiga e a mais recente)
            d["mosaicRule"]["mosaicOperatorType"] = "Max"
            print("mosaico:", d["mosaicRule"])
        elif it.filename == TOPO:
            d["visibility"] = not TEM_FF
            print("Topographic visível:", d["visibility"])
        else:
            d["visibility"] = True
            print("visível:", d.get("name"))
        b = (b"\xef\xbb\xbf" if bom else b"") + json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    zout.writestr(it, b)
zout.close()
for s, mins, (cx, cy, cz, pt, hd) in kfs:
    print("%5.1f s  T+%5.1f h  x %.0f y %.0f z %.0f  pitch %d  heading(CIM) %.0f" % (s, mins / 60, cx, cy, cz, pt, hd))
