# -*- coding: utf-8 -*-
"""15_layouts_b1.py — quatro layouts A3 do cenário B1 (rotura hipotética de Alqueva + Pedrógão).

Janela Python do ArcGIS Pro, com o projeto rotura-alqueva.aprx aberto (depois do 13, 13b e 14):
    exec(open(r"C:\\caminho\\para\\rotura-alqueva\\scripts\\15_layouts_b1.py", encoding="utf-8").read())

Cria no projeto 4 mapas + 4 layouts (B1_1 … B1_4) e exporta PDF (300 dpi) e PNG (200 dpi) para resultados\\p13\\layouts\\.
Decisões cartográficas (fixas e iguais nos quatro):
  • sem mapa base (fundo = relevo); seta do norte no canto superior direito do mapa; escala em km;
  • legenda só com as camadas temáticas (sem relevo, sem cabeçalhos repetidos), refeita depois de religar as molduras;
  • ETRS89 / UTM 29N (EPSG 25829); A3 vertical; escala 1:325 000; mesmo enquadramento;
  • relevo sombreado do terreno de 10 m como fundo; água que já existia às 09:00 a cinzento-azulado (não é inundação);
  • rasters recortados à área inundada pela rotura; classes definidas (não Jenks) com limiares com significado:
      profundidade 0–0,5 / 0,5–1 / 1–2 / 2–5 / 5–10 / 10–20 / >20 m (azuis sequenciais);
      h·v ≤0,3 / 0,3–0,6 / 0,6–1 / 1–4 / >4 m²/s (classes ARR 2019 simplificadas; amarelo→vermelho escuro);
      chegada ≤0,5 / 0,5–1 / 1–2 / 2–4 / 4–8 / 8–12 / 12–24 h (magenta escuro = chega primeiro → amarelo claro);
  • rampas legíveis por daltónicos (ColorBrewer Blues, YlOrRd; magma invertido).
Depois de correr, tudo fica editável no projeto (afinar à mão o que quiser).
"""
import os, csv, arcpy
from arcpy.sa import Raster, ExtractByMask, Hillshade

base = r"C:\caminho\para\rotura-alqueva"
mapas = os.path.join(base, r"resultados\p13\mapas")
gdb = os.path.join(mapas, "b1.gdb")
saida = os.path.join(base, r"resultados\p13\layouts")
os.makedirs(saida, exist_ok=True)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False          # não encher o mapa "Map" com resultados intermédios
arcpy.env.compression = "LZ77"
arcpy.CheckOutExtension("Spatial")
aprx = arcpy.mp.ArcGISProject("CURRENT")
# apagar já os layouts e mapas B1_ antigos (se forem apagados depois, as molduras novas ficam sem mapa)
for l in aprx.listLayouts("B1_*"):
    aprx.deleteItem(l)
for m_ in aprx.listMaps("B1_*"):
    aprx.deleteItem(m_)
for it in aprx.listLayouts("TMP_*") + aprx.listMaps("TMP_*"):
    aprx.deleteItem(it)
# o primeiro layout criado depois de apagar itens fica com a moldura sem ligação (defeito do ArcGIS);
# cria-se um layout descartável que absorve o problema e apaga-se no fim
_tmp_m = aprx.createMap("TMP_descartavel", "MAP")
_tmp_l = aprx.createLayout(100, 100, "MILLIMETER", "TMP_descartavel")
_tmp_l.createMapFrame(arcpy.Extent(5, 5, 95, 95), _tmp_m, "tmp")
sr = arcpy.SpatialReference(25829)
inund_rot = os.path.join(gdb, "area_inundada_rotura")
agua_0900 = os.path.join(gdb, "agua_antes_rotura")

# ---------------- dados de apoio
print("1/4 Dados de apoio (recortes, relevo, localidades)...")
rec = {}
for nome in ["profundidade_max", "hv_max", "chegada_h"]:
    out = os.path.join(mapas, nome + "_rotura.tif")
    ExtractByMask(Raster(os.path.join(mapas, nome + ".tif")), inund_rot).save(out)
    rec[nome] = out
