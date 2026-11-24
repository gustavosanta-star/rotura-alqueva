# -*- coding: utf-8 -*-
"""
18_limite_modelo.py - contorno da malha HEC-RAS (Perimeter 1 + Albufeira) na cena B1_cena3d.

Porquê: na foz a cheia espalha-se pelos sapais de Castro Marim e pelas marismas de
Isla Cristina e pára em linhas retas, que são o limite da área 2D (parede no modelo).
Com o contorno desenhado, os bordos retos lêem-se como "fim do modelo" e não como erro.

Uso (janela Python do ArcGIS Pro):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\18_limite_modelo.py", encoding="utf-8").read())
"""
import os
import arcpy

base = r"C:\caminho\para\rotura-alqueva"
gdb = os.path.join(base, r"resultados\p13\mapas\b1.gdb")
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False

cel = os.path.join(gdb, "celulas_malha")
per = os.path.join(gdb, "limite_modelo")
print("1. A dissolver as células da malha (pode levar 1-2 min)...")
arcpy.analysis.PairwiseDissolve(cel, per)
print("   feito:", per)

aprx = arcpy.mp.ArcGISProject("CURRENT")
cena = aprx.listMaps("B1_cena3d")[0]
for l in cena.listLayers("Limite do modelo*"):
    cena.removeLayer(l)
lyr = cena.addDataFromPath(per)
lyr.name = "Limite do modelo HEC-RAS"

# sem preenchimento, contorno cinzento escuro
sym = lyr.symbology
sym.renderer.symbol.color = {"RGB": [0, 0, 0, 0]}
sym.renderer.symbol.outlineColor = {"RGB": [70, 70, 70, 100]}
sym.renderer.symbol.outlineWidth = 1.5
lyr.symbology = sym

# tracejado (via CIM); se falhar fica contínuo
try:
    cim = lyr.getDefinition("V3")
    for sl in cim.renderer.symbol.symbol.symbolLayers:
        if type(sl).__name__ == "CIMSolidStroke":
            d = arcpy.cim.CreateCIMObjectFromClassName("CIMGeometricEffectDashes", "V3")
            d.dashTemplate = [6, 3]
            d.lineDashEnding = "NoConstraint"
            sl.effects = [d]
    lyr.setDefinition(cim)
    print("2. contorno tracejado aplicado")
except Exception as e:
    print("2. contorno contínuo (tracejado não aplicado: %s)" % e)

aprx.save()
print("3. Camada 'Limite do modelo HEC-RAS' na cena B1_cena3d; projeto gravado.")
