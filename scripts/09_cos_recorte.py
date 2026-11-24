# -*- coding: utf-8 -*-
"""09_cos_recorte.py — recorta a COS2025 para a zona do modelo e prepara-a para o HEC-RAS.

Correr na janela Python do ArcGIS Pro:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\09_cos_recorte.py", encoding="utf-8").read())

Faz:
 1) retângulo da zona do modelo (UTM 29N: 610000-682000 E, 4110000-4298000 N)
 2) recorta a cos2025v1 (PT-TM06) por esse retângulo
 3) reprojeta para ETRS89 / UTM 29N (EPSG 25829), o sistema do HEC-RAS
 4) escreve dados\\COS25\\cos2025_alqueva.shp e um resumo das classes (cos2025_classes.csv)
"""
import os, csv, arcpy

base = r"C:\caminho\para\rotura-alqueva"
cos = os.path.join(base, r"dados\COS25\cos2025v1.shp")
out_dir = os.path.join(base, r"dados\COS25")
out_shp = os.path.join(out_dir, "cos2025_alqueva.shp")
out_csv = os.path.join(out_dir, "cos2025_classes.csv")

arcpy.env.overwriteOutput = True
sr_utm = arcpy.SpatialReference(25829)
sr_cos = arcpy.Describe(cos).spatialReference
print("COS em:", sr_cos.name)

# 1) retângulo em UTM 29N, projetado para o sistema da COS
x0, x1, y0, y1 = 610000, 682000, 4110000, 4298000
ring = arcpy.Array([arcpy.Point(x0, y0), arcpy.Point(x0, y1), arcpy.Point(x1, y1),
                    arcpy.Point(x1, y0), arcpy.Point(x0, y0)])
rect = arcpy.Polygon(ring, sr_utm).projectAs(sr_cos)
rect_fc = r"memory\rect_alqueva"
arcpy.management.CopyFeatures([rect], rect_fc)

# 2) recorte (pode demorar alguns minutos: a COS tem ~1,4 GB)
print("A recortar...")
clip_fc = r"memory\cos_clip"
arcpy.analysis.PairwiseClip(cos, rect_fc, clip_fc)
print("Polígonos recortados:", int(arcpy.management.GetCount(clip_fc)[0]))

# 3) reprojetar para UTM 29N
print("A reprojetar para EPSG 25829...")
arcpy.management.Project(clip_fc, out_shp, sr_utm)

# 4) resumo das classes: todos os campos de texto/inteiros curtos + área total
fields = [f for f in arcpy.ListFields(out_shp) if f.type in ("String", "SmallInteger", "Integer", "Double")
          and f.name.upper() not in ("FID", "SHAPE_LENG", "SHAPE_AREA", "OBJECTID")]
print("Campos:", [(f.name, f.type) for f in fields])
names = [f.name for f in fields if f.type == "String" or f.name.upper().startswith("COS")]
if not names:
    names = [f.name for f in fields][:3]
area = {}
with arcpy.da.SearchCursor(out_shp, names + ["SHAPE@AREA"]) as cur:
    for row in cur:
        k = tuple(row[:-1]); area[k] = area.get(k, 0.0) + row[-1]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(names + ["area_km2"])
    for k, a in sorted(area.items(), key=lambda kv: -kv[1]):
        w.writerow(list(k) + [round(a / 1e6, 3)])
print("Classes:", len(area))
print("Feito:", out_shp)
print("Resumo:", out_csv)
