# -*- coding: utf-8 -*-
"""
19_animacao_camaras.py - escreve a câmara (e corrige a hora) de cada keyframe da
animação da cena B1_cena3d diretamente na definição CIM, sem depender do botão Update.

Diagnóstico (23/11): os 11 keyframes tinham todos a mesma câmara (a do passo 1);
as horas estavam certas. Este script reescreve as 11 câmaras.

Uso (janela Python do ArcGIS Pro):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\19_animacao_camaras.py", encoding="utf-8").read())
Depois: Ctrl+S, fechar e voltar a abrir o Animation Timeline (ou o separador da cena) e carregar em Play.
"""
import math
import datetime as dt
import arcpy

T0 = dt.datetime(2026, 1, 1, 9, 0, 0)

# local: (nome, x, y, heading_bússola, pitch, distância_m)   - ETRS89 / UTM 29N
LOC = {
    "alq": ("Barragem de Alqueva",   631500, 4228500, 220, -35, 22000),
    "ped": ("Pedrógão",              618700, 4219300, 200, -35, 20000),
    "mer": ("Mértola",               618200, 4166700, 180, -35, 22000),
    "alc": ("Alcoutim / Sanlúcar",   635300, 4147800, 165, -35, 22000),
    "foz": ("Foz - VRSA / Ayamonte", 640600, 4116700, 170, -35, 24000),
    "vale": ("Vale inteiro",         632000, 4150000,   0, -32, 75000),
}
PASSOS = [("alq", 0), ("alq", 20), ("ped", 20), ("ped", 100), ("mer", 220), ("mer", 320),
          ("alc", 380), ("alc", 480), ("foz", 640), ("foz", 760), ("vale", 1440)]


def camara(loc):
    nome, tx, ty, hd, pt, dist = LOC[loc]
    a = math.radians(abs(pt))
    horiz, z = dist * math.cos(a), dist * math.sin(a)
    if loc == "vale":
        cx, cy = tx, ty - horiz
    else:
        cx = tx - math.sin(math.radians(hd)) * horiz
        cy = ty - math.cos(math.radians(hd)) * horiz
    # no CIM o heading é guardado como 360 - rumo (confirmado no keyframe 1: 220 -> 140)
    return nome, cx, cy, z, pt, (360 - hd) % 360


def _mudar_hora(te, mins):
    """tenta reescrever o TimeExtent do keyframe (aceita datetime ou ms)."""
    t = T0 + dt.timedelta(minutes=mins)
    t2 = t + dt.timedelta(minutes=20)
    if isinstance(te.start, (int, float)):
        ep = dt.datetime(1970, 1, 1)
        te.start = int((t - ep).total_seconds() * 1000)
        te.end = int((t2 - ep).total_seconds() * 1000)
    else:
        te.start, te.end = t, t2


aprx = arcpy.mp.ArcGISProject("CURRENT")
cena = aprx.listMaps("B1_cena3d")[0]
cim = cena.getDefinition("V3")
trilhas = cim.animationViewTracks
if not trilhas:
    raise SystemExit("A cena não tem animação. Cria primeiro os 11 keyframes.")
ks = trilhas[0].keyframes
print("Animação '%s': %d keyframes" % (trilhas[0].name, len(ks)))
if len(ks) != len(PASSOS):
    print("ATENÇÃO: esperava %d keyframes; vou tratar os primeiros %d." % (len(PASSOS), min(len(ks), len(PASSOS))))

for i, (k, (loc, mins)) in enumerate(zip(ks, PASSOS), start=1):
    nome, x, y, z, pt, hd_cim = camara(loc)
    c = k.camera.camera
    c.x, c.y, c.z, c.pitch, c.heading = x, y, z, pt, hd_cim
    hora_ok = ""
    try:
        _mudar_hora(k.time.time, mins)
    except Exception as e:
        hora_ok = "  (hora não mexida: %s)" % e
    print("KF%2d  %-22s  +%2dh%02d  x %.0f  y %.0f  z %.0f%s" % (i, nome, mins // 60, mins % 60, x, y, z, hora_ok))

cena.setDefinition(cim)

# verificação: ler de volta
ks2 = cena.getDefinition("V3").animationViewTracks[0].keyframes
xs = {round(k.camera.camera.x) for k in ks2}
print("Câmaras diferentes gravadas: %d (devem ser 6)" % len(xs))
aprx.save()
print("Projeto gravado. Fecha e reabre o Animation Timeline e carrega em Play.")
