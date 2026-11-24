"""
05 - Descarregar dados abertos sem login, so para a area do corredor:
  a) MDT de 5 m de Espanha (WCS do IGN/IDEE) -> dados/mdt/cnig_5m/*.tif
  b) BGRI 2021 (WFS do INE)                  -> dados/vetor/bgri2021/bgri2021_corredor.geojson
                                                + feature class bgri2021 na gdb

Correr no ArcGIS Pro (Python window ou notebook):
  import runpy, sys; sys.argv = ['05', r'<pasta do projeto>', 'mdt,bgri']
  runpy.run_path(r'<pasta do projeto>\\scripts\\05_dados_abertos.py', run_name='__main__')

Os servicos nao tem documentacao clara de limites: o script sonda primeiro,
pede em blocos pequenos e escreve no ecra o que fez. Voltar a correr salta o
que ja existe.
"""
import json
import os
import sys
import time

WCS = "https://servicios.idee.es/wcs-inspire/mdt"
WFS_BGRI = "https://inspire.ine.pt/geoserver/BGRI2021/wfs"
# margem espanhola relevante: do Pomarao a foz (graus, ETRS89 ~ WGS84)
CAIXA_ESPANHA = (-7.56, 37.12, -7.28, 37.60)
PASSO = 0.04        # blocos de ~3,5 x 4,4 km
RES_GRAUS = 0.00005  # ~4,4 m em longitude, ~5,5 m em latitude


def corredor(gdb):
    import arcpy
    aoi = os.path.join(gdb, "aoi_vale_jusante")
    wgs = arcpy.SpatialReference(4326)
    return [r[0].projectAs(wgs) for r in arcpy.da.SearchCursor(aoi, ["SHAPE@"])], aoi


def caixa_poligono(o, s, e, n):
    import arcpy
    return arcpy.Polygon(arcpy.Array(
        [arcpy.Point(*p) for p in ((o, s), (e, s), (e, n), (o, n), (o, s))]),
        arcpy.SpatialReference(4326))


def mdt_espanha(projeto, geoms, sessao):
    destino = os.path.join(projeto, "dados", "mdt", "cnig_5m")
    os.makedirs(destino, exist_ok=True)
    o0, s0, e0, n0 = CAIXA_ESPANHA
    blocos = []
    o = o0
    while o < e0:
        s = s0
        while s < n0:
            cx = (o, s, min(o + PASSO, e0), min(s + PASSO, n0))
            if any(not g.disjoint(caixa_poligono(*cx)) for g in geoms):
                blocos.append(cx)
            s += PASSO
        o += PASSO
    print(f"MDT Espanha: {len(blocos)} blocos tocam no corredor")

    feitos = falhas = 0
    for i, (o, s, e, n) in enumerate(blocos, 1):
        nome = f"mdt05_es_{o:.2f}_{s:.2f}".replace("-", "m").replace(".", "p")
        tif = os.path.join(destino, nome + ".tif")
        asc = os.path.join(destino, nome + ".asc")
        if os.path.exists(tif) or os.path.exists(asc):
            continue
        largura = int(round((e - o) / RES_GRAUS))
        altura = int(round((n - s) / RES_GRAUS))
        base = dict(service="WCS", version="1.0.0", request="GetCoverage",
                    coverage="Elevacion4258_5", crs="EPSG:4258",
                    bbox=f"{o},{s},{e},{n}", width=largura, height=altura,
                    interpolationMethod="bilinear")
        ok = False
        for formato, caminho in (("GTiff", tif), ("image/tiff", tif), ("ArcGrid", asc)):
            try:
                r = sessao.get(WCS, params=dict(base, format=formato), timeout=180)
            except Exception as erro:
                print(f"\n[aviso] bloco {i}: {erro}")
                time.sleep(5)
                continue
            tipo = r.headers.get("Content-Type", "")
            corpo = r.content
            if r.status_code != 200 or b"ServiceException" in corpo[:2000] or "xml" in tipo:
                continue
            if caminho.endswith(".asc") and not corpo.lstrip().lower().startswith(b"ncols"):
                continue
            with open(caminho, "wb") as f:
                f.write(corpo)
            if caminho.endswith(".asc"):
                with open(caminho[:-4] + ".prj", "w") as f:
                    f.write('GEOGCS["ETRS89",DATUM["European_Terrestrial_Reference_System_1989",'
                            'SPHEROID["GRS 1980",6378137,298.257222101]],PRIMEM["Greenwich",0],'
                            'UNIT["degree",0.0174532925199433]]')
            ok = True
            break
        feitos += ok
        falhas += not ok
        if not ok and falhas == 1:
            print(f"\n[falhou] primeiro bloco sem resposta valida. Ultima resposta: "
                  f"HTTP {r.status_code} {tipo} {corpo[:300]!r}")
        print(f"  MDT Espanha {i}/{len(blocos)}  (ok {feitos}, falhas {falhas})", end="\r")
        time.sleep(1)
    print(f"\nMDT Espanha: {feitos} blocos novos, {falhas} falhas -> {destino}")


