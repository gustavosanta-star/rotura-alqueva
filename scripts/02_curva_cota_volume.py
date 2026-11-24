"""
02 - Curva cota-volume da albufeira de Alqueva a partir de um MDT anterior
ao enchimento (SRTM, fev. 2000; as comportas fecharam em fev. 2002).

Para que serve:
  - e o controlo de qualidade do terreno: ao NPA (152 m) a curva deve dar
    cerca de 4150 hm3 e 250 km2. Se nao der, o MDT nao serve para a albufeira.
  - a tabela CSV de saida entra diretamente no HEC-RAS como curva
    "Elevation-Volume" de uma Storage Area (opcao simples para a albufeira).

Correr no Python do ArcGIS Pro (precisa de arcpy + numpy):
  propy 02_curva_cota_volume.py <mdt_pre_enchimento.tif> <poligono_albufeira> <saida.csv>

O poligono deve conter toda a albufeira com folga (ex.: mascara de agua do
projeto "Monsaraz em Mudanca" alargada a toda a albufeira, com buffer de 500 m),
e parar na barragem. MDT em sistema projetado, em metros (EPSG:25829).

NOTA: a funcao curva() foi testada com dados sinteticos; a parte arcpy nao foi
corrida (nao tenho ArcGIS Pro deste lado).
"""
import csv
import sys

import numpy as np

NPA = 152.0
VOLUME_REF_HM3 = 4150.0
AREA_REF_KM2 = 250.0


def curva(mdt, celula_m, cotas):
    """Area (km2) e volume (hm3) abaixo de cada cota. mdt: array 2D com NaN fora."""
    area_celula = celula_m * celula_m
    validos = mdt[np.isfinite(mdt)]
    linhas = []
    for z in cotas:
        abaixo = validos[validos < z]
        area = abaixo.size * area_celula
        volume = float(np.sum(z - abaixo)) * area_celula
        linhas.append((float(z), area / 1e6, volume / 1e6))
    return linhas


def main(mdt_path, poligono, saida_csv):
    import arcpy
    from arcpy.sa import ExtractByMask

    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True

    recorte = ExtractByMask(mdt_path, poligono)
    celula = recorte.meanCellWidth
    mdt = arcpy.RasterToNumPyArray(recorte, nodata_to_value=np.nan).astype("float64")

    z_min = np.floor(np.nanmin(mdt))
    cotas = np.arange(z_min, 156.0 + 0.5, 1.0)
    linhas = curva(mdt, celula, cotas)

    with open(saida_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cota_m", "area_km2", "volume_hm3"])
        w.writerows((f"{z:.1f}", f"{a:.2f}", f"{v:.1f}") for z, a, v in linhas)

    z, a, v = min(linhas, key=lambda l: abs(l[0] - NPA))
    print(f"Ao NPA ({z:.0f} m): area {a:.0f} km2 (ref. {AREA_REF_KM2:.0f}), "
          f"volume {v:.0f} hm3 (ref. {VOLUME_REF_HM3:.0f})")
    print(f"Desvio no volume: {100 * (v - VOLUME_REF_HM3) / VOLUME_REF_HM3:+.1f} %")
    print(f"Curva gravada em {saida_csv}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
