# -*- coding: utf-8 -*-
"""16_cena3d_dados.py — dados para a cena 3D animada do cenário B1.

Janela Python do ArcGIS Pro (tem arcpy e h5py), com o projeto rotura-alqueva.aprx aberto e o HEC-RAS fechado:
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\16_cena3d_dados.py", encoding="utf-8").read())

O que faz:
 1. lê do rotura_alqueva.p13.hdf a geometria das células (Perimeter 1 + Albufeira) e a cota da água de 10 em 10 min;
 2. rasteriza o n.º de cada célula a 30 m (uma vez) e o terreno da cena a 30 m
    (prioridade: fundo de Pedrógão > canal do estuário > SRTM da albufeira > LiDAR 10 m);
 3. para cada instante (de 20 em 20 min, 0 a 24 h depois da rotura de Alqueva) calcula profundidade = cota da água − terreno
    e grava resultados\\p13\\cena3d\\frames\\prof_tMMMM.tif (MMMM = minutos após a rotura);
 4. junta tudo num mosaico com tempo (b1.gdb\\profundidade_tempo, campo TEMPO) e cria a cena "B1_cena3d".
Depois: passos no ecrã em docs\\passos_cena3d.md (superfície de elevação, câmara, animação, vídeo).
"""
import os, time, datetime, numpy as np, h5py, arcpy

T0 = time.time()
def t(msg): print(f"[{time.time() - T0:6.1f} s] {msg}")

base = r"C:\caminho\para\rotura-alqueva"
hdf = os.path.join(base, r"hecras\rotura_alqueva.p13.hdf")
out = os.path.join(base, r"resultados\p13\cena3d")
frames = os.path.join(out, "frames")
os.makedirs(frames, exist_ok=True)
gdb = os.path.join(base, r"resultados\p13\mapas\b1.gdb")
sr = arcpy.SpatialReference(25829)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False
arcpy.env.outputCoordinateSystem = sr
arcpy.CheckOutExtension("Spatial")

CEL = 30.0                       # resolução da animação (m)
PASSO = 2                        # de 2 em 2 registos de 10 min = 20 min
I_ROTURA = 48                    # 01JAN 01:00 + 8 h = 09:00 (registo 48)
N_HORAS = 24
ROTURA = datetime.datetime(2026, 1, 1, 9, 0)

# ---------------- 1. HDF
t("1. A ler o HDF...")
f = h5py.File(hdf, "r")
G = "Geometry/2D Flow Areas/"
R = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/"
polis, wse_blocos, off = [], [], 0
for area in ["Perimeter 1", "Albufeira"]:
    fp = f[G + area + "/FacePoints Coordinate"][()]
    idx = f[G + area + "/Cells FacePoint Indexes"][()]
    wse = f[R + area + "/Water Surface"]
    for i, row in enumerate(idx):
        v = row[row >= 0]
        if len(v) >= 3:
            polis.append((off + i, fp[v]))
    wse_blocos.append((off, wse))
    off += idx.shape[0]
n_tempos = f[R + "Perimeter 1/Water Surface"].shape[0]
t(f"1. {len(polis):,} células com geometria; {n_tempos} registos de tempo")

# ---------------- 2. células → raster de n.º de célula
t("2. Polígonos das células...")
cel_fc = os.path.join(gdb, "celulas_malha")
arcpy.management.CreateFeatureclass(gdb, "celulas_malha", "POLYGON", spatial_reference=sr)
arcpy.management.AddField(cel_fc, "CID", "LONG")
with arcpy.da.InsertCursor(cel_fc, ["CID", "SHAPE@"]) as c:
    for cid, xy in polis:
        c.insertRow([cid, arcpy.Polygon(arcpy.Array([arcpy.Point(x, y) for x, y in xy]), sr)])
d = arcpy.Describe(cel_fc).extent
xmin = np.floor(d.XMin / CEL) * CEL; ymin = np.floor(d.YMin / CEL) * CEL
xmax = np.ceil(d.XMax / CEL) * CEL;  ymax = np.ceil(d.YMax / CEL) * CEL
arcpy.env.extent = arcpy.Extent(xmin, ymin, xmax, ymax)
arcpy.env.snapRaster = None
cid_tif = os.path.join(out, "cid_30m.tif")
arcpy.conversion.PolygonToRaster(cel_fc, "CID", cid_tif, "CELL_CENTER", "", CEL)
ll = arcpy.Point(xmin, ymin)
NC, NR = int(round((xmax - xmin) / CEL)), int(round((ymax - ymin) / CEL))
CID = arcpy.RasterToNumPyArray(cid_tif, ll, NC, NR, nodata_to_value=-1).astype(np.int64)
t(f"2. raster de células {CID.shape}")