relevo = os.path.join(mapas, "relevo_sombreado.tif")
if not arcpy.Exists(relevo):
    Hillshade(os.path.join(base, r"dados\terreno\terreno_10m_final.tif"), 315, 45, "NO_SHADOWS", 2).save(relevo)

loc = os.path.join(gdb, "localidades")
LOC = [("Barragem de Alqueva", 631781, 4228790), ("Barragem de Pedrógão", 620071, 4218965),
       ("Pulo do Lobo", 620330, 4185037), ("Mértola", 618075, 4166660), ("Pomarão", 630214, 4157398),
       ("Alcoutim", 635116, 4148220), ("Sanlúcar de Guadiana", 635565, 4148361), ("Foz de Odeleite", 637223, 4133050),
       ("Castro Marim", 638108, 4120202), ("Vila Real de Santo António", 640645, 4117636), ("Ayamonte", 641356, 4119724)]
arcpy.management.CreateFeatureclass(gdb, "localidades", "POINT", spatial_reference=sr)
arcpy.management.AddField(loc, "NOME", "TEXT", field_length=40)
with arcpy.da.InsertCursor(loc, ["NOME", "SHAPE@XY"]) as c:
    for n, x, y in LOC:
        c.insertRow([n, (x, y)])
# hora de chegada (máximo num raio de 300 m, porque a localidade pode estar à beira de uma célula seca)
arcpy.management.AddField(loc, "CHEGADA_H", "DOUBLE")
arcpy.management.AddField(loc, "PROF_MAX", "DOUBLE")
ch_min = arcpy.sa.FocalStatistics(Raster(rec["chegada_h"]), arcpy.sa.NbrCircle(30, "CELL"), "MINIMUM", "DATA")
pr_max = arcpy.sa.FocalStatistics(Raster(rec["profundidade_max"]), arcpy.sa.NbrCircle(30, "CELL"), "MAXIMUM", "DATA")
ch_tif, pr_tif = os.path.join(mapas, "tmp_chegada_min.tif"), os.path.join(mapas, "tmp_prof_max.tif")
ch_min.save(ch_tif); pr_max.save(pr_tif)
arcpy.sa.ExtractMultiValuesToPoints(loc, [[ch_tif, "CH_TMP"], [pr_tif, "PR_TMP"]], "NONE")
with arcpy.da.UpdateCursor(loc, ["CH_TMP", "PR_TMP", "CHEGADA_H", "PROF_MAX"]) as c:
    for a, b, _, _ in c:
        c.updateRow([a, b, a, b])
arcpy.management.DeleteField(loc, ["CH_TMP", "PR_TMP"])

# isócrona de 30 min (contorno)
iso30 = os.path.join(gdb, "isocrona_30min")
arcpy.conversion.RasterToPolygon(arcpy.sa.Con(Raster(rec["chegada_h"]) <= 0.5, 1), r"memory\iso30", "SIMPLIFY")
arcpy.management.Dissolve(r"memory\iso30", iso30)

# ---------------- utilitários de simbologia
def rgb(r, g, b, a=100): return {"RGB": [r, g, b, a]}

def classificar(lyr, quebras, rotulos, cores):
    sym = lyr.symbology
    sym.updateColorizer("RasterClassifyColorizer")
    sym.colorizer.classificationMethod = "ManualInterval"
    sym.colorizer.breakCount = len(quebras)
    for brk, ub, lb, cor in zip(sym.colorizer.classBreaks, quebras, rotulos, cores):
        brk.upperBound = ub; brk.label = lb; brk.color = rgb(*cor)
    sym.colorizer.noDataColor = rgb(0, 0, 0, 0)
    lyr.symbology = sym

def poligono(lyr, cor, contorno=None, larg=0.0, transp=0):
    sym = lyr.symbology
    sym.renderer.symbol.color = rgb(*cor) if cor else rgb(0, 0, 0, 0)
    sym.renderer.symbol.outlineColor = rgb(*contorno) if contorno else rgb(0, 0, 0, 0)
    sym.renderer.symbol.outlineWidth = larg
    lyr.symbology = sym
    if transp: lyr.transparency = transp

