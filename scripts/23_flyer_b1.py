# -*- coding: utf-8 -*-
"""23_flyer_b1.py — flyer A4 vertical do cenário B1 (portefólio / LinkedIn), feito numa layout do ArcGIS Pro.

Janela Python do ArcGIS Pro, com o projeto rotura-alqueva.aprx aberto (depois do script 15, que cria os
recortes chegada_h_rotura.tif, relevo_sombreado.tif, isocrona_30min e localidades):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\23_flyer_b1.py", encoding="utf-8").read())

Cria o mapa "Flyer_B1_mapa" e a layout "Flyer_B1" (A4 vertical) e exporta para resultados\\p13\\flyer\\:
  Flyer_B1.pdf (300 dpi), Flyer_B1.png (300 dpi) e Flyer_B1_linkedin.jpg (150 dpi).
Tudo fica editável no projeto (textos, posições, cores). A imagem 3D é resultados\\p13\\flyer\\imagem_3d.png:
substitui o ficheiro por outro fotograma e volta a correr (ou troca a imagem à mão na layout).
Não mexe nos mapas/layouts B1_* (os do script 15).
"""
import os, arcpy

base = r"C:\caminho\para\rotura-alqueva"
mapas = os.path.join(base, r"resultados\p13\mapas")
gdb = os.path.join(mapas, "b1.gdb")
pasta = os.path.join(base, r"resultados\p13\flyer")
os.makedirs(pasta, exist_ok=True)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False
aprx = arcpy.mp.ArcGISProject("CURRENT")
sr = arcpy.SpatialReference(25829)

NOME_MAPA, NOME_LYT = "Flyer_B1_mapa", "Flyer_B1"
FONTE = "Segoe UI"
AZUL = (11, 37, 69)            # faixa do título
MAGENTA = (80, 18, 123)        # cor dos números (= classe mais rápida da chegada)
CINZA = (90, 90, 90)
EXT = arcpy.Extent(596000, 4098000, 664000, 4238000)   # vale de Alqueva à foz + margem de mar a sul (para os créditos do mapa base)

for it in aprx.listLayouts("Flyer_*") + aprx.listMaps("Flyer_*") + aprx.listLayouts("TMP_*") + aprx.listMaps("TMP_*"):
    aprx.deleteItem(it)
# o primeiro layout criado depois de apagar itens fica com a moldura sem ligação (defeito do ArcGIS)
_tm = aprx.createMap("TMP_descartavel", "MAP")
_tl = aprx.createLayout(100, 100, "MILLIMETER", "TMP_descartavel")
_tl.createMapFrame(arcpy.Extent(5, 5, 95, 95), _tm, "tmp")


def rgb(r, g, b, a=100): return {"RGB": [r, g, b, a]}


# ---------------- mapa: tempo de chegada
print("1/3 Mapa...")
m = aprx.createMap(NOME_MAPA, "MAP")
m.spatialReference = sr
# mapa base neutro (Light Gray, sem a camada de rótulos) em vez do mapa base por defeito
for l in m.listLayers():
    if l.isBasemapLayer:
        m.removeLayer(l)
try:
    m.addBasemap("Light Gray Canvas")
    for l in m.listLayers():
        if "Reference" in l.name or "Referência" in l.name:
            m.removeLayer(l)
except Exception as e:
    print("   (mapa base Light Gray à mão)", e)
lr = m.addDataFromPath(os.path.join(mapas, "relevo_sombreado.tif")); lr.name = "Relevo"
try:
    s = lr.symbology; s.updateColorizer("RasterStretchColorizer"); s.colorizer.stretchType = "MinimumMaximum"
    rampa = aprx.listColorRamps("Black to White") or aprx.listColorRamps("Gray*")
    if rampa: s.colorizer.colorRamp = rampa[0]
    lr.symbology = s
except Exception as e:
    print("   (relevo: Stretch + Black to White à mão)", e)
