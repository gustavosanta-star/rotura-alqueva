"""Recorta a grelha JRC-ESTAT 2021 (100 m, EPSG 3035, LZW) ao corredor e grava as células com população
como polígonos em EPSG 25829 (shapefile). Descodificador LZW próprio (sem imagecodecs)."""
import numpy as np, tifffile, struct, sys
sys.path.insert(0, '.')
from tm import inv, fwd

def lzw_decode(data):
    # LZW de TIFF (MSB-first, códigos 9–12 bits, early change)
    out = bytearray(); tab = [bytes([i]) for i in range(256)] + [b'', b'']
    nbits, pos, prev, n = 9, 0, None, len(data) * 8
    while pos + nbits <= n:
        byte = pos >> 3; chunk = int.from_bytes(data[byte:byte + 3].ljust(3, b'\0'), 'big')
        code = (chunk >> (24 - (pos & 7) - nbits)) & ((1 << nbits) - 1); pos += nbits
        if code == 256:
            tab = tab[:258]; nbits = 9; prev = None; continue
        if code == 257: break
        if prev is None:
            e = tab[code]; out += e; prev = e; continue
        e = tab[code] if code < len(tab) else prev + prev[:1]
        out += e; tab.append(prev + e[:1]); prev = e
        if len(tab) + 1 >= (1 << nbits) and nbits < 12: nbits += 1
    return bytes(out)

# LAEA ETRS89 (EPSG 3035), forma elipsoidal
a = 6378137.0; f = 1 / 298.257222101; e2 = f * (2 - f); e = np.sqrt(e2)
def q(phi): s = np.sin(phi); return (1 - e2) * (s / (1 - e2 * s * s) - (1 / (2 * e)) * np.log((1 - e * s) / (1 + e * s)))
p0, l0 = np.radians(52), np.radians(10); qp = q(np.pi / 2); Rq = a * np.sqrt(qp / 2)
b0 = np.arcsin(q(p0) / qp); D = a * (np.cos(p0) / np.sqrt(1 - e2 * np.sin(p0) ** 2)) / (Rq * np.cos(b0))
def laea_fwd(lat, lon):
    b = np.arcsin(q(np.radians(lat)) / qp); dl = np.radians(lon) - l0
    B = Rq * np.sqrt(2 / (1 + np.sin(b0) * np.sin(b) + np.cos(b0) * np.cos(b) * np.cos(dl)))
    return 4321000 + B * D * np.cos(b) * np.sin(dl), 3210000 + (B / D) * (np.cos(b0) * np.sin(b) - np.sin(b0) * np.cos(b) * np.cos(dl))
def laea_inv(x, y):
    x = x - 4321000; y = y - 3210000; rho = np.sqrt((x / D) ** 2 + (D * y) ** 2); C = 2 * np.arcsin(rho / (2 * Rq))
    bb = np.arcsin(np.cos(C) * np.sin(b0) + D * y * np.sin(C) * np.cos(b0) / rho)
    lon = l0 + np.arctan2(x * np.sin(C), D * rho * np.cos(b0) * np.cos(C) - D ** 2 * y * np.sin(b0) * np.sin(C))
    phi = bb
    for _ in range(6):
        s = np.sin(phi); phi = phi + (1 - e2 * s * s) ** 2 / (2 * np.cos(phi)) * (q(phi) / (1 - e2) - s / (1 - e2 * s * s) + (1 / (2 * e)) * np.log((1 - e * s) / (1 + e * s)))
        phi = bb if False else phi
        phi = np.arcsin(np.clip(np.sin(phi), -1, 1)) if False else phi
    # iteração correta (Snyder 3-16)
    phi = bb
    for _ in range(8):
        s = np.sin(phi)
        phi = phi + (1 - e2 * s * s) ** 2 / (2 * np.cos(phi)) * ((qp * np.sin(bb)) / (1 - e2) - s / (1 - e2 * s * s) + (1 / (2 * e)) * np.log((1 - e * s) / (1 + e * s)))
    return np.degrees(phi), np.degrees(lon)