EXT = arcpy.Extent(598000, 4110000, 662000, 4236000)   # vale de Alqueva à foz
ESCALA = 325000

def legenda(lyt, mf, x, y, largura=85, altura=None):
    """Legenda só com as camadas temáticas: sem relevo nem mapa base, sem cabeçalhos nem nomes de camada repetidos."""
    try:
        st = aprx.listStyleItems("ArcGIS 2D", "LEGEND", "Legend 1")[0]
        leg = lyt.createMapSurroundElement(arcpy.Point(x, y), "LEGEND", mf, st, "Legenda")
        leg.title = "Legenda"
        cim = leg.getDefinition("V3")
        fora = ("Relevo", "World", "Light Gray", "Topographic", "Imagery", "Hillshade")
        cim.items = [it for it in cim.items if not str(it.name).startswith(fora)]
        for it in cim.items:
            for att in ("showHeading", "showLayerName", "showGroupLayerName"):
                if hasattr(it, att):
                    setattr(it, att, False)
            for att in ("labelSymbol", "layerNameSymbol", "headingSymbol"):
                try: getattr(it, att).symbol.height = 8.5
                except Exception: pass
        try: cim.titleSymbol.symbol.height = 12
        except Exception: pass
        try: cim.autoAdd = False
        except Exception: pass
        if altura:
            cim.fittingStrategy = "AdjustFontSize"
        leg.setDefinition(cim)
        leg.elementWidth = largura
        if altura:
            leg.elementHeight = altura
        return leg
    except Exception as e:
        print("   (legenda: afinar à mão)", e)


def norte(lyt, mf, x, y):
    """Seta do norte no canto superior direito da moldura."""
    try:
        na = aprx.listStyleItems("ArcGIS 2D", "NORTH_ARROW", "ArcGIS North 1")[0]
        n_ = lyt.createMapSurroundElement(arcpy.Point(x, y), "NORTH_ARROW", mf, na, "Norte")
        n_.elementHeight = 14
        return n_
    except Exception as e:
        print("   (seta de norte à mão)", e)


def escala(lyt, mf, x, y, nome="Escala", largura=None):
    """Barra de escala em km."""
    try:
        sb = aprx.listStyleItems("ArcGIS 2D", "SCALE_BAR", "Scale Line 1 Metric")[0]
        e_ = lyt.createMapSurroundElement(arcpy.Point(x, y), "SCALE_BAR", mf, sb, nome)
        if largura:
            e_.elementWidth = largura
        try:
            c_ = e_.getDefinition("V3"); c_.unitLabel = "km"; e_.setDefinition(c_)
        except Exception:
            pass
        return e_
    except Exception as e:
        print("   (barra de escala à mão)", e)

def novo_mapa(nome):
    m = aprx.createMap(nome, "MAP")
    m.spatialReference = sr
    for l_ in m.listLayers():
        if l_.isBasemapLayer:
            m.removeLayer(l_)
    lr = m.addDataFromPath(relevo); lr.name = "Relevo sombreado (terreno 10 m)"
    try:
        sym = lr.symbology
        sym.updateColorizer("RasterStretchColorizer")
        sym.colorizer.stretchType = "MinimumMaximum"
        rampa = aprx.listColorRamps("Black to White") or aprx.listColorRamps("Gray*")
        if rampa: sym.colorizer.colorRamp = rampa[0]
        lr.symbology = sym
    except Exception as e:
        print("   (relevo: pôr à mão Stretch + Black to White)", e)
    lr.transparency = 55
    la = m.addDataFromPath(agua_0900); la.name = "Água antes da rotura (albufeiras, rio, estuário)"
    poligono(la, (190, 205, 215), None, 0)
    return m

