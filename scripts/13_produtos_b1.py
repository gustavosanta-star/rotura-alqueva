# -*- coding: utf-8 -*-
"""13_produtos_b1.py — produtos do cenário completo B1 (P13) a partir dos mapas do RAS Mapper.

Correr na janela Python do ArcGIS Pro (precisa de Spatial Analyst), com o HEC-RAS fechado:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\13_produtos_b1.py", encoding="utf-8").read())

Entrada : hecras\\p13b1\\*.vrt e *.shp (mapas gravados em "Manage Results Maps")
          dados\\vetor\\bgri2021\\bgri2021_corredor.geojson (geometria das subsecções) +
          dados\\vetor\\bgri2021\\fs2021_corredor.csv (Censos 2021, ficheiro síntese do INE, só o corredor)
          dados\\COS25\\cos2025_alqueva.shp (para as áreas urbanas)
Saída   : resultados\\p13\\mapas\\  (rasters GeoTIFF + shapefiles) e resultados\\p13\\produtos_b1.csv

O que faz:
 1. copia os mapas (VRT em mosaico) para GeoTIFF únicos com nomes simples;
 2. área inundada pela rotura = envolvente máxima − água que já existia às 09:00;
 3. perigosidade pelo produto h·v (classes ARR 2019, simplificadas só pelo h·v):
      1: ≤0,3   2: 0,3–0,6   3: 0,6–1,0   4: 1,0–4,0   5: >4,0 m²/s;
 4. isócronas do tempo de chegada (h depois da rotura de Alqueva, subida ≥ 0,3 m):
      ≤0,5 (≈ ZAS de 30 min) | 0,5–1 | 1–2 | 2–4 | 4–8 | 8–12 | 12–24 | >24 h;
 5. exposição: residentes, idosos, crianças, edifícios e alojamentos (Censos 2021) por concelho,
    por ponderação de área e limite superior; e área urbana da COS 2025 inundada.
"""
import os, glob, csv, arcpy
from arcpy.sa import Raster, Con, IsNull, SetNull, Reclassify, RemapRange, Int

base = r"C:\caminho\para\rotura-alqueva"
src = os.path.join(base, r"hecras\p13b1")
out = os.path.join(base, r"resultados\p13\mapas")
os.makedirs(out, exist_ok=True)
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
sr = arcpy.SpatialReference(25829)
arcpy.env.outputCoordinateSystem = sr
gdb = os.path.join(out, "b1.gdb")
if not arcpy.Exists(gdb):
    arcpy.management.CreateFileGDB(out, "b1.gdb")

def achar(padrao, ext):
    f = sorted(glob.glob(os.path.join(src, padrao + ext)))
    if not f:
        raise SystemExit(f"Não encontrei {padrao}{ext} em {src}. Confirma em 'Manage Results Maps' que o mapa foi criado.")
    return f[0]

# ---------- 1. rasters
mapas = {"profundidade_max": "Depth (Max)", "velocidade_max": "Velocity (Max)", "hv_max": "D _ V (Max)",
         "nivel_max": "WSE (Max)", "chegada_h": "Arrival Time*"}
R = {}
for nome, padrao in mapas.items():
    try:
        vrt = achar(padrao, ".vrt")
    except SystemExit:
        if nome == "nivel_max":
            vrt = achar("Water Surface Elevation (Max)", ".vrt")
        else:
            raise
    tif = os.path.join(out, nome + ".tif")
    print(f"1/5 {nome:18s} ← {os.path.basename(vrt)}")
    arcpy.management.CopyRaster(vrt, tif, pixel_type="32_BIT_FLOAT", nodata_value="-9999")
    R[nome] = tif

# ---------- 2. área inundada pela rotura
print("2/5 Área inundada...")
shp_09 = [s for s in glob.glob(os.path.join(src, "*Inundation*09*00*.shp"))]
if not shp_09:
    raise SystemExit("Falta o polígono 'Inundation Boundary (01JAN2026 09:00)' em hecras\\p13b1.")
inund_max = os.path.join(gdb, "inundacao_max")
agua_0900 = os.path.join(gdb, "agua_antes_rotura")
shp_max = [s for s in glob.glob(os.path.join(src, "*Inundation*Max*.shp"))]
if shp_max:
    arcpy.management.Dissolve(shp_max[0], inund_max)
