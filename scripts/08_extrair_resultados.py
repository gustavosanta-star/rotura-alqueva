"""08_extrair_resultados.py
Extrai do ficheiro de resultados do HEC-RAS (p02.hdf) os hidrogramas das
Reference Lines, das ligações SA/2D e da Storage Area, e grava CSV pequenos.

Correr no ArcGIS Pro (tem h5py):
    Iniciar > ArcGIS > Python Command Prompt
    cd "C:\\caminho\\para\\rotura-alqueva"
    python scripts\\08_extrair_resultados.py hecras\\rotura_alqueva.p02.hdf

Saída: pasta resultados\\p02\\ com
    estrutura_hdf.txt     lista de todos os grupos/datasets (para diagnóstico)
    tempo.csv             data/hora de cada registo
    <grupo>_<variavel>.csv  uma coluna por objeto (Reference Line, ligação, ...)
"""
import sys, os, csv
import numpy as np
import h5py

hdf_path = sys.argv[1] if len(sys.argv) > 1 else r"hecras\rotura_alqueva.p02.hdf"
plan = os.path.splitext(os.path.splitext(os.path.basename(hdf_path))[0])[1].lstrip(".") or "p02"
out = os.path.join("resultados", plan)
os.makedirs(out, exist_ok=True)

f = h5py.File(hdf_path, "r")

# 1) estrutura completa (só nomes, formas e tipos)
with open(os.path.join(out, "estrutura_hdf.txt"), "w", encoding="utf-8") as fh:
    def show(name, obj):
        if isinstance(obj, h5py.Dataset):
            fh.write(f"D {name}  {obj.shape}  {obj.dtype}\n")
        else:
            fh.write(f"G {name}\n")
        for k, v in obj.attrs.items():
            try:
                s = v.decode() if isinstance(v, bytes) else (str(v.tolist()) if hasattr(v, "tolist") else str(v))
            except Exception:
                s = "?"
            fh.write(f"    @{k} = {s[:200]}\n")
    f.visititems(show)

def dec(a):
    return [x.decode(errors="ignore").strip() if isinstance(x, (bytes, np.bytes_)) else str(x).strip() for x in a]

# 2) eixo do tempo de cada bloco de séries temporais
base = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
if base not in f:
    # procurar um bloco alternativo
    cands = []
    f.visit(lambda n: cands.append(n) if n.endswith("Unsteady Time Series") else None)
    base = cands[0] if cands else None
if base is None:
    sys.exit("Não encontrei 'Unsteady Time Series' no HDF; ver estrutura_hdf.txt")

g = f[base]
tempo = None
for key in ("Time Date Stamp", "Time Date Stamp (ms)"):
    if key in g:
        tempo = dec(g[key][()])
        break
t_dias = g["Time"][()] if "Time" in g else np.arange(len(tempo))
with open(os.path.join(out, "tempo.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["indice", "data_hora", "dias"])
    for i, td in enumerate(t_dias):
        w.writerow([i, tempo[i] if tempo else "", float(td)])

# 3) nomes dos objetos (a partir da geometria guardada no próprio p02.hdf)
def nomes(geo_path):
    if geo_path in f:
        d = f[geo_path]
        if d.dtype.names and "Name" in d.dtype.names:
            return dec(d["Name"])
    return None

nomes_ref = nomes("Geometry/Reference Lines/Attributes")
nomes_conn = nomes("Geometry/Structures/Attributes")

# 4) despejar todos os datasets 1D/2D de séries temporais que não sejam células da malha
n_t = len(t_dias)
escritos = []
def dump(name, obj):
    if not isinstance(obj, h5py.Dataset):
        return
    if obj.ndim == 0 or obj.shape[0] != n_t:
        return
    if obj.dtype.kind not in "fiu":            # texto (datas) ou tabelas compostas: saltar
        return
    if obj.ndim == 2 and obj.shape[1] > 5000:   # células da malha: demasiado grande
        return
    arr = obj[()]
    if arr.ndim == 1:
        arr = arr[:, None]
    cols = None
    nm = obj.attrs.get("Names")
    if nm is None:
        nm = obj.attrs.get("Name")
    if nm is not None:
        try:
            cols = dec(np.atleast_1d(nm))
        except Exception:
            cols = None
    if cols is None or len(cols) != arr.shape[1]:
        if "Reference Lines" in name and nomes_ref and len(nomes_ref) == arr.shape[1]:
            cols = nomes_ref
        elif nomes_conn and len(nomes_conn) == arr.shape[1] and ("Conn" in name or "Structure" in name):
            cols = nomes_conn
        else:
            cols = [f"c{j}" for j in range(arr.shape[1])]
    fname = name.replace(base + "/", "").replace("/", "__").replace(" ", "_") + ".csv"
    with open(os.path.join(out, fname), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["indice"] + cols)
        for i in range(arr.shape[0]):
            w.writerow([i] + [f"{v:.4f}" for v in arr[i]])
    escritos.append((fname, arr.shape))
g.visititems(lambda n, o: dump(base + "/" + n, o))

# 5) máximos da malha nas células atravessadas pelas Reference Lines (se existirem no HDF)
with open(os.path.join(out, "resumo.txt"), "w", encoding="utf-8") as fh:
    fh.write(f"Ficheiro: {hdf_path}\nRegistos de tempo: {n_t}\n")
    if tempo:
        fh.write(f"Início: {tempo[0]}  Fim: {tempo[-1]}\n")
    fh.write(f"Reference Lines: {nomes_ref}\nEstruturas: {nomes_conn}\n\nCSV escritos:\n")
    for fn, sh in escritos:
        fh.write(f"  {fn}  {sh}\n")

print("Feito. Resultados em", out)
for fn, sh in escritos:
    print("  ", fn, sh)