def topo(m):
    lc = m.addDataFromPath(loc); lc.name = "Localidades"
    sym = lc.symbology; sym.renderer.symbol.size = 5; sym.renderer.symbol.color = rgb(30, 30, 30); lc.symbology = sym
    lc.showLabels = True
    lbl = lc.listLabelClasses()[0]
    lbl.expression = "$feature.NOME"
    try:  # rótulos a 7 pt com halo branco
        cim = lc.getDefinition("V3")
        ts = cim.labelClasses[0].textSymbol.symbol
        ts.height = 7
        cor = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3"); cor.values = [255, 255, 255, 100]
        fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3"); fill.color = cor; fill.enable = True
        halo = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3"); halo.symbolLayers = [fill]
        ts.haloSymbol = halo; ts.haloSize = 1.2
        lc.setDefinition(cim)
    except Exception as e:
        print("   (halo dos rótulos à mão)", e)
    return lc

def layout(nome, m, titulo, subtitulo, notas_extra=""):
    lyt = aprx.createLayout(297, 420, "MILLIMETER", nome)
    mf = lyt.createMapFrame(arcpy.Extent(10, 25, 200, 400), m, "Mapa")
    mf.map = m
    mf.camera.setExtent(EXT); mf.camera.scale = ESCALA
    aprx.createTextElement(lyt, arcpy.Point(10, 412), "POINT", titulo, 20, name="Titulo")
    aprx.createTextElement(lyt, arcpy.Point(10, 405), "POINT", subtitulo, 10, name="Subtitulo")
    legenda(lyt, mf, 205, 398)
    escala(lyt, mf, 205, 40)
    norte(lyt, mf, 186, 382)
    nota = ("Cenário hipotético de rotura em série das barragens de Alqueva e Pedrógão (B1), para fins académicos.\n"
            "Não substitui o Plano de Emergência Externo (PEExt). Modelo HEC-RAS 7.0.2 2D; terreno LiDAR DGT + MDT CNIG + SRTM;\n"
            "rugosidade COS 2025 (DGT). Projeção: ETRS89 / UTM 29N (EPSG 25829). Escala 1:325 000." + notas_extra +
            "\nAutor: Gustavo Santa, 2026.")
    aprx.createTextElement(lyt, arcpy.Point(10, 5), "POINT", nota, 6.5, name="Fontes")
    return lyt

A_EXPORTAR = []
def exportar(lyt, nome):
    A_EXPORTAR.append(nome)

def exportar_tudo():
    global aprx
    # a ligação ao projeto aberta antes de apagar os mapas antigos fica desatualizada:
    # gravar e voltar a abrir o projeto antes de ligar as molduras e exportar
    aprx.save()
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    for nome in A_EXPORTAR:
        lyt = aprx.listLayouts(nome)[-1]
        # o ArcGIS pode manter na lista o mapa antigo (apagado) com o mesmo nome: usar o que tem camadas
        mp = [m_ for m_ in aprx.listMaps(nome) if len(m_.listLayers()) > 0][-1]
        uri = mp.getDefinition("V3").uRI
        for f in lyt.listElements("MAPFRAME_ELEMENT"):
            f.map = mp                                   # religar sempre
        cim = lyt.getDefinition("V3")                    # e garantir a referência interna (uRI) da moldura
        for e in cim.elements:
            if type(e).__name__ == "CIMMapFrame":
                e.uRI = uri
        lyt.setDefinition(cim)
        for f in lyt.listElements("MAPFRAME_ELEMENT"):
            if f.name == "Mapa":
                f.camera.setExtent(EXT); f.camera.scale = ESCALA
        # refazer a legenda já com o mapa ligado (senão o ArcGIS volta a pôr o relevo e os cabeçalhos)
        for e in lyt.listElements("LEGEND_ELEMENT"):
            lyt.deleteElement(e)
        molduras = {f.name: f for f in lyt.listElements("MAPFRAME_ELEMENT")}
        mf_leg = molduras.get("Mapa") or molduras.get("Estuario")
        legenda(lyt, mf_leg, 205, 398)
        lyt.exportToPDF(os.path.join(saida, nome + ".pdf"), resolution=300)
        lyt.exportToPNG(os.path.join(saida, nome + ".png"), resolution=200)
        print("   exportado:", nome)

