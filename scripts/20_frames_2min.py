# -*- coding: utf-8 -*-
"""20_frames_2min.py - imagens de profundidade de 2 em 2 min (interpoladas) para a animação B1 ficar fluida.

Problema: com imagens de 20 em 20 min, nos 50 s de vídeo a água muda aos saltos (cerca de 1,4 imagens por segundo).
Solução: interpolar linearmente a cota da água entre os registos de 10 min do HDF e gerar uma imagem a cada 2 min
(721 imagens, 0 a 24 h). A câmara e as horas dos keyframes não mudam.

Janela Python do ArcGIS Pro, com o projeto aberto e o HEC-RAS fechado:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\20_frames_2min.py", encoding="utf-8").read())
Demora ~20-40 min. No fim: fechar o Pro SEM guardar, reabrir o projeto, ver a animação, exportar.

O que faz:
 1. lê do p13.hdf a cota da água das células (Perimeter 1 + Albufeira), como o script 16;
 2. reaproveita cid_30m.tif e terreno_cena_30m.tif do script 16;
 3. grava resultados\\p13\\cena3d\\frames_2min\\prof_tMMMM.tif (a pasta frames\\ de 20 min fica intacta);
 4. cria o mosaico b1.gdb\\profundidade_2min (tempo no campo TEMPO; a imagem mais recente fica por cima);
 5. troca a fonte da camada de profundidade da cena (mantém cores e tempo) e põe a janela dos keyframes em 2 min.
"""
import os, time, datetime, numpy as np, h5py, arcpy

T0 = time.time()
def t(msg): print(f"[{time.time() - T0:6.1f} s] {msg}")

base = r"C:\caminho\para\rotura-alqueva"
hdf = os.path.join(base, r"hecras\rotura_alqueva.p13.hdf")
out = os.path.join(base, r"resultados\p13\cena3d")
frames = os.path.join(out, "frames_2min")
os.makedirs(frames, exist_ok=True)
gdb = os.path.join(base, r"resultados\p13\mapas\b1.gdb")
sr = arcpy.SpatialReference(25829)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False

CEL = 30.0
PASSO_MIN = 2                   # minutos entre imagens
I_ROTURA = 48                   # registo do HDF às 09:00 (10 em 10 min)
N_HORAS = 24
ROTURA = datetime.datetime(2026, 1, 1, 9, 0)

# ---------------- 1. HDF
t("1. A ler o HDF...")
f = h5py.File(hdf, "r")
G = "Geometry/2D Flow Areas/"
R = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/"
blocos, off = [], 0
for area in ["Perimeter 1", "Albufeira"]:
    n = f[G + area + "/Cells FacePoint Indexes"].shape[0]
    blocos.append((off, f[R + area + "/Water Surface"]))
    off += n
n_tempos = blocos[0][1].shape[0]
t(f"1. {off:,} células; {n_tempos} registos")

_cache = {}
def ws(i):
    """cota da água de todas as células no registo i (com cache dos últimos registos)."""
    if i not in _cache:
        v = np.full(off, np.nan, np.float32)
        for o, ds in blocos:
            v[o:o + ds.shape[1]] = ds[i, :]
        if len(_cache) > 3:
            _cache.pop(min(_cache))
        _cache[i] = v
    return _cache[i]

# ---------------- 2. grelha e terreno do script 16
t("2. Grelha e terreno...")
cid_tif = os.path.join(out, "cid_30m.tif")
d = arcpy.Describe(cid_tif).extent
ll = arcpy.Point(d.XMin, d.YMin)
NC = int(round((d.XMax - d.XMin) / CEL)); NR = int(round((d.YMax - d.YMin) / CEL))
CID = arcpy.RasterToNumPyArray(cid_tif, ll, NC, NR, nodata_to_value=-1).astype(np.int64)
TER = arcpy.RasterToNumPyArray(os.path.join(out, "terreno_cena_30m.tif"), ll, NC, NR,
                               nodata_to_value=np.nan).astype(np.float32)
