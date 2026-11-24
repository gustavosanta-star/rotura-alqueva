# -*- coding: utf-8 -*-
"""14_exposicao_iberica.py — exposição das duas margens (Portugal + Espanha) na área inundada pela rotura (B1).

Janela Python do ArcGIS Pro (depois do 13 e do 13b):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\14_exposicao_iberica.py", encoding="utf-8").read())

Entradas (dados\\espanha\\):
  jrc_pop2021_100m_corredor_25829.shp — JRC-ESTAT Census Population Grid 2021 (100 m), recortada ao corredor
      e convertida de EPSG 3035 para 25829 (scripts\\kit_p11\\r9_jrc_corredor.py). Campo POP = residentes.
  catastro_edificios_huelva_25829.shp — Catastro INSPIRE (edifícios) de Ayamonte, Villablanca, San Silvestre de
      Guzmán, Sanlúcar de Guadiana, El Granado, Puebla de Guzmán e Paymogo (scripts\\kit_p11\\r8_catastro_shp.py).
País de cada célula: Portugal se o centro cair numa subsecção BGRI do corredor; caso contrário, Espanha.
Residentes: ponderação de área da célula de 100 m inundada e limite superior (célula tocada = toda exposta).
Edifícios espanhóis: edifícios do Catastro cuja planta toca a área inundada pela rotura.
"""
import os, csv, time, arcpy

T0 = time.time()
def t(msg): print(f"[{time.time() - T0:6.1f} s] {msg}")

base = r"C:\caminho\para\rotura-alqueva"
gdb = os.path.join(base, r"resultados\p13\mapas\b1.gdb")
esp = os.path.join(base, r"dados\espanha")
arcpy.env.overwriteOutput = True
inund_rot = os.path.join(gdb, "area_inundada_rotura")
bgri = os.path.join(gdb, "bgri2021")

t("1. Grelha JRC 2021 (100 m)...")
jrc = os.path.join(gdb, "jrc_pop2021")
arcpy.management.CopyFeatures(os.path.join(esp, "jrc_pop2021_100m_corredor_25829.shp"), jrc)
arcpy.management.AddField(jrc, "AREA_CEL", "DOUBLE")
arcpy.management.CalculateField(jrc, "AREA_CEL", "!shape.area!", "PYTHON3")
arcpy.management.AddField(jrc, "PAIS", "TEXT", field_length=2)
arcpy.management.CalculateField(jrc, "PAIS", "'ES'", "PYTHON3")
lyr = arcpy.management.MakeFeatureLayer(jrc, "jrc_lyr")
arcpy.management.SelectLayerByLocation(lyr, "HAVE_THEIR_CENTER_IN", bgri)
arcpy.management.CalculateField(lyr, "PAIS", "'PT'", "PYTHON3")
arcpy.management.SelectLayerByAttribute(lyr, "CLEAR_SELECTION")
tot_pais = {}
for p, pop in arcpy.da.SearchCursor(jrc, ["PAIS", "POP"]):
    tot_pais[p] = tot_pais.get(p, 0) + pop
t(f"1. residentes na janela do corredor: PT {tot_pais.get('PT', 0):,.0f} | ES {tot_pais.get('ES', 0):,.0f}")

t("2. Intersect com a área inundada pela rotura...")
jrc_in = os.path.join(gdb, "jrc_pop2021_inundada")
arcpy.analysis.PairwiseIntersect([jrc, inund_rot], jrc_in)
pond, sup, vistos = {}, {}, set()
for oid, p, pop, a_cel, g in arcpy.da.SearchCursor(jrc_in, ["FID_jrc_pop2021", "PAIS", "POP", "AREA_CEL", "SHAPE@"]):
    pond[p] = pond.get(p, 0) + pop * min(g.area / a_cel, 1.0)
    if oid not in vistos:
        vistos.add(oid); sup[p] = sup.get(p, 0) + pop
for p in ("PT", "ES"):
    t(f"2. {p}: residentes expostos {pond.get(p, 0):,.0f} (ponderação de área) | até {sup.get(p, 0):,.0f} (células tocadas)")

t("3. Edifícios do Catastro (Espanha)...")
cat = os.path.join(gdb, "catastro_huelva")
arcpy.management.CopyFeatures(os.path.join(esp, "catastro_edificios_huelva_25829.shp"), cat)
clyr = arcpy.management.MakeFeatureLayer(cat, "cat_lyr")
arcpy.management.SelectLayerByLocation(clyr, "INTERSECT", inund_rot)
cat_in = os.path.join(gdb, "catastro_inundado")
arcpy.management.CopyFeatures(clyr, cat_in)
por_mun, por_uso = {}, {}
for mun, uso, viv in arcpy.da.SearchCursor(cat_in, ["MUN", "USO", "N_VIV"]):
    m = por_mun.setdefault(mun, [0, 0]); m[0] += 1; m[1] += int(viv or 0)
    por_uso[uso or "sem_uso"] = por_uso.get(uso or "sem_uso", 0) + 1
n_ed = sum(v[0] for v in por_mun.values()); n_viv = sum(v[1] for v in por_mun.values())
t(f"3. edifícios espanhóis expostos: {n_ed:,} | habitações: {n_viv:,}")
for mun, (n, v) in sorted(por_mun.items(), key=lambda kv: -kv[1][0]):
    print(f"      {mun:26s} edifícios {n:6,}  habitações {v:6,}")
for uso, n in sorted(por_uso.items(), key=lambda kv: -kv[1]):
    print(f"      uso {uso:22s} {n:6,}")

with open(os.path.join(base, r"resultados\p13\exposicao_iberica_b1.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["indicador", "valor", "unidade", "fonte"])
    for p in ("PT", "ES"):
        w.writerow([f"residentes_expostos_{p}_ponderado", round(pond.get(p, 0)), "n", "JRC-ESTAT Census Grid 2021 100 m"])
        w.writerow([f"residentes_expostos_{p}_limite_sup", round(sup.get(p, 0)), "n", "JRC-ESTAT Census Grid 2021 100 m"])
    w.writerow(["edificios_expostos_ES", n_ed, "n", "Catastro INSPIRE"])
    w.writerow(["habitacoes_expostas_ES", n_viv, "n", "Catastro INSPIRE"])
    for mun, (n, v) in sorted(por_mun.items()):
        w.writerow([f"edificios_expostos_{mun}", n, "n", "Catastro INSPIRE"])
        w.writerow([f"habitacoes_expostas_{mun}", v, "n", "Catastro INSPIRE"])
t("Feito: resultados\\p13\\exposicao_iberica_b1.csv")