# ---------------- 1. profundidade
print("2/4 Layouts 1 e 2...")
m1 = novo_mapa("B1_1_profundidade")
l1 = m1.addDataFromPath(rec["profundidade_max"]); l1.name = "Profundidade máxima (m)"
classificar(l1, [0.5, 1, 2, 5, 10, 20, 999],
            ["≤ 0,5", "0,5 – 1", "1 – 2", "2 – 5", "5 – 10", "10 – 20", "> 20"],
            [(222, 235, 247), (198, 219, 239), (158, 202, 225), (107, 174, 214), (66, 146, 198), (33, 113, 181), (8, 69, 148)])
topo(m1)
lyt1 = layout("B1_1_profundidade", m1, "Profundidade máxima da inundação",
              "Rotura hipotética de Alqueva e Pedrógão (cenário B1) — 48 h após a rotura | área inundada pela rotura: 22 631 ha")
exportar(lyt1, "B1_1_profundidade")

# ---------------- 2. perigosidade h·v
m2 = novo_mapa("B1_2_perigosidade")
l2 = m2.addDataFromPath(rec["hv_max"]); l2.name = "Perigosidade h·v máx. (m²/s)"
classificar(l2, [0.3, 0.6, 1.0, 4.0, 9999],
            ["≤ 0,3 — baixa", "0,3 – 0,6 — moderada", "0,6 – 1,0 — elevada", "1,0 – 4,0 — muito elevada", "> 4,0 — extrema"],
            [(255, 255, 178), (254, 204, 92), (253, 141, 60), (227, 26, 28), (128, 0, 38)])
topo(m2)
lyt2 = layout("B1_2_perigosidade", m2, "Perigosidade da inundação (profundidade × velocidade)",
              "Produto h·v máximo, classes baseadas em ARR 2019 (simplificadas só pelo h·v) | 10 351 ha com h·v > 4 m²/s",
              "\nClasses: limiares de estabilidade de pessoas, veículos e edifícios (h·v); não incluem profundidade nem velocidade isoladas.")
exportar(lyt2, "B1_2_perigosidade")

# ---------------- 3. tempo de chegada
print("3/4 Layout 3...")
m3 = novo_mapa("B1_3_chegada")
l3 = m3.addDataFromPath(rec["chegada_h"]); l3.name = "Chegada da onda (h após a rotura)"
classificar(l3, [0.5, 1, 2, 4, 8, 12, 24, 999],
            ["≤ 0,5 (30 min)", "0,5 – 1", "1 – 2", "2 – 4", "4 – 8", "8 – 12", "12 – 24", "> 24"],
            [(80, 18, 123), (129, 37, 129), (181, 54, 122), (229, 80, 100), (251, 135, 97), (254, 194, 135), (252, 253, 191), (240, 240, 240)])
li = m3.addDataFromPath(iso30); li.name = "Limite dos primeiros 30 min"
poligono(li, None, (0, 0, 0), 1.2)
lc3 = topo(m3)
lc3.listLabelClasses()[0].expression = ('$feature.NOME + IIf(IsEmpty($feature.CHEGADA_H), "", " — " + '
                                        'Text(Floor($feature.CHEGADA_H), "0") + " h " + Text(Round(($feature.CHEGADA_H % 1) * 60), "00") + " min")')
lyt3 = layout("B1_3_chegada", m3, "Tempo de chegada da onda de inundação",
              "Horas após a rotura de Alqueva até o nível subir 0,3 m | 1 319 ha atingidos nos primeiros 30 min",
              "\nAs chegadas a jusante do Pulo do Lobo são 1,4–2× mais lentas do que no PEExt (limitação do modelo; ver relatório).")
exportar(lyt3, "B1_3_chegada")

# ---------------- 4. exposição
print("4/4 Layout 4...")
m4 = novo_mapa("B1_4_exposicao")
lf = m4.addDataFromPath(inund_rot); lf.name = "Área inundada pela rotura"
poligono(lf, (107, 174, 214), None, 0, 30)
for fc, nome in [("urbano_inundado", "Tecido urbano inundado — Portugal (COS 2025)"),
                 ("catastro_inundado", "Edifícios inundados — Espanha (Catastro)")]:
    if arcpy.Exists(os.path.join(gdb, fc)):
        l = m4.addDataFromPath(os.path.join(gdb, fc)); l.name = nome
        poligono(l, (203, 24, 29), (103, 0, 13), 0.2)