# ---------------- terreno da cena (30 m para a animação; 20 m para a superfície de elevação)
t("3. Terreno da cena...")
fontes = [os.path.join(base, r"dados\terreno\srtm_pedrogao_25829_10m.tif"),
          os.path.join(base, r"dados\terreno\canal_estuario_25829_10m.tif"),
          os.path.join(base, r"dados\srtm\srtm_albufeira_25829_30m.tif"),
          os.path.join(base, r"dados\terreno\terreno_10m_final.tif")]
arcpy.env.snapRaster = cid_tif
for cel, nome in [(CEL, "terreno_cena_30m.tif"), (20, "terreno_cena_20m.tif")]:
    arcpy.management.MosaicToNewRaster(fontes, out, nome, sr, "32_BIT_FLOAT", cel, 1, "FIRST")
TER = arcpy.RasterToNumPyArray(os.path.join(out, "terreno_cena_30m.tif"), ll, NC, NR, nodata_to_value=np.nan).astype(np.float32)
assert TER.shape == CID.shape, (TER.shape, CID.shape)
valido = CID >= 0
t("3. feito")

# ---------------- 4. imagens de profundidade
t("4. Imagens de profundidade...")
WS = np.full(off, np.nan, np.float32)
idxs = list(range(I_ROTURA, min(I_ROTURA + N_HORAS * 6 + 1, n_tempos), PASSO))
for k, it in enumerate(idxs):
    for o, ds in wse_blocos:
        WS[o:o + ds.shape[1]] = ds[it, :]
    prof = np.full(CID.shape, np.nan, np.float32)
    prof[valido] = WS[CID[valido]] - TER[valido]
    prof[~(prof > 0.05)] = np.nan
    minutos = (it - I_ROTURA) * 10
    r = arcpy.NumPyArrayToRaster(prof, ll, CEL, CEL, np.nan)
    arcpy.management.CopyRaster(r, os.path.join(frames, f"prof_t{minutos:04d}.tif"), nodata_value="-9999",
                                pixel_type="32_BIT_FLOAT", format="TIFF")
    if k % 12 == 0:
        t(f"   {minutos / 60:4.1f} h — área molhada {np.isfinite(prof).sum() * CEL * CEL / 1e4:,.0f} ha")
f.close()
arcpy.ClearEnvironment("extent")
t(f"4. {len(idxs)} imagens")

# ---------------- 5. mosaico com tempo
t("5. Mosaico com tempo...")
md = os.path.join(gdb, "profundidade_tempo")
if arcpy.Exists(md):
    arcpy.management.Delete(md)
arcpy.management.CreateMosaicDataset(gdb, "profundidade_tempo", sr, 1, "32_BIT_FLOAT")
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
t("5. feito")

# ---------------- 6. cena
t("6. Cena 3D...")
aprx = arcpy.mp.ArcGISProject("CURRENT")
for m_ in aprx.listMaps("B1_cena3d"):
    aprx.deleteItem(m_)
try:
    cena = aprx.createMap("B1_cena3d", "LOCAL_SCENE")
except Exception:
    cena = aprx.createMap("B1_cena3d", "SCENE")
cena.spatialReference = sr
lp = cena.addDataFromPath(md); lp.name = "Profundidade (m) — 20 em 20 min"
try:
    sym = lp.symbology
    sym.updateColorizer("RasterClassifyColorizer")
    sym.colorizer.classificationMethod = "ManualInterval"
    sym.colorizer.breakCount = 7
    cores = [(222, 235, 247), (198, 219, 239), (158, 202, 225), (107, 174, 214), (66, 146, 198), (33, 113, 181), (8, 69, 148)]
    for brk, ub, lb, c_ in zip(sym.colorizer.classBreaks, [0.5, 1, 2, 5, 10, 20, 999],
                               ["≤ 0,5", "0,5 – 1", "1 – 2", "2 – 5", "5 – 10", "10 – 20", "> 20"], cores):
        brk.upperBound = ub; brk.label = lb; brk.color = {"RGB": list(c_) + [100]}
    lp.symbology = sym
except Exception as e:
    print("   (cores da profundidade à mão)", e)
try:
    lp.enableTime("TEMPO", "TEMPO")
except Exception as e:
    print("   (ativar o tempo da camada à mão: Properties → Time)", e)
lc = cena.addDataFromPath(os.path.join(gdb, "localidades")); lc.showLabels = True
aprx.save()
t("Feito. Próximo: docs\\passos_cena3d.md (superfície de elevação, câmara, animação, vídeo)")
