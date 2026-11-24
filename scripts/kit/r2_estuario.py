"""Canal sintético do estuário do Guadiana (Mértola → foz) sobre o plano de água a 0 m do LiDAR.
Secção parabólica: d = Dmax·(1−(1−e/W)²), e = distância à margem, W = meia-largura local.
Profundidade média por troço (km desde a foz; Garel, UAlg/CIMA): 0–10: 4,1 m; 10–50: 5,9 m; 50–72: 3,2 m."""
import numpy as np, sys
from scipy import ndimage
from skimage.graph import MCP_Geometric
sys.path.insert(0, '.')
from geoio import escrever
Z = np.load('lidar10.npy'); x0, y0 = 611925.0, 4232805.0
ys = y0 - 5 - 10 * np.arange(Z.shape[0]); xs = x0 + 5 + 10 * np.arange(Z.shape[1])
agua = (Z > -0.8) & (Z < 0.3) & (ys[:, None] < 4170000) & (ys[:, None] > 4115400)
lab, n = ndimage.label(ndimage.binary_closing(agua, iterations=3), structure=np.ones((3, 3)))
# componente principal = a que contém o canal junto a VRSA e a Alcoutim
cnt = np.bincount(lab.ravel()); cnt[0] = 0
keep = lab == np.argmax(cnt)
keep = ndimage.binary_fill_holes(keep)
print('área do plano a 0 m (componente principal) km2', round(keep.sum() * 1e-4, 2), '| todas', round(agua.sum() * 1e-4, 2))
# quilometragem desde a foz (distância geodésica dentro da água)
cost = np.where(keep, 1.0, np.inf)
ifoz = np.argmin(abs(ys - 4115420)); starts = [(ifoz, j) for j in np.nonzero(keep[ifoz])[0]]
if not starts:
    r = np.nonzero(keep.any(1))[0].max(); starts = [(r, j) for j in np.nonzero(keep[r])[0]]
km = MCP_Geometric(cost).find_costs(starts)[0] * 10 / 1000.0
km[~keep] = np.nan
print('km máximo (Mértola)', round(np.nanmax(km), 1))
e = ndimage.distance_transform_edt(keep) * 10.0          # m até à margem
# meia-largura W por troço de 250 m: máximo de e
b = np.floor(km / 0.25); b[~keep] = -1; b = b.astype(int)
Wb = ndimage.maximum(e, b, index=np.arange(b.max() + 1))
W = np.where(keep, np.asarray(Wb)[np.clip(b, 0, None)], np.nan)
forma = np.clip(1 - (1 - np.minimum(e / W, 1)) ** 2, 0, 1)
alvo = [(0, 10, 4.1), (10, 50, 5.9), (50, 1e9, 3.2)]
D = np.zeros_like(Z)
for a, z, med in alvo:
    m = keep & (km >= a) & (km < z)
    if not m.any(): continue
    Dmax = med / forma[m].mean()
    D[m] = Dmax * forma[m]
    if not m.any(): continue
    print(f'km {a}-{min(z, np.nanmax(km)):.0f}: Dmax={Dmax:4.1f} m  média={D[m].mean():.2f}  máx={D[m].max():.1f}  área={m.sum()*1e-4:5.2f} km2')
# suaviza os degraus entre troços (janela de ~1 km ao longo do canal)
Ds = ndimage.uniform_filter(np.where(keep, D, 0), 101) / np.maximum(ndimage.uniform_filter(keep.astype(float), 101), 1e-6)
fs = ndimage.uniform_filter(np.where(keep, forma, 0), 101) / np.maximum(ndimage.uniform_filter(keep.astype(float), 101), 1e-6)
Dfin = np.where(keep, Ds / np.maximum(fs, 1e-3) * forma, np.nan)
for a, z, med in alvo:
    m = keep & (km >= a) & (km < z)
    if m.any(): print(f'  suavizado km {a}: média={np.nanmean(Dfin[m]):.2f} máx={np.nanmax(Dfin[m]):.1f}')
out = np.where(keep, -Dfin, np.nan).astype(np.float32)
ii, jj = np.nonzero(keep); r0, r1, c0, c1 = ii.min() - 2, ii.max() + 3, jj.min() - 2, jj.max() + 3
escrever('canal_estuario_25829_10m.tif', out[r0:r1, c0:c1], x0 + 10 * c0, y0 - 10 * r0, 10.0)
np.save('km_foz.npy', km)