lr.transparency = 55
la = m.addDataFromPath(os.path.join(gdb, "agua_antes_rotura")); la.name = "Água antes da rotura"
s = la.symbology; s.renderer.symbol.color = rgb(190, 205, 215); s.renderer.symbol.outlineColor = rgb(0, 0, 0, 0); la.symbology = s
lch = m.addDataFromPath(os.path.join(mapas, "chegada_h_rotura.tif")); lch.name = "Chegada da onda (horas após a rotura)"
s = lch.symbology
s.updateColorizer("RasterClassifyColorizer")
s.colorizer.classificationMethod = "ManualInterval"
s.colorizer.breakCount = 7
for brk, ub, lb, cor in zip(s.colorizer.classBreaks, [0.5, 1, 2, 4, 8, 12, 999],
                            ["até 30 min", "30 min – 1 h", "1 – 2 h", "2 – 4 h", "4 – 8 h", "8 – 12 h", "12 – 24 h"],
                            [(80, 18, 123), (129, 37, 129), (181, 54, 122), (229, 80, 100), (251, 135, 97), (254, 194, 135), (252, 253, 191)]):
    brk.upperBound = ub; brk.label = lb; brk.color = rgb(*cor)
s.colorizer.noDataColor = rgb(0, 0, 0, 0)
lch.symbology = s
li = m.addDataFromPath(os.path.join(gdb, "isocrona_30min")); li.name = "Atingido nos primeiros 30 min"
s = li.symbology; s.renderer.symbol.color = rgb(0, 0, 0, 0); s.renderer.symbol.outlineColor = rgb(0, 0, 0); s.renderer.symbol.outlineWidth = 1.0
li.symbology = s
lc = m.addDataFromPath(os.path.join(gdb, "localidades")); lc.name = "Localidades"
s = lc.symbology; s.renderer.symbol.size = 4; s.renderer.symbol.color = rgb(30, 30, 30); lc.symbology = s
lc.showLabels = True
lc.listLabelClasses()[0].expression = "$feature.NOME"
try:
    cim = lc.getDefinition("V3")
    ts = cim.labelClasses[0].textSymbol.symbol
    ts.height = 6.5; ts.fontFamilyName = FONTE; ts.fontStyleName = "Semibold"
    cor = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3"); cor.values = [255, 255, 255, 100]
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3"); fill.color = cor; fill.enable = True
    halo = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3"); halo.symbolLayers = [fill]
    ts.haloSymbol = halo; ts.haloSize = 1.0
    lc.setDefinition(cim)
except Exception as e:
    print("   (halo dos rótulos à mão)", e)


# ---------------- utilitários da layout
def texto(lyt, x, y, t, tam, negrito=False, cor=(20, 20, 20), nome=None):
    el = aprx.createTextElement(lyt, arcpy.Point(x, y), "POINT", t, tam, name=nome)
    try:
        el.fontFamilyName = FONTE
        el.fontStyleName = "Bold" if negrito else "Regular"
    except Exception:
        pass
    try:
        cim = el.getDefinition("V3")
        cim.graphic.symbol.symbol.symbol.symbolLayers[0].color.values = [cor[0], cor[1], cor[2], 100]
        el.setDefinition(cim)
    except Exception as e:
        print("   (cor do texto '%s' à mão)" % (nome or t[:20]), e)
    return el


def caixa(lyt, x0, y0, x1, y1, cor, nome, contorno=None):
    pol = arcpy.Polygon(arcpy.Array([arcpy.Point(x0, y0), arcpy.Point(x0, y1), arcpy.Point(x1, y1), arcpy.Point(x1, y0), arcpy.Point(x0, y0)]))
    try:
        el = aprx.createGraphicElement(lyt, pol, name=nome)
    except Exception as e:
        print("   (retângulo '%s' à mão)" % nome, e); return None
    try:
        cim = el.getDefinition("V3")
        camadas = cim.graphic.symbol.symbol.symbolLayers
        for sl in camadas:
            if type(sl).__name__ == "CIMSolidFill":
                sl.color.values = [cor[0], cor[1], cor[2], 100]
            if type(sl).__name__ == "CIMSolidStroke":
                if contorno:
                    sl.color.values = [contorno[0], contorno[1], contorno[2], 100]; sl.width = 0.5
                else:
                    sl.enable = False
        el.setDefinition(cim)
    except Exception as e:
        print("   (cor do retângulo '%s' à mão)" % nome, e)
    return el


