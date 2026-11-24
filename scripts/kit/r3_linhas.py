"""Linhas de referência novas (P14, P20, P24, P28, P43, P52) e P09 a 0,5 km a jusante de Pedrógão.
Perpendiculares ao eixo, estendidas até o terreno passar Nmax(PEExt)+10 m, recortadas ao Perimeter 1."""
import numpy as np, json
from matplotlib.path import Path
G = '/mnt/user-data/uploads/rotura-alqueva/hecras/rotura_alqueva.g04'
L = open(G, encoding='latin-1').read().splitlines()
perim = np.array([[float(v) for v in L[k].split()] for k in range(7160, 7160 + 211)])
PP = Path(perim)
Z = np.load('lidar10.npy'); x0, y0 = 611925.0, 4232805.0
def z(x, y):
    i = int((y0 - y) // 10); j = int((x - x0) // 10)
    return Z[i, j] if 0 <= i < Z.shape[0] and 0 <= j < Z.shape[1] else np.nan
px, py, ch, zt = np.load('eixo.npy').T
ctrl_km = [5.0, 9.0, 26.7, 45.7, 71.7, 89.7, 104.7, 122.7, 138.7]
ctrl_ch = [0.0, 3.85, 20.81, 38.15, 61.59, 81.82, 100.30, 112.36, 128.51]
def km2ch(k):
    if k > ctrl_km[-1]: return ctrl_ch[-1] + (k - ctrl_km[-1])  # extrapola com o último desvio
    return float(np.interp(k, ctrl_km, ctrl_ch))
novas = {  # nome: (km PEExt, Nmax PEExt)
    'P09_Pedrogao_jus': (None, 92.32), 'P14': (37.7, 81.67), 'P20': (54.7, 69.26), 'P24': (65.7, 55.91),
    'P28': (73.7, 40.56), 'P43': (116.7, 17.18), 'P52': (144.7, 4.98)}
res = {}
for nome, (km, nmax) in novas.items():
    c = 20.81 + 0.5 if km is None else km2ch(km)
    i = int(np.argmin(abs(ch - c)))
    a, b = max(i - 10, 0), min(i + 10, len(ch) - 1)
    t = np.array([px[b] - px[a], py[b] - py[a]]); t /= np.hypot(*t); nrm = np.array([-t[1], t[0]])
    P0 = np.array([px[i], py[i]]); lim = nmax + 10
    ends = []
    for s in (1, -1):
        d = 0; last = P0
        while d < 6000:
            d += 10; Q = P0 + s * d * nrm
            if not PP.contains_point(Q): break
            last = Q
            zz = z(*Q)
            if np.isfinite(zz) and zz > lim and d > 100: break
        ends.append(last)
    A, B = ends
    res[nome] = dict(km_peext=km, ch=round(c, 2), z_eixo=float(z(*P0)), nmax=nmax, A=A.round(1).tolist(), B=B.round(1).tolist(),
                     comp_m=round(float(np.hypot(*(A - B)))), dentro=bool(PP.contains_point(A) and PP.contains_point(B)))
    print(nome, res[nome])
json.dump(res, open('linhas_novas.json', 'w'), indent=1)
