"""
06 - Retirar do terreno o corpo das barragens (e, se preciso, pontes).

O LiDAR mede o paredao de Pedrogao como terreno: um muro de ~43 m. Se ficar no
MDT, a agua continua bloqueada mesmo depois de a brecha abrir no HEC-RAS. A
barragem entra no modelo como estrutura (SA/2D Connection), por isso tem de
desaparecer do terreno.

Como: as celulas dentro dos poligonos desenhados passam a "sem dados" e sao
preenchidas por interpolacao a partir da envolvente (Elevation Void Fill), o
que da uma rampa suave entre a albufeira e o leito a jusante.

Antes de correr:
  1. Na gdb do projeto criar a feature class de poligonos "remover_terreno"
     (Catalog > rotura-alqueva.gdb > New > Feature Class, tipo Polygon,
     sistema ETRS89 / UTM 29N, EPSG:25829).
  2. Desenhar um poligono a cobrir o corpo da barragem de Pedrogao: todo o
     comprimento do coroamento (~450 m) e as duas faces (60-100 m de largura),
     com uma folga de 20-30 m para cada lado. Guardar a edicao.

Correr na janela Python do ArcGIS Pro:
  import runpy, sys, os; P = r'C:\\caminho\\para\\rotura-alqueva'
  sys.argv = ['06', P]; _ = runpy.run_path(os.path.join(P, 'scripts', '06_retirar_barragens.py'), run_name='__main__')

Saida: dados/terreno/terreno_10m_sem_barragens.tif (o original fica intacto).
"""
import os
import sys


def main(projeto):
    import arcpy
    from arcpy.sa import Con, IsNull, Raster, ElevationVoidFill, ZonalStatistics

    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True

    terreno = os.path.join(projeto, "dados", "terreno", "terreno_10m.tif")
    poligonos = os.path.join(projeto, "rotura-alqueva.gdb", "remover_terreno")
    saida = os.path.join(projeto, "dados", "terreno", "terreno_10m_sem_barragens.tif")

    if not arcpy.Exists(poligonos) or int(arcpy.management.GetCount(poligonos)[0]) == 0:
        sys.exit("Falta a feature class remover_terreno com pelo menos um poligono.")

    t = Raster(terreno)
    arcpy.env.snapRaster = terreno
    arcpy.env.cellSize = terreno
    arcpy.env.extent = terreno

    # cota maxima dentro de cada poligono, so para registo (deve ser o coroamento)
    antes = ZonalStatistics(poligonos, "OBJECTID", t, "MAXIMUM")

    mascara = arcpy.conversion.PolygonToRaster(
        poligonos, "OBJECTID", "in_memory\\mascara", cellsize=terreno)
    com_buraco = Con(IsNull(Raster("in_memory\\mascara")), t)

    # largura maxima do vazio a preencher: generosa para cobrir o paredao todo
    preenchido = ElevationVoidFill(com_buraco, max_void_width=2000)
    preenchido.save(saida)

    depois = ZonalStatistics(poligonos, "OBJECTID", preenchido, "MAXIMUM")
    a = antes.maximum
    d = depois.maximum
    print(f"Cota maxima dentro dos poligonos: antes {a:.1f} m, depois {d:.1f} m")
    print(f"Terreno sem barragens gravado em {saida}")
    if d > a - 5:
        print("[aviso] baixou pouco: confirmar se o poligono cobre o paredao todo")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
