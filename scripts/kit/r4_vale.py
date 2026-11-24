"""Máscara do vale profundo entre Pedrógão e Odeleite: células abaixo de talvegue + 30 m, ligadas ao rio.
Uso: n = 0,040 nestas células (script 12), em vez dos valores COS de matos/floresta."""
import numpy as np, sys
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, '.')
from geoio import escrever
Z = np.load('lidar10.npy'); x0, y0 = 611925.0, 4232805.0
px, py, ch, zt = np.load('eixo.npy').T
# talvegue: mínimo local ao longo do eixo, monotónico para jusante
zs = ndimage.minimum_filter1d(zt, 25)
zs = np.minimum.accumulate(zs)
sel = (ch >= 20.81) & (ch <= 128.51)
tree = cKDTree(np.c_[px, py])
ys = y0 - 5 - 10 * np.arange(Z.shape[0]); xs = x0 + 5 + 10 * np.arange(Z.shape[1])
r = np.nonzero((ys < py[sel].max() + 3000) & (ys > py[sel].min() - 3000))[0]
c = np.nonzero((xs < px[sel].max() + 3000) & (xs > px[sel].min() - 3000))[0]
sub = Z[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
YY, XX = np.meshgrid(ys[r], xs[c], indexing='ij')
d, k = tree.query(np.c_[XX.ravel(), YY.ravel()], distance_upper_bound=3000)
k = k.reshape(sub.shape); d = d.reshape(sub.shape)
ok = np.isfinite(d)
kk = np.where(ok, k, 0)
m = ok & sel[kk] & np.isfinite(sub) & (sub < zs[kk] + 30)
# só o que está ligado ao eixo
lab, _ = ndimage.label(m)
ei = ((y0 - py[sel]) // 10).astype(int) - r[0]; ej = ((px[sel] - x0) // 10).astype(int) - c[0]
ids = np.unique(lab[ei, ej]); ids = ids[ids > 0]
m = np.isin(lab, ids)
print('área km2', round(m.sum() * 1e-4, 1))
for a, b in [(20.81, 61.6), (61.6, 81.8), (81.8, 128.51)]:
    print(f'  ch {a:.0f}-{b:.0f} km: {((m) & (ch[kk] >= a) & (ch[kk] < b)).sum() * 1e-4:5.1f} km2')
out = np.where(m, 1.0, np.nan).astype(np.float32)
ii, jj = np.nonzero(m)
escrever('vale_profundo_mask.tif', out[ii.min():ii.max() + 1, jj.min():jj.max() + 1],
         x0 + 10 * (c[0] + jj.min()), y0 - 10 * (r[0] + ii.min()), 10.0)
