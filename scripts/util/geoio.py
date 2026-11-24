"""Leitura/escrita de GeoTIFF sem GDAL (tifffile + Pillow) e projeção ETRS89/UTM 29N.

ler(path)  -> (array float32, dict(x0, y0, dx, dy, nodata))   # x0,y0 = canto sup. esq.
escrever(path, arr, x0, y0, dx, nodata=-9999) -> GeoTIFF EPSG 25829, DEFLATE
fwd/inv    -> lat/lon (graus, ETRS89) <-> x/y EPSG 25829
"""
import sys, warnings
import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
warnings.filterwarnings("ignore")
sys.path.insert(0, "/mnt/user-data/uploads/rotura-alqueva/scripts/g03_srtm")
from tm import fwd, inv  # noqa: E402,F401  (UTM 29N, já validado no G03)


def ler(path):
    with tifffile.TiffFile(path) as t:
        p = t.pages[0]
        sx, sy = p.tags["ModelPixelScaleTag"].value[:2]
        tp = p.tags["ModelTiepointTag"].value
        nod = p.tags["GDAL_NODATA"].value if "GDAL_NODATA" in p.tags else None
        try:
            a = p.asarray()
        except Exception:  # LZW sem imagecodecs -> Pillow
            a = np.array(Image.open(path))
    a = a.astype(np.float32)
    nod = float(str(nod).strip("\x00")) if nod not in (None, "") else None
    if nod is not None:
        a[a == nod] = np.nan
    return a, dict(x0=tp[3] - tp[0] * sx, y0=tp[4] + tp[1] * sy, dx=sx, dy=sy, nodata=nod)


def escrever(path, arr, x0, y0, dx, nodata=-9999.0, epsg=25829):
    a = np.where(np.isfinite(arr), arr, nodata).astype(np.float32)
    geokeys = (1, 1, 0, 3,
               1024, 0, 1, 1,        # ModelTypeProjected
               1025, 0, 1, 1,        # RasterPixelIsArea
               3072, 0, 1, epsg)     # ProjectedCSType
    extra = [
        (33550, "d", 3, (dx, dx, 0.0), True),
        (33922, "d", 6, (0.0, 0.0, 0.0, x0, y0, 0.0), True),
        (34735, "H", len(geokeys), geokeys, True),
        (42113, "s", 0, str(nodata), True),
    ]
    tifffile.imwrite(path, a, extratags=extra, compression="zlib", tile=(256, 256))


if __name__ == "__main__":  # teste de ida e volta
    import os, tempfile
    z = np.arange(12, dtype=np.float32).reshape(3, 4); z[0, 0] = np.nan
    f = os.path.join(tempfile.gettempdir(), "t.tif")
    escrever(f, z, 600000.0, 4200000.0, 30.0)
    b, g = ler(f)
    assert np.allclose(np.nan_to_num(b), np.nan_to_num(z)) and g["x0"] == 600000 and g["y0"] == 4200000
    x, y = fwd(38.1966, -7.4963)          # aprox. barragem de Alqueva
    lat, lon = inv(x, y)
    print("ok", round(x), round(y), round(lat, 6), round(lon, 6))