t = tifffile.TiffFile(sys.argv[1]); p = t.pages[0]
X0, Y0 = p.tags['ModelTiepointTag'].value[3:5]; TS = 256; H, W = p.shape; ntx = -(-W // TS)
# caixa do corredor em UTM 29N → LAEA (com margem)
ux = np.array([603000, 653000, 603000, 653000, 628000, 628000]); uy = np.array([4107000, 4107000, 4240000, 4240000, 4107000, 4240000])
la, lo = inv(ux, uy); lx, ly = laea_fwd(la, lo)
c0, c1 = int((lx.min() - X0) // 100), int((lx.max() - X0) // 100) + 1
r0, r1 = int((Y0 - ly.max()) // 100), int((Y0 - ly.min()) // 100) + 1
print('janela', r0, r1, c0, c1)
fh = t.filehandle
sub = np.full((r1 - r0, c1 - c0), -1, np.int16)
for tr in range(r0 // TS, (r1 - 1) // TS + 1):
    for tc in range(c0 // TS, (c1 - 1) // TS + 1):
        k = tr * ntx + tc; fh.seek(p.dataoffsets[k]); raw = fh.read(p.databytecounts[k])
        tile = np.frombuffer(lzw_decode(raw)[:TS * TS * 2], '<i2').reshape(TS, TS)
        R0, C0 = tr * TS, tc * TS
        rs, re_ = max(R0, r0), min(R0 + TS, r1); cs, ce = max(C0, c0), min(C0 + TS, c1)
        sub[rs - r0:re_ - r0, cs - c0:ce - c0] = tile[rs - R0:re_ - R0, cs - C0:ce - C0]
ii, jj = np.nonzero(sub > 0); pop = sub[ii, jj].astype(int)
print('células com população', len(pop), 'total', pop.sum())
# polígonos (4 cantos) em EPSG 25829
xl = X0 + (c0 + jj) * 100.0; yt = Y0 - (r0 + ii) * 100.0
corn = [(xl, yt), (xl + 100, yt), (xl + 100, yt - 100), (xl, yt - 100), (xl, yt)]
U = []
for cx, cy in corn:
    la_, lo_ = laea_inv(cx, cy); U.append(np.c_[fwd(la_, lo_)])
U = np.stack(U, 1)  # n x 5 x 2 (sentido horário em LAEA → mantém-se em UTM)
cx = U[:, :4, 0].mean(1); cy = U[:, :4, 1].mean(1)
keep = (cx > 603000) & (cx < 653000) & (cy > 4107000) & (cy < 4240000)
U, pop = U[keep], pop[keep]
print('no corredor', len(pop), 'pessoas', pop.sum())
o = sys.argv[2]
BB = (U[..., 0].min(), U[..., 1].min(), U[..., 0].max(), U[..., 1].max())
shp, shx, off = bytearray(), bytearray(), 50
for i, r in enumerate(U):
    c = struct.pack('<i', 5) + struct.pack('<4d', r[:, 0].min(), r[:, 1].min(), r[:, 0].max(), r[:, 1].max()) + struct.pack('<3i', 1, 5, 0) + r.astype('<f8').tobytes()
    L = len(c) // 2; shx += struct.pack('>2i', off, L); shp += struct.pack('>2i', i + 1, L) + c; off += 4 + L
hdr = lambda n: struct.pack('>7i', 9994, 0, 0, 0, 0, 0, n) + struct.pack('<2i', 1000, 5) + struct.pack('<4d', *BB) + struct.pack('<4d', 0, 0, 0, 0)
open(o + '.shp', 'wb').write(hdr(50 + len(shp) // 2) + shp); open(o + '.shx', 'wb').write(hdr(50 + len(shx) // 2) + shx)
d = bytearray(struct.pack('<BBBBIHH20x', 3, 126, 11, 22, len(pop), 65, 7)) + b'POP'.ljust(11, b'\0') + b'N' + b'\0' * 4 + bytes([6, 0]) + b'\0' * 14 + b'\r'
for v in pop: d += b' ' + str(int(v)).encode().rjust(6)
d += b'\x1a'; open(o + '.dbf', 'wb').write(d)
open(o + '.prj', 'w').write(open('bgri/bgri2021_corredor_25829.prj').read())
np.save('jrc_cells.npy', np.c_[cx[keep] if False else U[:, :4, 0].mean(1), U[:, :4, 1].mean(1), pop])
