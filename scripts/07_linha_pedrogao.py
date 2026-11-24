"""
07 - Gerar a linha do coroamento de Pedrogao para o HEC-RAS.

Tira o eixo longo do poligono remover_terreno (que desenhaste sobre o paredao)
e grava-o como shapefile de linha, para importares no RAS Mapper como a
SA/2D Connection da barragem de Pedrogao. Fica alinhado com o entalhe do terreno.

Correr na janela Python do ArcGIS Pro:
  import runpy, sys, os; P=r'C:\\caminho\\para\\rotura-alqueva'; sys.argv=['07',P]; _=runpy.run_path(os.path.join(P,'scripts','07_linha_pedrogao.py'), run_name='__main__')

Saida: hecras\\conn_pedrogao.shp (EPSG:25829).
"""
import math
import os
import sys


def main(projeto):
    import arcpy

    arcpy.env.overwriteOutput = True
    gdb = os.path.join(projeto, "rotura-alqueva.gdb")
    fc = os.path.join(gdb, "remover_terreno")
    mbg = os.path.join(gdb, "_mbg_pedrogao")
    saida = os.path.join(projeto, "hecras", "conn_pedrogao.shp")
    sr = arcpy.Describe(fc).spatialReference

    # retangulo orientado minimo -> comprimento e orientacao do lado mais longo
    arcpy.management.MinimumBoundingGeometry(
        fc, mbg, "RECTANGLE_BY_WIDTH", "ALL", "", "MBG_FIELDS")
    with arcpy.da.SearchCursor(mbg, ["SHAPE@XY", "MBG_Length", "MBG_Orientation"]) as cur:
        (cx, cy), comp, ang = next(iter(cur))

    # a linha segue o lado mais longo (atravessa o vale), centrada no centroide,
    # alongada 15% para garantir que encosta as duas margens
    r = math.radians(ang)
    dx = (comp * 1.15 / 2) * math.cos(r)
    dy = (comp * 1.15 / 2) * math.sin(r)
    p1 = arcpy.Point(cx - dx, cy - dy)
    p2 = arcpy.Point(cx + dx, cy + dy)
    linha = arcpy.Polyline(arcpy.Array([p1, p2]), sr)

    arcpy.management.CopyFeatures([linha], saida)
    print(f"Linha de Pedrogao: comprimento {comp * 1.15:.0f} m, orientacao {ang:.0f} graus")
    print(f"Gravada em {saida}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
