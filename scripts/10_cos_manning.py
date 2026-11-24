# -*- coding: utf-8 -*-
"""10_cos_manning.py — atribui o coeficiente de Manning a cada classe da COS2025 e
agrega os polígonos por grupo de rugosidade, para importar no RAS Mapper.

Correr na janela Python do ArcGIS Pro:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\10_cos_manning.py", encoding="utf-8").read())

Entrada : dados\\COS25\\cos2025_alqueva.shp (do 09_cos_recorte.py), campos cos25v1_n4 / cos25v1_n2
Saída   : dados\\COS25\\cos2025_manning.shp (campos LC_NOME, MANNING) + cos2025_manning_tabela.csv
Valores : referências usuais para modelação 2D de cheias (Chow 1959; manual HEC-RAS 2D),
          escolhidos para a vegetação do Baixo Alentejo/Guadiana. São uma decisão de modelação.
"""
import os, csv, arcpy

base = r"C:\caminho\para\rotura-alqueva"
src = os.path.join(base, r"dados\COS25\cos2025_alqueva.shp")
out = os.path.join(base, r"dados\COS25\cos2025_manning.shp")
tab = os.path.join(base, r"dados\COS25\cos2025_manning_tabela.csv")
arcpy.env.overwriteOutput = True

# grupo de rugosidade -> Manning n
GRUPOS = {
    "Rio":                      0.035,
    "Albufeira_lagos":          0.030,
    "Estuario_mar":             0.025,
    "Zonas_humidas":            0.060,
    "Areais_descoberto":        0.030,
    "Pastagens":                0.035,
    "Culturas_temporarias":     0.040,
    "Culturas_permanentes":     0.060,
    "Culturas_associadas":      0.050,
    "Estufas":                  0.100,
    "Montado_SAF":              0.050,
    "Floresta":                 0.100,
    "Matos":                    0.070,
    "Urbano_denso":             0.150,
    "Urbano_disperso":          0.100,
    "Artificial_outros":        0.080,
    "Estradas":                 0.030,
    "Extracao_solo_nu":         0.035,
}

def grupo(n4, n2):
    n4 = str(n4); n2 = str(n2)
    if n4.startswith("9.1.1"):              return "Rio"
    if n4.startswith("9.1.2"):              return "Albufeira_lagos"
    if n4.startswith("9.3"):                return "Estuario_mar"
    if n2 == "81" or n2.startswith("8"):    return "Zonas_humidas"
    if n2.startswith("7"):                  return "Areais_descoberto"
    if n2 == "31" or n2.startswith("3"):    return "Pastagens"
    if n2 == "21":                          return "Culturas_temporarias"
    if n2 == "22":                          return "Culturas_permanentes"
    if n2 == "23":                          return "Culturas_associadas"
    if n2 == "24":                          return "Estufas"
    if n2.startswith("4"):                  return "Montado_SAF"
    if n2.startswith("5"):                  return "Floresta"
    if n2.startswith("6"):                  return "Matos"
    if n4.startswith("1.1.1"):              return "Urbano_denso"
    if n4.startswith("1.1.2"):              return "Urbano_disperso"
    if n2 == "15":                          return "Estradas"
    if n2 in ("16", "17"):                  return "Extracao_solo_nu"
    if n2.startswith("1"):                  return "Artificial_outros"
    return "Pastagens"   # classe desconhecida: valor intermédio

tmp = r"memory\cos_lc"
arcpy.management.CopyFeatures(src, tmp)
arcpy.management.AddField(tmp, "LC_NOME", "TEXT", field_length=30)
arcpy.management.AddField(tmp, "MANNING", "DOUBLE")
cont = {}
with arcpy.da.UpdateCursor(tmp, ["cos25v1_n4", "cos25v1_n2", "LC_NOME", "MANNING", "SHAPE@AREA"]) as cur:
    for n4, n2, _, _, a in cur:
        g = grupo(n4, n2)
        cur.updateRow([n4, n2, g, GRUPOS[g], a])
        cont[g] = cont.get(g, 0.0) + a

print("A agregar por grupo (Dissolve)...")
arcpy.analysis.PairwiseDissolve(tmp, out, ["LC_NOME", "MANNING"], multi_part="MULTI_PART")

with open(tab, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["LC_NOME", "MANNING", "area_km2"])
    for g, a in sorted(cont.items(), key=lambda kv: -kv[1]):
        w.writerow([g, GRUPOS[g], round(a / 1e6, 2)])
        print(f"{g:22s} n={GRUPOS[g]:.3f}  {a/1e6:8.1f} km2")
print("Feito:", out)
