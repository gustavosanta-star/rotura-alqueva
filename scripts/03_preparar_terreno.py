"""
03 - Preparar o terreno unico para o HEC-RAS (RAS Mapper) e para a cena 3D.

Junta os MDT por ordem de prioridade (o mais fino por cima), reprojeta para
ETRS89 / UTM 29N (EPSG:25829, serve os dois lados da fronteira), recorta pela
area de estudo e exporta um GeoTIFF float32.

Entradas esperadas (pastas com GeoTIFF/ASC):
  dados/mdt/MDT-2m/     MDT 2 m LiDAR da DGT (Portugal)        prioridade 1
  dados/mdt/cnig_5m/    MDT02 do CNIG, 2.a cobertura (Espanha)  prioridade 2
  dados/mdt/srtm_30m/   SRTM 1" (fundo da albufeira e lacunas)  prioridade 3

Correr:  propy 03_preparar_terreno.py <pasta_dados_mdt> <aoi.shp> <saida.tif> [celula_m]

Avisos:
  - O SRTM vem com altitudes EGM96 e os MDT nacionais em datum vertical proprio
    (Cascais / Alicante). As diferencas sao pequenas face a uma onda de dezenas
    de metros, mas ficam registadas como limitacao.
  - Dentro da albufeira os MDT recentes mostram agua ou vazio: e ai que o SRTM
    (anterior ao enchimento) tem de prevalecer. Para isso o script apaga, nos
    MDT finos, as celulas dentro do poligono da albufeira se este for dado
    na variavel POLIGONO_ALBUFEIRA.
  - Nao foi corrido (nao tenho ArcGIS Pro deste lado): rever na primeira execucao.
"""
import os
import sys
import time

POLIGONO_ALBUFEIRA = None      # ex.: r"dados/vetor/albufeira_alqueva.shp"
EPSG_SAIDA = 25829
ORDEM = ["srtm_30m", "cnig_5m", "MDT-2m"]   # do menos para o mais prioritario


def main(pasta_mdt, aoi, saida_tif, celula=10.0):
    import arcpy
    from arcpy.sa import ExtractByMask, IsNull, SetNull, Raster

    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True
    sr = arcpy.SpatialReference(EPSG_SAIDA)
    trabalho = arcpy.env.scratchGDB

    camadas = []
    for nome in ORDEM:
        pasta = os.path.join(pasta_mdt, nome)
        if not os.path.isdir(pasta):
            print(f"[aviso] sem pasta {pasta}; a continuar sem esta fonte")
            continue
        arcpy.env.workspace = pasta
        ficheiros = [os.path.join(pasta, r) for r in (arcpy.ListRasters() or [])]
        if not ficheiros:
            print(f"[aviso] {pasta} vazia")
            continue

        t0 = time.time()
        seguro = nome.replace("-", "_")          # hifens nao sao validos numa gdb
        # 1) mosaico da fonte no sistema original
        bruto = os.path.join(trabalho, f"bruto_{seguro}")
        arcpy.management.MosaicToNewRaster(
            ficheiros, trabalho, f"bruto_{seguro}",
            pixel_type="32_BIT_FLOAT", number_of_bands=1, mosaic_method="FIRST")
        print(f"  {nome}: mosaico feito ({time.time() - t0:.0f} s)")

        # 2) reprojetar e reamostrar para a celula comum
        proj = os.path.join(trabalho, f"proj_{seguro}")
        arcpy.management.ProjectRaster(
            bruto, proj, sr, resampling_type="BILINEAR", cell_size=celula)

        # 3) nos MDT posteriores ao enchimento, retirar a zona da albufeira
        if POLIGONO_ALBUFEIRA and nome != "srtm_30m":
            dentro = ExtractByMask(proj, POLIGONO_ALBUFEIRA)
            sem_albufeira = SetNull(~IsNull(dentro), Raster(proj))
            proj = os.path.join(trabalho, f"seco_{seguro}")
            sem_albufeira.save(proj)

        camadas.append(proj)
        print(f"[ok] {nome}: {len(ficheiros)} ficheiros ({time.time() - t0:.0f} s)")

    if not camadas:
        sys.exit("Nenhum MDT encontrado.")

    # 4) mosaico final: o ultimo da lista (mais fino) fica por cima
    arcpy.env.snapRaster = camadas[-1]
    arcpy.management.MosaicToNewRaster(
        camadas, trabalho, "terreno_unico", sr,
        pixel_type="32_BIT_FLOAT", cellsize=celula,
        number_of_bands=1, mosaic_method="LAST")

    # 5) recortar pela area de estudo e exportar
    os.makedirs(os.path.dirname(os.path.abspath(saida_tif)), exist_ok=True)
    final = ExtractByMask(os.path.join(trabalho, "terreno_unico"), aoi)
    arcpy.management.CopyRaster(final, saida_tif, pixel_type="32_BIT_FLOAT",
                                format="TIFF", nodata_value="-9999")
    print(f"Terreno gravado em {saida_tif} (celula {celula} m, EPSG:{EPSG_SAIDA})")


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    args = sys.argv[1:]
    if len(args) == 4:
        args[3] = float(args[3])
    main(*args)
