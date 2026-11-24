# -*- coding: utf-8 -*-
"""
17_camara_b1.py  (v2) - câmara + hora para os keyframes da animação B1.

v2: a câmara chega a cada local ANTES da frente de onda e fica parada enquanto
a onda passa (2 keyframes por local). A hora nunca anda para trás.

Uso (janela Python do ArcGIS Pro, com a cena B1_cena3d ativa):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\17_camara_b1.py", encoding="utf-8").read())
    passo(1)   -> Create first keyframe
    passo(2)   -> Append
    ...
    passo(11)  -> Append
Antes de começar: Animation Properties -> Configuration -> Append Time = 00:05.000
(11 keyframes x 5 s = 50 s).

Ajustes finos: passo(n, d=..., pitch=..., heading=...).
Coordenadas dos alvos em ETRS89 / UTM 29N (EPSG 25829), aproximadas.
Chegadas B1 (subida >= 0,3 m): Pedrógão 0,7 h, Mértola 4,3 h, Alcoutim 7,2 h, VRSA 11,5 h.
"""
import math
import datetime as dt
import arcpy

T0 = dt.datetime(2026, 1, 1, 9, 0, 0)   # instante da rotura na cena (data de referência)

# local: (nome, x, y, heading, pitch, distancia_m)
LOC = {
    "alq": ("Barragem de Alqueva",     631500, 4228500, 220, -35, 22000),
    "ped": ("Pedrógão",                618700, 4219300, 200, -35, 20000),
    "mer": ("Mértola",                 618200, 4166700, 180, -35, 22000),
    "alc": ("Alcoutim / Sanlúcar",     635300, 4147800, 165, -35, 22000),
    "foz": ("Foz - VRSA / Ayamonte",   640600, 4116700, 170, -35, 24000),
    "vale": ("Vale inteiro",           632000, 4150000,   0, -32, 75000),
}

# passo: (local, minutos após a rotura)  - sempre crescente
PASSOS = {
    1: ("alq", 0),      # rotura
    2: ("alq", 20),     # albufeira a esvaziar
    3: ("ped", 20),     # câmara chega a Pedrógão antes da onda (chegada ~42 min)
    4: ("ped", 100),    # onda passa Pedrógão
    5: ("mer", 220),    # Mértola antes da onda (chegada ~4 h 20)
    6: ("mer", 320),
    7: ("alc", 380),    # Alcoutim antes da onda (chegada ~7 h 10)
    8: ("alc", 480),
    9: ("foz", 640),    # foz antes da onda (chegada ~11 h 30)
    10: ("foz", 760),
    11: ("vale", 1440),  # fim: vale inteiro às 24 h
}


def _por_tempo(v, t):
    try:
        v.time.currentTimeStart = t
        v.time.currentTimeEnd = t + dt.timedelta(minutes=20)
        return True
    except Exception as e:
        print("  (hora não definida por script: %s) -> põe à mão %s" % (e, t.strftime("%d/%m %H:%M")))
        return False


def _camara(v, m, tx, ty, hd, pt, dist, geral=False):
    a = math.radians(abs(pt))
    horiz = dist * math.cos(a)
    z = dist * math.sin(a)
    if geral:  # a sul a olhar para norte
        cx, cy = tx, ty - horiz
    else:
        cx = tx - math.sin(math.radians(hd)) * horiz
        cy = ty - math.cos(math.radians(hd)) * horiz
    p = arcpy.PointGeometry(arcpy.Point(cx, cy), arcpy.SpatialReference(25829)) \
        .projectAs(m.spatialReference).firstPoint
    c = v.camera
    c.X, c.Y, c.Z = p.X, p.Y, z
    c.pitch, c.heading, c.roll = pt, hd, 0
    v.camera = c


def passo(n, d=None, pitch=None, heading=None):
    loc, mins = PASSOS[n]
    nome, tx, ty, hd, pt, dist = LOC[loc]
    dist = d if d is not None else dist
    pt = pitch if pitch is not None else pt
    hd = heading if heading is not None else hd
    v = arcpy.mp.ArcGISProject("CURRENT").activeView
    _camara(v, v.map, tx, ty, hd, pt, dist, geral=(loc == "vale"))
    t = T0 + dt.timedelta(minutes=mins)
    _por_tempo(v, t)
    acao = "Create first keyframe" if n == 1 else "Append"
    print("passo %2d  %-24s %s (+%d h %02d min)  -> agora: %s"
          % (n, nome, t.strftime("%d/%m %H:%M"), mins // 60, mins % 60, acao))


# compatibilidade com a v1
def kf(n, d=None, pitch=None, heading=None):
    mapa = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11}
    passo(mapa[n], d, pitch, heading)


print("17_camara_b1 v2 carregado: passo(1) ... passo(11)  (Append Time = 5 s)")
