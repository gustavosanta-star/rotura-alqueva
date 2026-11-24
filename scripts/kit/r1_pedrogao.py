"""Fundo da albufeira de Pedrógão: SRTM (fev. 2000, antes do enchimento em 2005) dentro do plano de água do LiDAR."""
import numpy as np, sys
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator
sys.path.insert(0, '.')
from geoio import ler, escrever
B = '/mnt/user-data/uploads/rotura-alqueva/'
Z = np.load('lidar10.npy'); _, g = ler(B + 'dados/terreno/terreno_10m_final.tif')
ys = g['y0'] - 5 - 10 * np.arange(Z.shape[0]); xs = g['x0'] + 5 + 10 * np.arange(Z.shape[1])
# 1) plano de água entre as barragens (Pedrógão y≈4218965; Alqueva y=4228790)
plano = (Z >= 79.0) & (Z < 80.5) & (ys[:, None] > 4218600) & (ys[:, None] < 4228790)
lab, n = ndimage.label(plano)
i0, j0 = np.argmin(abs(ys - 4219600)), np.argmin(abs(xs - 620300))
w = lab[i0-60:i0+60, j0-60:j0+60]; vals, cnt = np.unique(w[w > 0], return_counts=True)
comp = vals[np.argmax(cnt)]
sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n+1))
# junta componentes grandes (o plano pode estar cortado por pontes)
keep = np.isin(lab, [comp] + [k+1 for k, s in enumerate(sizes) if s > 20000])
keep = ndimage.binary_closing(keep, iterations=3) & np.isfinite(Z)
keep = ndimage.binary_fill_holes(keep)
nivel = float(np.median(Z[keep & plano]))
print('componentes', n, 'area plano km2', keep.sum() * 1e-4, 'nivel LiDAR', round(nivel, 2))
# 2) SRTM 1" (tile N38W008, PixelIsPoint, EGM96) reprojetado para os centros das células de 10 m; −1 m como no G03
from tm import inv
T, _ = ler(B + 'dados/srtm/n38_w008_1arc_v3.tif')
lat_ax = 39.0 - np.arange(T.shape[0]) / 3600.0; lon_ax = -8.0 + np.arange(T.shape[1]) / 3600.0
f = RegularGridInterpolator((lat_ax[::-1], lon_ax), T[::-1], bounds_error=False, fill_value=np.nan)
ii, jj = np.nonzero(keep)
la, lo = inv(xs[jj], ys[ii])
zs = f(np.c_[la, lo]) - 1.0
zs = np.minimum(zs, nivel - 0.5)          # o fundo nunca acima do plano de água
out = np.full(Z.shape, np.nan, np.float32); out[ii, jj] = zs
r0, r1 = ii.min() - 2, ii.max() + 3; c0, c1 = jj.min() - 2, jj.max() + 3
sub = out[r0:r1, c0:c1]
escrever('srtm_pedrogao_25829_10m.tif', sub, g['x0'] + 10 * c0, g['y0'] - 10 * r0, 10.0)
print('NaN no fundo', np.isnan(zs).sum(), 'min/med', np.nanmin(zs), np.nanmedian(zs))
# 3) volume a 84,8 m com o terreno combinado
C = Z.copy(); C[ii, jj] = zs
reg = (ys[:, None] > 4218700) & (ys[:, None] < 4228790)
for h in [80.0, 84.6, 84.8]:
    m = (C < h) & reg & np.isfinite(C)
    lab2, _ = ndimage.label(m); R = np.isin(lab2, np.unique(lab2[ii, jj][lab2[ii, jj] > 0]))
    print(f'{h}: V={((h - C)[R]).sum() * 100 / 1e6:6.1f} hm3  A={R.sum() * 1e-4:5.2f} km2   (só LiDAR: {((h - Z)[R & (Z < h)]).sum() * 100 / 1e6:5.1f} hm3)')
np.save('pedrogao_keep.npy', np.array([r0, r1, c0, c1]))
