# -*- coding: utf-8 -*-
"""13b_exposicao_b1.py — passo 5 do 13 (exposição) + perigosidade recortada à área inundada pela rotura.
Usa o que o 13 já gravou em resultados\\p13\\mapas\\ (b1.gdb\\area_inundada_rotura, perigo_hv_classes.tif,
isocronas_classes.tif). Imprime o tempo de cada etapa.

Janela Python do ArcGIS Pro:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\13b_exposicao_b1.py", encoding="utf-8").read())

Entradas novas:
  dados\\vetor\\bgri2021\\bgri2021_corredor_25829.shp — subsecções BGRI 2021 já em EPSG 25829
      (convertidas do geojson; o JSONToFeatures encravava)
  dados\\vetor\\bgri2021\\fs2021_corredor.csv — Censos 2021 (ficheiro síntese do INE), só o corredor
Exposição: ponderação de área (população uniforme na subsecção) e limite superior (subsecção tocada = toda exposta).
"""
import os, csv, time, arcpy
from arcpy.sa import Raster, ExtractByMask

T0 = time.time()
def t(msg): print(f"[{time.time() - T0:6.1f} s] {msg}")

base = r"C:\caminho\para\rotura-alqueva"
out = os.path.join(base, r"resultados\p13\mapas")
gdb = os.path.join(out, "b1.gdb")
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
sr = arcpy.SpatialReference(25829)
inund_rot = os.path.join(gdb, "area_inundada_rotura")
area = lambda fc: sum(r[0] for r in arcpy.da.SearchCursor(fc, ["SHAPE@AREA"])) / 1e4

# ---------- A. perigosidade e isócronas só na área inundada pela rotura
t("A. Perigosidade e isócronas recortadas à área inundada pela rotura...")
nomes_p = {1: "≤0,3", 2: "0,3–0,6", 3: "0,6–1,0", 4: "1,0–4,0", 5: ">4,0"}
rot = {1: "<=0.5 h", 2: "0.5-1 h", 3: "1-2 h", 4: "2-4 h", 5: "4-8 h", 6: "8-12 h", 7: "12-24 h", 8: ">24 h"}
res = {}
for nome, tif, rotulos in [("perigo", "perigo_hv_classes.tif", nomes_p), ("isocrona", "isocronas_classes.tif", rot)]:
    r = ExtractByMask(Raster(os.path.join(out, tif)), inund_rot)
    saida = os.path.join(out, tif.replace(".tif", "_rotura.tif"))
    r.save(saida)
    arcpy.management.BuildRasterAttributeTable(saida, "Overwrite")
    cell = arcpy.Describe(saida).meanCellWidth
    d = {int(v): n * cell * cell / 1e4 for v, n in arcpy.da.SearchCursor(saida, ["VALUE", "COUNT"])}
    res[nome] = d
    for k in sorted(rotulos):
        print(f"    {nome} {rotulos[k]:8s}: {d.get(k, 0):8,.0f} ha")
t("A. feito")

# ---------- B. exposição
t("B1. A ler subsecções BGRI (shapefile em EPSG 25829)...")
bgri = os.path.join(gdb, "bgri2021")
arcpy.management.CopyFeatures(os.path.join(base, r"dados\vetor\bgri2021\bgri2021_corredor_25829.shp"), bgri)
arcpy.management.AddField(bgri, "AREA_SUB", "DOUBLE")
arcpy.management.CalculateField(bgri, "AREA_SUB", "!shape.area!", "PYTHON3")
t(f"B1. {int(arcpy.management.GetCount(bgri)[0])} subsecções")

t("B2. Intersect com a área inundada pela rotura...")
bgri_in = os.path.join(gdb, "bgri_inundada")
arcpy.analysis.PairwiseIntersect([bgri, inund_rot], bgri_in)
t(f"B2. {int(arcpy.management.GetCount(bgri_in)[0])} pedaços")

