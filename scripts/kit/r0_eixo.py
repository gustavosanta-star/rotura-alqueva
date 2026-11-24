"""Eixo do rio (talvegue) da barragem de Alqueva à foz, quilometragem e calibração com os km do PEExt."""
import numpy as np, time
from scipy import ndimage
from skimage.graph import MCP_Geometric
Z = np.load('lidar10.npy'); x0, y0 = 611925.0, 4232805.0
ys = y0 - 5 - 10 * np.arange(Z.shape[0]); xs = x0 + 5 + 10 * np.arange(Z.shape[1])
t = time.time()
Zf = np.where(np.isfinite(Z), Z, 9999)
# a 20 m para ser mais rápido
Zc = Zf[::2, ::2]; ysc = ys[::2]; xsc = xs[::2]
loc = ndimage.minimum_filter(Zc, size=101)
rel = Zc - loc
cost = 1 + (np.clip(rel, 0, None) / 2.0) ** 2
cost[Zc > 9000] = np.inf
def ij(x, y): return int(np.argmin(abs(ysc - y))), int(np.argmin(abs(xsc - x)))
ini = ij(631781, 4228650); fim = ij(640500, 4115500)
m = MCP_Geometric(cost); m.find_costs([ini], [fim])
path = np.array(m.traceback(fim))
px, py = xsc[path[:, 1]], ysc[path[:, 0]]
# alisa o eixo (média móvel de ~300 m) e calcula a distância acumulada
k = 15; pxs = np.convolve(np.r_[[px[0]]*k, px, [px[-1]]*k], np.ones(2*k+1)/(2*k+1), 'valid')
pys = np.convolve(np.r_[[py[0]]*k, py, [py[-1]]*k], np.ones(2*k+1)/(2*k+1), 'valid')
ch = np.r_[0, np.cumsum(np.hypot(np.diff(pxs), np.diff(pys)))] / 1000
zt = Zc[path[:, 0], path[:, 1]]
np.save('eixo.npy', np.c_[pxs, pys, ch, zt])
print('pontos', len(path), 'comprimento km', round(ch[-1], 1), 'tempo', round(time.time() - t))
