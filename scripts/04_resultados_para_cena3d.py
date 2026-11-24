"""
04 - Levar os resultados do HEC-RAS para o ArcGIS Pro com dimensao tempo.

No RAS Mapper exporta-se um GeoTIFF por instante (Depth ou WSE) para uma pasta.
Este script cria um mosaic dataset, le o instante a partir do nome de cada
ficheiro e constroi a informacao multidimensional, para a camada responder ao
"time slider" numa cena local.

Correr:  propy 04_resultados_para_cena3d.py <pasta_tifs> <saida.gdb> [variavel]
         variavel = Depth (por omissao) ou WSE

Ajustar PADRAO_DATA ao nome real dos ficheiros exportados. O habitual e algo como
  "Depth (12NOV2026 00 10 00).Terreno.tif"

Para a cena 3D usar a cota da superficie de agua (WSE) como superficie de
elevacao da camada, e a profundidade (Depth) so para a simbologia.

Nao foi corrido (nao tenho ArcGIS Pro deste lado): rever na primeira execucao.
"""
import datetime as dt
import os
import re
import sys

PADRAO_DATA = re.compile(r"\((\d{2}[A-Za-z]{3}\d{4}) (\d{2}) (\d{2}) (\d{2})\)")
EPSG = 25829
MESES = {m: i for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), start=1)}


def instante(nome):
    m = PADRAO_DATA.search(nome)
    if not m:
        return None
    dia, hh, mm, ss = m.groups()
    # meses em ingles, lidos a mao para nao depender do idioma do Windows
    base = dt.datetime(int(dia[5:]), MESES[dia[2:5].upper()], int(dia[:2]))
    # o HEC-RAS escreve a meia-noite final como 24:00:00; o timedelta trata disso
    return base + dt.timedelta(hours=int(hh), minutes=int(mm), seconds=int(ss))


def main(pasta_tifs, gdb, variavel="Depth"):
    import arcpy

    arcpy.env.overwriteOutput = True
    if not arcpy.Exists(gdb):
        arcpy.management.CreateFileGDB(os.path.dirname(gdb) or ".", os.path.basename(gdb))

    nome_md = f"rotura_{variavel.lower()}"
    md = os.path.join(gdb, nome_md)
    arcpy.management.CreateMosaicDataset(gdb, nome_md, arcpy.SpatialReference(EPSG),
                                         num_bands=1, pixel_type="32_BIT_FLOAT")
    arcpy.management.AddRastersToMosaicDataset(
        md, "Raster Dataset", pasta_tifs, filter=f"{variavel}*.tif",
        update_cellsize_ranges="UPDATE_CELL_SIZES", update_boundary="UPDATE_BOUNDARY")

    arcpy.management.AddField(md, "Variable", "TEXT", field_length=20)
    arcpy.management.AddField(md, "StdTime", "DATE")

    sem_data = 0
    with arcpy.da.UpdateCursor(md, ["Name", "Variable", "StdTime"]) as cur:
        for nome, _, _ in cur:
            t = instante(nome)
            if t is None:
                sem_data += 1
            cur.updateRow([nome, variavel, t])
    if sem_data:
        print(f"[aviso] {sem_data} ficheiros sem instante reconhecido - rever PADRAO_DATA")

    arcpy.md.BuildMultidimensionalInfo(
        md, "Variable", [["StdTime", "Instante da simulacao", "ISO8601"]])
    print(f"Mosaic dataset multidimensional criado: {md}")
    print("Adicionar a cena local; o separador Multidimensional e o time slider ficam ativos.")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(*sys.argv[1:])