assert TER.shape == CID.shape, (TER.shape, CID.shape)
valido = CID >= 0
cidv = CID[valido]; terv = TER[valido]
t(f"2. grelha {CID.shape}")

# ---------------- 3. imagens interpoladas
t("3. Imagens de 2 em 2 min (721)...")
ultimo = n_tempos - 1
for minutos in range(0, N_HORAS * 60 + 1, PASSO_MIN):
    nome = os.path.join(frames, f"prof_t{minutos:04d}.tif")
    if os.path.exists(nome):        # permite retomar se for interrompido
        continue
    i0 = I_ROTURA + minutos // 10
    fr = (minutos % 10) / 10.0
    i0 = min(i0, ultimo); i1 = min(i0 + 1, ultimo)
    w = ws(i0) if fr == 0 else ws(i0) * (1 - fr) + ws(i1) * fr
    prof = np.full(CID.shape, np.nan, np.float32)
    prof[valido] = w[cidv] - terv
    prof[~(prof > 0.05)] = np.nan
    r = arcpy.NumPyArrayToRaster(prof, ll, CEL, CEL, np.nan)
    arcpy.management.CopyRaster(r, nome, nodata_value="-9999", pixel_type="32_BIT_FLOAT", format="TIFF")
    if minutos % 120 == 0:
        t(f"   {minutos / 60:4.1f} h — área molhada {np.isfinite(prof).sum() * CEL * CEL / 1e4:,.0f} ha")
f.close()
t("3. feito")

# ---------------- 4. mosaico
t("4. Mosaico profundidade_2min...")
md = os.path.join(gdb, "profundidade_2min")
if arcpy.Exists(md):
    arcpy.management.Delete(md)
arcpy.management.CreateMosaicDataset(gdb, "profundidade_2min", sr, 1, "32_BIT_FLOAT")
arcpy.management.AddRastersToMosaicDataset(md, "Raster Dataset", frames, "UPDATE_CELL_SIZES", "UPDATE_BOUNDARY",
                                           "NO_OVERVIEWS", None, 0, 1500, None, "*.tif")
arcpy.management.AddField(md, "TEMPO", "DATE")
arcpy.management.AddField(md, "MIN_APOS", "LONG")
with arcpy.da.UpdateCursor(md, ["Name", "TEMPO", "MIN_APOS"]) as c:
    for nome, _, _ in c:
        mm = int(nome.split("_t")[1][:4])
        c.updateRow([nome, ROTURA + datetime.timedelta(minutes=mm), mm])
arcpy.management.SetMosaicDatasetProperties(md, start_time_field="TEMPO", end_time_field="TEMPO",
                                            use_time="ENABLED", time_format="YYYY-MM-DD HH:mm:ss")
try:  # se a janela de tempo apanhar 2 imagens, mostra a mais recente
    arcpy.management.SetMosaicDatasetProperties(md, allowed_mosaic_methods="ByAttribute;None;Center;NorthWest",
                                                default_mosaic_method="ByAttribute", order_field="MIN_APOS",
                                                sorting_order="DESCENDING")
except Exception as e:
    print("   (método de mosaico por atributo não aplicado:", e, ")")
arcpy.management.CalculateStatistics(md, 1, 1, "", "OVERWRITE")
t("4. feito")

# ---------------- 5. cena: trocar a fonte da camada e janela dos keyframes
t("5. Cena...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
cena = aprx.listMaps("B1_cena3d")[0]
lyr = [l for l in cena.listLayers() if l.name.startswith("Profundidade (m)")][0]
try:
    cp = lyr.connectionProperties
    novo = dict(cp); novo["dataset"] = "profundidade_2min"
    lyr.updateConnectionProperties(cp, novo)
    lyr.name = "Profundidade (m) — 2 em 2 min"
    print("   camada ligada a", arcpy.Describe(lyr).catalogPath)
except Exception as e:
    print("   (trocar a fonte à mão: botão direito na camada -> Data -> Set Data Source -> profundidade_2min)", e)

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
t(f"Feito: {n_kf} keyframes com janela de {PASSO_MIN} min; projeto gravado. "
  "Fecha o Pro SEM guardar, reabre e vê a animação.")