# ---------------- layout A4
print("2/3 Layout...")
lyt = aprx.createLayout(210, 297, "MILLIMETER", NOME_LYT)
caixa(lyt, 0, 250, 210, 297, AZUL, "Faixa_titulo")
caixa(lyt, 0, 0, 210, 15, (238, 238, 238), "Faixa_rodape")

mf = lyt.createMapFrame(arcpy.Extent(8, 20, 116, 244), m, "Mapa")
mf.map = m
mf.camera.setExtent(EXT)

texto(lyt, 10, 280, "E se a barragem de Alqueva rompesse?", 25, True, (255, 255, 255), "Titulo")
texto(lyt, 10, 270.5, "Simulação hidráulica 2D de um cenário hipotético: a onda de cheia do Alqueva ao mar, em 24 horas",
      9.5, False, (225, 232, 240), "Subtitulo")
texto(lyt, 10, 262, "HEC-RAS 7.0.2  ·  ArcGIS Pro 3.6  ·  Python  ·  só dados abertos", 8.5, True, (150, 190, 225), "Ferramentas")

# imagem 3D
img = os.path.join(pasta, "imagem_3d.png")
if os.path.exists(img):
    try:
        aprx.createPictureElement(lyt, arcpy.Extent(122, 199, 202, 244), img, "Imagem_3D")
    except Exception as e:
        print("   (imagem 3D à mão: Insert -> Picture)", e)
texto(lyt, 122, 195, "Animação 3D (ArcGIS Pro): a onda a descer o vale do Guadiana", 6.5, False, CINZA, "Legenda_imagem")

# números
NUM = [("22 631 ha", "inundados pela onda da rotura"),
       ("~28 800", "residentes em zona inundada (Portugal + Espanha)"),
       ("210 000 m³/s", "caudal máximo à saída de Alqueva"),
       ("10 351 ha", "com perigosidade extrema (h·v > 4 m²/s)")]
for k, (n, t) in enumerate(NUM):
    y = 181 - k * 19
    texto(lyt, 122, y, n, 19, True, MAGENTA, "Num_%d" % k)
    texto(lyt, 122, y - 5.5, t, 7.5, False, (40, 40, 40), "Num_txt_%d" % k)

# chegadas
texto(lyt, 122, 101, "Quando chega a onda", 11, True, AZUL, "Chegadas_titulo")
CHEG = [("Pedrógão", "0 h 42"), ("Mértola", "4 h 18"), ("Alcoutim", "7 h 12"), ("Vila Real de Santo António", "11 h 30")]
for k, (n, h) in enumerate(CHEG):
    y = 94 - k * 6
    texto(lyt, 122, y, n, 8.5, False, (40, 40, 40), "Cheg_n_%d" % k)
    texto(lyt, 186, y, h, 8.5, True, MAGENTA, "Cheg_h_%d" % k)
texto(lyt, 122, 70, "horas após a rotura de Alqueva (subida da água ≥ 0,3 m)", 6.5, False, CINZA, "Cheg_nota")

# como foi feito
# (os textos de várias linhas crescem para cima a partir do ponto de inserção)
texto(lyt, 122, 52, "Como foi feito", 11, True, AZUL, "Metodo_titulo")
texto(lyt, 122, 21,
      "•  Terreno: LiDAR (DGT), MDT (CNIG) e SRTM\n"
      "•  Rugosidade: COS 2025 (DGT)\n"
      "•  Modelo hidráulico 2D: HEC-RAS 7.0.2\n"
      "•  Validação: níveis do PEExt (±3 m até ao km 55)\n"
      "•  Exposição: Censos 2021 (INE), grelha JRC 2021,\n"
      "    Catastro (Espanha)\n"
      "•  Mapas, cena 3D e vídeo: ArcGIS Pro + Python",
      7.5, False, (40, 40, 40), "Metodo")

