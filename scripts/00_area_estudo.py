"""
00 - Area de estudo para o descarregamento do LiDAR da DGT e para o modelo.

Cria um corredor ao longo do Guadiana, da barragem de Alqueva a foz, a partir
de pontos de passagem, e grava-o como feature class e como GeoJSON (para o
plugin do QGIS ou para a toolbox de descarregamento).

  propy 00_area_estudo.py <saida.gdb> [largura_km]      (por omissao 4 km para cada lado)

ATENCAO: so as coordenadas da barragem de Alqueva vem de fonte oficial. As
restantes sao aproximadas (de memoria, erro possivel de 1 a 2 km) e servem
apenas para desenhar o corredor: abrir o resultado sobre um mapa de base e
corrigir os pontos antes de descarregar. Melhor ainda, trocar a linha por uma
linha do Guadiana tirada da hidrografia oficial.

A albufeira de Alqueva fica de fora de proposito: o LiDAR nao ve o fundo.
Nao foi corrido (nao tenho ArcGIS Pro deste lado).
"""
import os
import sys

# (longitude, latitude) em WGS84, de montante para jusante
PONTOS = [
    (-7.4964, 38.1975),   # barragem de Alqueva (PEExt: 38 11'51"N, 7 29'47"W)
    (-7.5500, 38.1700),   # confluencia do Ardila (aprox.)
    (-7.6300, 38.1150),   # barragem de Pedrogao (aprox.)
    (-7.6800, 37.9750),   # pontes de Serpa (aprox.)
    (-7.6330, 37.8040),   # Pulo do Lobo (aprox.)
    (-7.6620, 37.6420),   # Mertola (aprox.)
    (-7.5240, 37.5550),   # Pomarao (aprox.)
    (-7.4710, 37.4710),   # Alcoutim (aprox.)
    (-7.4400, 37.3500),   # Foz de Odeleite (aprox.)
    (-7.4430, 37.2180),   # Castro Marim (aprox.)
    (-7.4000, 37.1650),   # foz, Vila Real de Santo Antonio (aprox.)
]
# Ramais com largura propria: o PEExt da como inundado o Bairro do Sete e Meio,
# em Moura (perfis P2-P4), ou seja, a onda sobe o vale do Ardila.
RAMAIS = [
    ("ardila_moura", 2.0, [(-7.5500, 38.1700), (-7.5000, 38.1550), (-7.4480, 38.1400)]),
]
EPSG_TRABALHO = 25829


def main(gdb, largura_km=4.0):
    import arcpy

    arcpy.env.overwriteOutput = True
    if not arcpy.Exists(gdb):
        arcpy.management.CreateFileGDB(os.path.dirname(gdb) or ".", os.path.basename(gdb))

    wgs84 = arcpy.SpatialReference(4326)
    linha = arcpy.Polyline(arcpy.Array([arcpy.Point(x, y) for x, y in PONTOS]), wgs84)
    linha = linha.projectAs(arcpy.SpatialReference(EPSG_TRABALHO))

    eixo = os.path.join(gdb, "guadiana_eixo_aprox")
    arcpy.management.CopyFeatures([linha], eixo)

    sr = arcpy.SpatialReference(EPSG_TRABALHO)
    buffers = [linha.buffer(float(largura_km) * 1000)]
    for nome, larg_km, pts in RAMAIS:
        ramal = arcpy.Polyline(arcpy.Array([arcpy.Point(x, y) for x, y in pts]), wgs84)
        buffers.append(ramal.projectAs(sr).buffer(larg_km * 1000))
    corredor = buffers[0]
    for b in buffers[1:]:
        corredor = corredor.union(b)

    aoi = os.path.join(gdb, "aoi_vale_jusante")
    arcpy.management.CopyFeatures([corredor], aoi)

    geojson = os.path.join(os.path.dirname(gdb) or ".", "aoi_vale_jusante.geojson")
    arcpy.conversion.FeaturesToJSON(aoi, geojson, geoJSON="GEOJSON",
                                    outputToWGS84="WGS84")

    area_km2 = sum(r[0] for r in arcpy.da.SearchCursor(aoi, ["SHAPE@AREA"])) / 1e6
    print(f"Corredor: {aoi} ({area_km2:.0f} km2)")
    print(f"GeoJSON : {geojson}")
    print("Ver sobre um mapa de base antes de descarregar.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(*sys.argv[1:])