t("B3. Censos 2021...")
fs = {}
with open(os.path.join(base, r"dados\vetor\bgri2021\fs2021_corredor.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        fs[r["SUBSECCAO"]] = r
VARS = ["N_INDIVIDUOS", "N_INDIVIDUOS_65_OU_MAIS", "N_INDIVIDUOS_0_14", "N_EDIFICIOS_CLASSICOS", "N_ALOJAMENTOS_TOTAL"]
arcpy.management.AddField(bgri_in, "FRACAO", "DOUBLE")
for v in VARS:
    arcpy.management.AddField(bgri_in, "E_" + v[2:], "DOUBLE")
expo, sup, tocadas = {}, {}, set()
with arcpy.da.UpdateCursor(bgri_in, ["BGRI2021", "AREA_SUB", "SHAPE@", "FRACAO"] + ["E_" + v[2:] for v in VARS]) as c:
    for row in c:
        cod, a_sub, g = row[0], row[1], row[2]
        a = g.area
        r = fs.get(cod)
        if not r or not a_sub:
            continue
        fr = min(a / a_sub, 1.0)
        vals = [fr * float(r[v] or 0) for v in VARS]
        c.updateRow([cod, a_sub, g, fr] + vals)
        mun = r["MUNICIPIO_DSG"]
        e = expo.setdefault(mun, [0.0] * len(VARS))
        for k, x in enumerate(vals):
            e[k] += x
        if cod not in tocadas:
            tocadas.add(cod)
            s = sup.setdefault(mun, [0.0] * len(VARS))
            for k, v in enumerate(VARS):
                s[k] += float(r[v] or 0)
tot = [sum(e[k] for e in expo.values()) for k in range(len(VARS))]
tot_sup = [sum(e[k] for e in sup.values()) for k in range(len(VARS))]
t("B3. feito")
print(f"    subsecções tocadas: {len(tocadas)}")
print(f"    residentes expostos: {tot[0]:,.0f} (ponderação de área) | até {tot_sup[0]:,.0f} (limite superior)")
print(f"      dos quais 65+ anos: {tot[1]:,.0f} | até {tot_sup[1]:,.0f};  0–14 anos: {tot[2]:,.0f} | até {tot_sup[2]:,.0f}")
print(f"    edifícios clássicos: {tot[3]:,.0f} | até {tot_sup[3]:,.0f};  alojamentos: {tot[4]:,.0f} | até {tot_sup[4]:,.0f}")
for mun in sorted(expo, key=lambda m: -expo[m][0]):
    print(f"      {mun:28s} residentes {expo[mun][0]:8,.0f} (até {sup[mun][0]:8,.0f})   edifícios {expo[mun][3]:7,.0f} (até {sup[mun][3]:7,.0f})")

t("B4. Área urbana da COS inundada...")
urb = r"memory\cos_urb"
arcpy.analysis.Select(os.path.join(base, r"dados\COS25\cos2025_alqueva.shp"), urb, "cos25v1_n2 LIKE '1%'")
urb_in = os.path.join(gdb, "urbano_inundado")
arcpy.analysis.PairwiseIntersect([urb, inund_rot], urb_in)
a_urb = area(urb_in)
t(f"B4. área urbana/artificial (COS 1.x) inundada: {a_urb:,.1f} ha")

with open(os.path.join(base, r"resultados\p13\exposicao_b1.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["indicador", "valor", "unidade"])
    for k in sorted(nomes_p):
        w.writerow([f"perigo_hv_{nomes_p[k]}_na_area_rotura", round(res["perigo"].get(k, 0)), "ha"])
    for k in sorted(rot):
        w.writerow([f"isocrona_{rot[k]}_na_area_rotura", round(res["isocrona"].get(k, 0)), "ha"])
    w.writerow(["subseccoes_tocadas", len(tocadas), "n"])
    for k, v in enumerate(VARS):
        w.writerow([f"{v}_ponderado", round(tot[k]), "n"])
        w.writerow([f"{v}_limite_sup", round(tot_sup[k]), "n"])
    w.writerow(["urbano_inundado_COS1", round(a_urb, 1), "ha"])
    for mun in sorted(expo):
        w.writerow([f"residentes_{mun}_ponderado", round(expo[mun][0]), "n"])
        w.writerow([f"residentes_{mun}_limite_sup", round(sup[mun][0]), "n"])
        w.writerow([f"edificios_{mun}_ponderado", round(expo[mun][3]), "n"])
t("Feito: resultados\\p13\\exposicao_b1.csv")