else:
    # envolvente máxima = células com profundidade máxima > 0 (o RAS Mapper não gerou o polígono Max)
    molhado = Con(Raster(R["profundidade_max"]) > 0, 1)
    arcpy.conversion.RasterToPolygon(molhado, r"memory\inund_max_p", "SIMPLIFY", "Value")
    arcpy.management.Dissolve(r"memory\inund_max_p", inund_max)
arcpy.management.Dissolve(shp_09[0], agua_0900)
inund_rot = os.path.join(gdb, "area_inundada_rotura")
arcpy.analysis.PairwiseErase(inund_max, agua_0900, inund_rot)
area = lambda fc: sum(r[0] for r in arcpy.da.SearchCursor(fc, ["SHAPE@AREA"])) / 1e4
A_max, A_09, A_rot = area(inund_max), area(agua_0900), area(inund_rot)
print(f"    envolvente máxima {A_max:,.0f} ha | água às 09:00 {A_09:,.0f} ha | inundada pela rotura {A_rot:,.0f} ha (PEExt: 11 738 ha)")

# ---------- 3. perigosidade h·v
print("3/5 Perigosidade h·v...")
hv = Raster(R["hv_max"])
cls = Reclassify(hv, "VALUE", RemapRange([[0, 0.3, 1], [0.3, 0.6, 2], [0.6, 1.0, 3], [1.0, 4.0, 4], [4.0, 1e9, 5]]), "NODATA")
cls.save(os.path.join(out, "perigo_hv_classes.tif"))
perigo = {}
with arcpy.da.SearchCursor(os.path.join(out, "perigo_hv_classes.tif"), ["VALUE", "COUNT"]) as c:
    for v, n in c:
        perigo[int(v)] = n
cell = arcpy.Describe(R["hv_max"]).meanCellWidth
nomes_p = {1: "≤0,3", 2: "0,3–0,6", 3: "0,6–1,0", 4: "1,0–4,0", 5: ">4,0"}
for k in sorted(perigo):
    print(f"    classe {k} (h·v {nomes_p[k]} m²/s): {perigo[k] * cell * cell / 1e4:,.0f} ha")

# ---------- 4. isócronas
print("4/5 Isócronas...")
ch = Raster(R["chegada_h"])
iso = Reclassify(ch, "VALUE", RemapRange([[-1e9, 0.5, 1], [0.5, 1, 2], [1, 2, 3], [2, 4, 4], [4, 8, 5],
                                          [8, 12, 6], [12, 24, 7], [24, 1e9, 8]]), "NODATA")
iso_tif = os.path.join(out, "isocronas_classes.tif")
iso.save(iso_tif)
iso_fc = os.path.join(gdb, "isocronas")
arcpy.conversion.RasterToPolygon(iso_tif, iso_fc, "SIMPLIFY", "Value")
arcpy.management.AddField(iso_fc, "CLASSE", "TEXT", field_length=12)
rot = {1: "<=0.5 h", 2: "0.5-1 h", 3: "1-2 h", 4: "2-4 h", 5: "4-8 h", 6: "8-12 h", 7: "12-24 h", 8: ">24 h"}
iso_area = {}
with arcpy.da.UpdateCursor(iso_fc, ["gridcode", "CLASSE", "SHAPE@AREA"]) as c:
    for g, _, a in c:
        c.updateRow([g, rot[g], a]); iso_area[rot[g]] = iso_area.get(rot[g], 0) + a / 1e4
for k in rot.values():
    print(f"    {k:8s}: {iso_area.get(k, 0):,.0f} ha")

