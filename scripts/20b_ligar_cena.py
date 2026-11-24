# -*- coding: utf-8 -*-
"""20b_ligar_cena.py - passo 5 do script 20, à parte e mais robusto.

As imagens de 2 min e o mosaico profundidade_2min já estão feitos (passos 1-4 do script 20).
Este script só liga a camada da cena ao mosaico novo e põe a janela dos keyframes em 2 min.

    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\20b_ligar_cena.py", encoding="utf-8").read())
"""
import os, datetime, arcpy

base = r"C:\caminho\para\rotura-alqueva"
gdb = os.path.join(base, r"resultados\p13\mapas\b1.gdb")
md = os.path.join(gdb, "profundidade_2min")
PASSO_MIN = 2
assert arcpy.Exists(md), "Falta o mosaico profundidade_2min: corre primeiro o script 20."

aprx = arcpy.mp.ArcGISProject("CURRENT")
cenas = [m for m in aprx.listMaps() if m.name.startswith("B1_cena3d")]
print("Cenas encontradas:", [m.name for m in cenas])


def fonte(l):
    for attr in ("dataSource",):
        try:
            return getattr(l, attr)
        except Exception:
            pass
    try:
        return arcpy.Describe(l).catalogPath
    except Exception:
        return ""


alvo = None
for m in cenas:
    for l in m.listLayers():
        nome = l.name or ""
        src = fonte(l) or ""
        print("   camada: %-45s  fonte: %s" % (nome[:45], src[-60:]))
        if alvo is None and ("profundidade_tempo" in src.lower() or "profundidade_2min" in src.lower()
                             or nome.lower().startswith("profundidade")):
            # só a camada de topo do mosaico (não as subcamadas Boundary/Footprint/Image)
            if nome not in ("Boundary", "Footprint", "Image"):
                alvo = (m, l)

if alvo is None:
    raise SystemExit("Não encontrei a camada de profundidade. Manda ao Claude a lista de camadas acima.")
cena, lyr = alvo
print("Camada a trocar:", lyr.name, "na cena", cena.name)

try:
    cp = lyr.connectionProperties
    novo = dict(cp)
    novo["dataset"] = "profundidade_2min"
    lyr.updateConnectionProperties(cp, novo)
    lyr.name = "Profundidade (m) - 2 em 2 min"
    print("   ligada a:", fonte(lyr))
except Exception as e:
    print("   (trocar a fonte à mão: botão direito na camada -> Properties -> Source -> Set Data Source -> "
          "b1.gdb\\profundidade_2min)", e)

cim = cena.getDefinition("V3")
n_kf = 0
for tr in cim.animationViewTracks or []:
    for k in tr.keyframes:
        te = k.time.time
        if isinstance(te.start, (int, float)):
            te.end = te.start + PASSO_MIN * 60 * 1000
        else:
            te.end = te.start + datetime.timedelta(minutes=PASSO_MIN)
        n_kf += 1
cena.setDefinition(cim)
aprx.save()
print("Feito: %d keyframes com janela de %d min; projeto gravado. Fecha o Pro SEM guardar e reabre." % (n_kf, PASSO_MIN))
