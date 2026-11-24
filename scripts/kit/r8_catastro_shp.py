"""Catastro INSPIRE (edifícios, GML, EPSG 25829) → um shapefile único com os 7 municípios de Huelva."""
import re, glob, struct, numpy as np, sys, os
fl = sorted(glob.glob(sys.argv[1] + '/A.ES.SDGC.BU.*.building.gml'))
MUN = {'21010': 'Ayamonte', '21072': 'Villablanca', '21065': 'San Silvestre de Guzman', '21064': 'Sanlucar de Guadiana',
       '21037': 'El Granado', '21058': 'Puebla de Guzman', '21057': 'Paymogo'}
recs = []
tag = lambda b, t: (re.search(rf'<bu-ext2d:{t}>([^<]*)</bu-ext2d:{t}>', b) or [None, ''])[1]
for f in fl:
    cod = re.search(r'BU\.(\d{5})\.building', f).group(1)
    s = open(f, encoding='latin-1').read()
    for b in re.findall(r'<bu-ext2d:Building .*?</bu-ext2d:Building>', s, re.S):
        ref = re.search(r'<base:localId>([^<]*)', b).group(1)
        rings = []
        for kind, pl in re.findall(r'<gml:(exterior|interior)>\s*<gml:LinearRing>\s*<gml:posList[^>]*>([^<]*)', b):
            v = np.array(pl.split(), float).reshape(-1, 2)
            a = 0.5 * np.sum(v[:-1, 0] * v[1:, 1] - v[1:, 0] * v[:-1, 1])
            if (kind == 'exterior' and a > 0) or (kind == 'interior' and a < 0):
                v = v[::-1]
            rings.append(v)
        if not rings:
            continue
        ano = (re.search(r'<bu-core2d:beginning>(\d{4})', b) or [None, ''])[1]
        area = (re.search(r'<bu-ext2d:value uom="m2">([^<]*)', b) or [None, '0'])[1]
        recs.append(dict(REFCAT=ref, MUN=MUN.get(cod, cod), USO=tag(b, 'currentUse'), N_VIV=tag(b, 'numberOfDwellings') or '0',
                         N_UNID=tag(b, 'numberOfBuildingUnits') or '0', ANO=ano, AREA_M2=area, rings=rings))
print('edifícios', len(recs))
from collections import Counter
print(Counter(r['MUN'] for r in recs)); print(Counter(r['USO'] for r in recs).most_common(8))
print('habitações', sum(int(r['N_VIV'] or 0) for r in recs))
# shapefile
def bbox(p): return p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()
shp, shx, off = bytearray(), bytearray(), 50
allp = np.vstack([np.vstack(r['rings']) for r in recs]); BB = bbox(allp)
for i, r in enumerate(recs):
    pts = np.vstack(r['rings'])
    c = struct.pack('<i', 5) + struct.pack('<4d', *bbox(pts)) + struct.pack('<2i', len(r['rings']), len(pts))
    k = 0
    for p in r['rings']:
        c += struct.pack('<i', k); k += len(p)
    c += pts.astype('<f8').tobytes()
    L = len(c) // 2; shx += struct.pack('>2i', off, L); shp += struct.pack('>2i', i + 1, L) + c; off += 4 + L
hdr = lambda n: struct.pack('>7i', 9994, 0, 0, 0, 0, 0, n) + struct.pack('<2i', 1000, 5) + struct.pack('<4d', *BB) + struct.pack('<4d', 0, 0, 0, 0)
o = sys.argv[2]
open(o + '.shp', 'wb').write(hdr(50 + len(shp) // 2) + shp); open(o + '.shx', 'wb').write(hdr(50 + len(shx) // 2) + shx)
F = [('REFCAT', 'C', 20), ('MUN', 'C', 24), ('USO', 'C', 24), ('N_VIV', 'N', 6), ('N_UNID', 'N', 6), ('ANO', 'C', 4), ('AREA_M2', 'N', 10)]
hl = 32 + 32 * len(F) + 1; rl = 1 + sum(w for _, _, w in F)
d = bytearray(struct.pack('<BBBBIHH20x', 3, 126, 11, 22, len(recs), hl, rl))
for n, t, w in F: d += n.encode().ljust(11, b'\0') + t.encode() + b'\0' * 4 + bytes([w, 0]) + b'\0' * 14
d += b'\r'
for r in recs:
    d += b' ' + b''.join((str(r[n]).encode('latin-1').rjust(w) if t == 'N' else str(r[n]).encode('latin-1').ljust(w))[:w] for n, t, w in F)
d += b'\x1a'; open(o + '.dbf', 'wb').write(d)
open(o + '.cpg', 'w').write('ISO-8859-1')
open(o + '.prj', 'w').write(open('bgri/bgri2021_corredor_25829.prj').read())
