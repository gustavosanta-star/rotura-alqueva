# -*- coding: utf-8 -*-
"""12_manning_vale.py — rugosidade do vale profundo (P12).

No P10 a rugosidade efetiva em Mértola ficou ~3× a do PEExt (n ≈ 0,085 contra 0,03).
Causa provável: os n da COS para matos e floresta (0,07–0,10) aplicados às encostas do
canhão, que ficam sob 20 a 40 m de água. Aqui essas encostas passam a n = 0,040.

Correr na janela Python do ArcGIS Pro (precisa de Spatial Analyst):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\12_manning_vale.py", encoding="utf-8").read())

Entrada : dados\\COS25\\cos2025_manning.shp (do 10) e dados\\manning\\vale_profundo_mask.tif
          (64,6 km² entre Pedrógão e Odeleite abaixo de talvegue + 30 m; scripts\\kit_p11\\r4_vale.py)
Saída   : dados\\COS25\\cos2025_manning_vale.shp (LC_NOME, MANNING) + cos2025_manning_vale_tabela.csv
Regra   : dentro do vale, os grupos de vegetação/culturas/solo passam a "Vale_profundo" (n = 0,040).
          Água (Rio, Albufeira, Estuário) e urbano mantêm o valor da COS.
"""
import os, csv, arcpy
from arcpy.sa import Raster, Int

base = r"C:\caminho\para\rotura-alqueva"
cos = os.path.join(base, r"dados\COS25\cos2025_manning.shp")
mask = os.path.join(base, r"dados\manning\vale_profundo_mask.tif")
out = os.path.join(base, r"dados\COS25\cos2025_manning_vale.shp")
tab = os.path.join(base, r"dados\COS25\cos2025_manning_vale_tabela.csv")
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

N_VALE = 0.040
MANTEM = {"Rio", "Albufeira_lagos", "Estuario_mar", "Urbano_denso", "Urbano_disperso",
          "Artificial_outros", "Estradas"}

print("1/4 Máscara do vale → polígono...")
vale = r"memory\vale"
arcpy.conversion.RasterToPolygon(Int(Raster(mask)), vale, "NO_SIMPLIFY", "Value")
arcpy.management.AddField(vale, "VALE", "SHORT")
arcpy.management.CalculateField(vale, "VALE", "1")
a_vale = sum(r[0] for r in arcpy.da.SearchCursor(vale, ["SHAPE@AREA"])) / 1e6
print(f"    área do vale: {a_vale:.1f} km2")

print("2/4 Identity COS × vale...")
ident = r"memory\cos_vale"
arcpy.analysis.Identity(cos, vale, ident)

print("3/4 Reclassificar dentro do vale...")
cont = {}
with arcpy.da.UpdateCursor(ident, ["LC_NOME", "MANNING", "VALE", "SHAPE@AREA"]) as cur:
    for nome, n, v, a in cur:
        if v == 1 and nome not in MANTEM:
            nome, n = "Vale_profundo", N_VALE
            cur.updateRow([nome, n, v, a])
        cont[(nome, n)] = cont.get((nome, n), 0.0) + a

print("4/4 Dissolve por grupo...")
arcpy.analysis.PairwiseDissolve(ident, out, ["LC_NOME", "MANNING"], multi_part="MULTI_PART")

with open(tab, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["LC_NOME", "MANNING", "area_km2"])
    for (g, n), a in sorted(cont.items(), key=lambda kv: -kv[1]):
        w.writerow([g, n, round(a / 1e6, 2)])
        print(f"{g:22s} n={n:.3f}  {a/1e6:8.1f} km2")
print("Feito:", out)
print("A seguir: RAS Mapper → Land Cover → nova camada 'LandCover_vale' a partir deste shapefile "
      "(campo de classes LC_NOME, Manning do campo MANNING).")