# ---------- 5. exposição
# População e edifícios: Censos 2021, ficheiro síntese por subsecção (INE), recortado ao corredor em
# dados\vetor\bgri2021\fs2021_corredor.csv. Estimativa por ponderação de área (população uniforme
# dentro de cada subsecção) e limite superior (todos os residentes das subsecções tocadas).
print("5/5 Exposição...")
bgri = os.path.join(gdb, "bgri2021")
arcpy.conversion.JSONToFeatures(os.path.join(base, r"dados\vetor\bgri2021\bgri2021_corredor.geojson"), r"memory\bgri_3763")
arcpy.management.Project(r"memory\bgri_3763", bgri, sr)
arcpy.management.AddField(bgri, "AREA_SUB", "DOUBLE")
arcpy.management.CalculateField(bgri, "AREA_SUB", "!shape.area!", "PYTHON3")
fs = {}
with open(os.path.join(base, r"dados\vetor\bgri2021\fs2021_corredor.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        fs[r["SUBSECCAO"]] = r
VARS = ["N_INDIVIDUOS", "N_INDIVIDUOS_65_OU_MAIS", "N_INDIVIDUOS_0_14", "N_EDIFICIOS_CLASSICOS", "N_ALOJAMENTOS_TOTAL"]
bgri_in = os.path.join(gdb, "bgri_inundada")
arcpy.analysis.PairwiseIntersect([bgri, inund_rot], bgri_in)
for v in VARS + ["FRACAO"]:
    arcpy.management.AddField(bgri_in, v if v == "FRACAO" else "E_" + v[2:], "DOUBLE")
expo, sup, tocadas = {}, {}, set()
campos = ["BGRI2021", "AREA_SUB", "SHAPE@", "FRACAO"] + ["E_" + v[2:] for v in VARS]
with arcpy.da.UpdateCursor(bgri_in, campos) as c:
    for row in c:
        cod, a_sub, a = row[0], row[1], row[2].area
        r = fs.get(cod)
        if not r or not a_sub:
            continue
        fr = min(a / a_sub, 1.0)
        mun = r["MUNICIPIO_DSG"]
        vals = [fr * float(r[v] or 0) for v in VARS]
        c.updateRow(row[:3] + [fr] + vals)
        e = expo.setdefault(mun, [0.0] * len(VARS))
        for k, x in enumerate(vals):
            e[k] += x
        if cod not in tocadas:
            tocadas.add(cod)
            s_ = sup.setdefault(mun, [0.0] * len(VARS))
            for k, v in enumerate(VARS):
                s_[k] += float(r[v] or 0)
n_sub = len(tocadas)
tot = [sum(e[k] for e in expo.values()) for k in range(len(VARS))]
tot_sup = [sum(e[k] for e in sup.values()) for k in range(len(VARS))]
print(f"    subsecções BGRI tocadas: {n_sub}")
print(f"    residentes expostos (ponderação de área): {tot[0]:,.0f}  | limite superior: {tot_sup[0]:,.0f}")
print(f"    edifícios clássicos expostos (ponderação): {tot[3]:,.0f}  | limite superior: {tot_sup[3]:,.0f}")
for mun in sorted(expo, key=lambda m: -expo[m][0]):
    print(f"      {mun:28s} residentes {expo[mun][0]:8,.0f} (até {sup[mun][0]:8,.0f})  edifícios {expo[mun][3]:7,.0f}")
cos = os.path.join(base, r"dados\COS25\cos2025_alqueva.shp")
urb = r"memory\cos_urb"
arcpy.analysis.Select(cos, urb, "cos25v1_n2 LIKE '1%'")
urb_in = os.path.join(gdb, "urbano_inundado")
arcpy.analysis.PairwiseIntersect([urb, inund_rot], urb_in)
a_urb = area(urb_in)
print(f"    área urbana/artificial (COS 1.x) inundada: {a_urb:,.1f} ha")
conc = {m: e for m, e in expo.items()}

with open(os.path.join(base, r"resultados\p13\produtos_b1.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["indicador", "valor", "unidade"])
    w.writerows([["envolvente_maxima", round(A_max), "ha"], ["agua_antes_rotura", round(A_09), "ha"],
                 ["inundada_pela_rotura", round(A_rot), "ha"], ["peext_area_inundada", 11738, "ha"],
                 ["urbano_inundado_COS1", round(a_urb, 1), "ha"], ["subseccoes_bgri_tocadas", n_sub, "n"]])
    for k in sorted(perigo):
        w.writerow([f"perigo_hv_{k}_{nomes_p[k]}", round(perigo[k] * cell * cell / 1e4), "ha"])
    for k in rot.values():
        w.writerow([f"isocrona_{k}", round(iso_area.get(k, 0)), "ha"])
    for k, v in enumerate(VARS):
        w.writerow([f"expostos_{v}_ponderado", round(tot[k]), "n"])
        w.writerow([f"expostos_{v}_limite_sup", round(tot_sup[k]), "n"])
    for mun, e in sorted(conc.items()):
        w.writerow([f"residentes_expostos_{mun}", round(e[0]), "n"])
        w.writerow([f"edificios_expostos_{mun}", round(e[3]), "n"])
print("Feito:", out)