topo(m4)

def ler(nome):
    d = {}
    p = os.path.join(base, r"resultados\p13", nome)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d[r["indicador"]] = float(r["valor"])
    return d
pt, ib = ler("exposicao_b1.csv"), ler("exposicao_iberica_b1.csv")
conc = sorted([(k.replace("residentes_", "").replace("_ponderado", ""), v) for k, v in pt.items()
               if k.startswith("residentes_") and k.endswith("_ponderado") and v >= 1], key=lambda kv: -kv[1])
tab = "Residentes expostos (Censos 2021)\n"
tab += "\n".join(f"  {n}: {v:,.0f}".replace(",", " ") for n, v in conc)
tab += f"\n  Espanha (grelha JRC 100 m): {ib.get('residentes_expostos_ES_ponderado', 0):,.0f}".replace(",", " ")
tab += f"\n\nEdifícios — Espanha (Catastro): {ib.get('edificios_expostos_ES', 0):,.0f}".replace(",", " ")
tab += f"\n  habitações: {ib.get('habitacoes_expostas_ES', 0):,.0f}".replace(",", " ")
tab += f"\nTecido urbano inundado — Portugal: {pt.get('urbano_inundado_COS1', 0):,.0f} ha".replace(",", " ")
tab += "\n\nPortugal: ponderação de área por subsecção BGRI 2021;\nEspanha: grelha JRC-ESTAT 2021 (100 m).\nResidentes, não população presente (turismo)."
lyt4 = aprx.createLayout(297, 420, "MILLIMETER", "B1_4_exposicao")
fa = lyt4.createMapFrame(arcpy.Extent(10, 165, 200, 400), m4, "Estuario")
fa.map = m4
fa.camera.setExtent(arcpy.Extent(633000, 4113000, 647000, 4130000))
fb = lyt4.createMapFrame(arcpy.Extent(10, 30, 200, 158), m4, "Alcoutim_Sanlucar")
fb.map = m4
fb.camera.setExtent(arcpy.Extent(631500, 4145200, 639500, 4151200))
aprx.createTextElement(lyt4, arcpy.Point(10, 412), "POINT", "População e edifícios expostos", 20, name="Titulo")
aprx.createTextElement(lyt4, arcpy.Point(10, 405), "POINT",
                       "Portugal e Espanha | ~28 800 residentes na área inundada pela rotura (até ~32 100)", 10, name="Subtitulo")
aprx.createTextElement(lyt4, arcpy.Point(12, 396), "POINT", "Estuário — Vila Real de Santo António, Ayamonte e Castro Marim", 9, name="T_a")
aprx.createTextElement(lyt4, arcpy.Point(12, 154), "POINT", "Alcoutim e Sanlúcar de Guadiana", 9, name="T_b")
legenda(lyt4, fa, 205, 398, 85)
escala(lyt4, fa, 14, 169, "Escala_a", 55)
escala(lyt4, fb, 14, 34, "Escala_b", 55)
norte(lyt4, fa, 186, 382)
aprx.createTextElement(lyt4, arcpy.Point(205, 230), "POINT", tab, 8, name="Tabela")
aprx.createTextElement(lyt4, arcpy.Point(10, 8), "POINT",
    "Cenário hipotético de rotura em série das barragens de Alqueva e Pedrógão (B1), para fins académicos. Não substitui o PEExt.\n"
    "Exposição: INE (BGRI e Censos 2021), JRC-ESTAT Census Population Grid 2021, D.G. del Catastro (INSPIRE); COS 2025 (DGT).\n"
    "ETRS89 / UTM 29N (EPSG 25829). Autor: Gustavo Santa, 2026.", 6.5, name="Fontes")
exportar(lyt4, "B1_4_exposicao")

exportar_tudo()
for it in aprx.listLayouts("TMP_*") + aprx.listMaps("TMP_*"):
    aprx.deleteItem(it)
aprx.save()
print("Feito: 4 mapas e 4 layouts no projeto; PDF e PNG em", saida)