try:
    sb = aprx.listStyleItems("ArcGIS 2D", "SCALE_BAR", "Scale Line 1 Metric")[0]
    e_ = lyt.createMapSurroundElement(arcpy.Point(12, 234), "SCALE_BAR", mf, sb, "Escala"); e_.elementWidth = 35
    try:
        c_ = e_.getDefinition("V3"); c_.unitLabel = "km"; e_.setDefinition(c_)
    except Exception:
        pass
    try:   # 0 – 5 – 10 km, sem subdivisões
        c_ = e_.getDefinition("V3")
        c_.fittingStrategy = "AdjustFrame"; c_.division = 5; c_.divisions = 2; c_.subdivisions = 0
        e_.setDefinition(c_)
    except Exception as e:
        print("   (divisões da escala à mão)", e)
    na = aprx.listStyleItems("ArcGIS 2D", "NORTH_ARROW", "ArcGIS North 1")[0]
    n_ = lyt.createMapSurroundElement(arcpy.Point(106, 228), "NORTH_ARROW", mf, na, "Norte"); n_.elementHeight = 12
except Exception as e:
    print("   (escala/norte à mão)", e)

texto(lyt, 10, 10, "Cenário hipotético, para estudo e portefólio, feito só com dados abertos. "
                   "Não é um plano de emergência e não substitui o PEExt de Alqueva.", 6.5, False, (60, 60, 60), "Aviso")
texto(lyt, 10, 5, "ETRS89 / UTM 29N  ·  rotura em série de Alqueva e Pedrógão (cenário B1)", 6, False, CINZA, "Ref")
texto(lyt, 150, 5, "Gustavo Santa · 2026  ·  gustavosanta-star.github.io", 6.5, True, AZUL, "Autor")

# ---------------- gravar, religar e exportar
print("3/3 Exportar...")
aprx.save()
aprx = arcpy.mp.ArcGISProject("CURRENT")
lyt = aprx.listLayouts(NOME_LYT)[-1]
mp = [m_ for m_ in aprx.listMaps(NOME_MAPA) if len(m_.listLayers()) > 0][-1]
for f in lyt.listElements("MAPFRAME_ELEMENT"):
    f.map = mp
cim = lyt.getDefinition("V3")
for e in cim.elements:
    if type(e).__name__ == "CIMMapFrame":
        e.uRI = mp.getDefinition("V3").uRI
lyt.setDefinition(cim)
for f in lyt.listElements("MAPFRAME_ELEMENT"):
    f.camera.setExtent(EXT)


def legenda(lyt, mf):
    """Legenda só com a chegada, os 30 min e a água; sem relevo, mapa base nem cabeçalhos repetidos."""
    for e in lyt.listElements("LEGEND_ELEMENT"):
        lyt.deleteElement(e)
    try:
        st = aprx.listStyleItems("ArcGIS 2D", "LEGEND", "Legend 1")[0]
        leg = lyt.createMapSurroundElement(arcpy.Point(10, 92), "LEGEND", mf, st, "Legenda")
        leg.title = "Chegada da onda"
        cim = leg.getDefinition("V3")
        manter = ("Chegada", "Atingido", "Água")
        cim.items = [it for it in cim.items if str(it.name).startswith(manter)]
        for it in cim.items:
            for att in ("showHeading", "showLayerName", "showGroupLayerName"):
                if hasattr(it, att):
                    setattr(it, att, False)
            for att in ("labelSymbol", "layerNameSymbol", "headingSymbol"):
                try: getattr(it, att).symbol.height = 7.5
                except Exception: pass
        try: cim.titleSymbol.symbol.height = 9.5
        except Exception: pass
        try: cim.autoAdd = False
        except Exception: pass
        leg.setDefinition(cim)
        leg.elementWidth = 38
    except Exception as e:
        print("   (legenda à mão)", e)


legenda(lyt, lyt.listElements("MAPFRAME_ELEMENT")[0])
lyt.exportToPDF(os.path.join(pasta, NOME_LYT + ".pdf"), resolution=300)
lyt.exportToPNG(os.path.join(pasta, NOME_LYT + ".png"), resolution=300)
lyt.exportToJPEG(os.path.join(pasta, NOME_LYT + "_linkedin.jpg"), resolution=150, jpeg_quality=92)
for it in aprx.listLayouts("TMP_*") + aprx.listMaps("TMP_*"):
    aprx.deleteItem(it)
aprx.save()
print("Feito: layout Flyer_B1 no projeto; PDF, PNG e JPG em", pasta)