def bgri(projeto, aoi, sessao):
    import arcpy
    destino = os.path.join(projeto, "dados", "vetor", "bgri2021")
    os.makedirs(destino, exist_ok=True)
    saida = os.path.join(destino, "bgri2021_corredor.geojson")
    arcpy.env.overwriteOutput = True
    if os.path.exists(saida):
        with open(saida, encoding="utf-8") as f:
            n_exist = len(json.load(f).get("features", []))
        if n_exist:
            print(f"BGRI: ja existe {saida} ({n_exist} subseccoes)")
            return

    cap = sessao.get(WFS_BGRI, params=dict(service="WFS", version="2.0.0",
                                           request="GetCapabilities"), timeout=60)
    cap.raise_for_status()
    import re
    nomes = re.findall(r"<(?:wfs:)?Name>([^<]+)</(?:wfs:)?Name>", cap.text)
    print("BGRI: camadas no WFS:", nomes)
    if not nomes:
        print("[falhou] BGRI: nao encontrei camadas no GetCapabilities")
        return
    # o WFS tem uma camada por regiao: CONT = continente
    camada = next((n for n in nomes if n.upper().endswith("CONT")),
                  next((n for n in nomes if "bgri" in n.lower()), nomes[0]))
    print("BGRI: camada usada:", camada)

    pt = arcpy.SpatialReference(3763)
    ext = arcpy.Describe(aoi).extent.projectAs(pt) if hasattr(arcpy.Describe(aoi).extent, "projectAs") else None
    if ext is None:
        geom = [r[0].projectAs(pt) for r in arcpy.da.SearchCursor(aoi, ["SHAPE@"])]
        xmin = min(g.extent.XMin for g in geom); ymin = min(g.extent.YMin for g in geom)
        xmax = max(g.extent.XMax for g in geom); ymax = max(g.extent.YMax for g in geom)
    else:
        xmin, ymin, xmax, ymax = ext.XMin, ext.YMin, ext.XMax, ext.YMax

    feicoes, inicio, lote = [], 0, 1000
    while True:
        r = sessao.get(WFS_BGRI, timeout=120, params=dict(
            service="WFS", version="2.0.0", request="GetFeature", typeNames=camada,
            srsName="EPSG:3763", bbox=f"{xmin},{ymin},{xmax},{ymax},EPSG:3763",
            outputFormat="application/json", count=lote, startIndex=inicio))
        if r.status_code != 200 or "json" not in r.headers.get("Content-Type", ""):
            print(f"[falhou] BGRI: HTTP {r.status_code} {r.text[:300]}")
            return
        lote_f = r.json().get("features", [])
        feicoes += lote_f
        print(f"  BGRI: {len(feicoes)} subseccoes", end="\r")
        if len(lote_f) < lote:
            break
        inicio += lote
        time.sleep(0.5)
    print()
    fc = {"type": "FeatureCollection", "features": feicoes,
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3763"}}}
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    gdb = os.path.join(projeto, "rotura-alqueva.gdb")
    try:
        arcpy.conversion.JSONToFeatures(saida, os.path.join(gdb, "bgri2021"),
                                        geometry_type="POLYGON")
        print(f"BGRI: {len(feicoes)} subseccoes -> {saida} e gdb\\bgri2021")
    except Exception as erro:
        print(f"BGRI: gravado {saida}; conversao para a gdb falhou: {erro}")


def main(projeto, o_que="mdt,bgri"):
    import requests
    sessao = requests.Session()
    sessao.headers["User-Agent"] = "rotura-alqueva/0.1 (projeto academico; requests)"
    gdb = os.path.join(projeto, "rotura-alqueva.gdb")
    geoms, aoi = corredor(gdb)
    if "mdt" in o_que:
        mdt_espanha(projeto, geoms, sessao)
    if "bgri" in o_que:
        bgri(projeto, aoi, sessao)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(*sys.argv[1:])
