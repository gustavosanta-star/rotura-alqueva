"""11_comparar_peext.py — compara um plano com a Tabela I.5 do PEExt (cenário mais gravoso).

Uso (Python Command Prompt do ArcGIS Pro, na pasta do projeto, depois do 08):
    python scripts\\11_comparar_peext.py p11 30
    python scripts\\11_comparar_peext.py p12 30
    python scripts\\11_comparar_peext.py p10 30      (linha de base, mesma métrica)

Argumentos: plano (pasta em resultados\\) e t0 = horas desde o início da simulação
até ao início do pulso do PEExt (30 h nos planos de teste P10/P11/P12).

Definições (iguais para todos os planos):
  Qmax, Nmax  máximos depois de t0 (Reference Lines: Flow e Water Surface)
  tQmax       instante do caudal máximo − t0 (h)
  tNmax       instante do nível máximo − t0 (h)      → compara com tNmax do PEExt
  chegada     1.º instante em que o nível sobe ≥ 20 % da subida máxima (h)
              → compara com a "chegada onda de cheia" do PEExt
              (a definição usada antes de 20/11 perdeu-se; por isso recalcula-se o P10)

Critério de congelamento (até Alcoutim, P45): Nmax ±3 m, chegada ±30 %, Qmax ±25 %.
Saída: resultados\\<plano>\\comparacao_peext.csv e tabela no ecrã.
"""
import csv, os, re, sys

# Tabela I.5 do PEExt: perfil -> (km, Qmax m3/s, Nmax m, tNmax h, chegada h)
PEEXT = {
    3: (9.0, 135502, 116.44, 0.22, 0.07),   9: (26.7, 56471, 92.32, 0.60, 0.41),
    10: (28.7, 56471, 90.00, 0.65, 0.45),  14: (37.7, 41193, 81.67, 1.01, 0.63),
    17: (45.7, 35302, 76.16, 1.34, 0.79),  20: (54.7, 30498, 69.26, 1.81, 1.01),
    24: (65.7, 27869, 55.91, 2.15, 1.28),  26: (71.7, 27549, 42.75, 2.51, 1.69),
    28: (73.7, 27366, 40.56, 2.61, 1.69),  34: (89.7, 25500, 30.78, 3.42, 1.82),
    39: (104.7, 23895, 24.12, 3.87, 2.12), 43: (116.7, 23262, 17.18, 4.47, 2.54),
    45: (122.7, 22883, 15.02, 4.73, 2.64), 50: (138.7, 22214, 8.54, 5.27, 3.28),
    52: (144.7, 22106, 4.98, 5.58, 4.30),
}
# a P09 do G05/G06 está 0,5 km a jusante da barragem de Pedrógão: interpola P9–P10 (km 27,2)
_a, _b = PEEXT[9], PEEXT[10]
PEEXT_P09 = tuple(_a[i] + (_b[i] - _a[i]) * 0.25 for i in range(5))

def ler(path):
    with open(path, encoding="utf-8") as f:
        r = list(csv.reader(f))
    cab = r[0][1:]
    cols = {c: [float(l[k + 1]) for l in r[1:]] for k, c in enumerate(cab)}
    return cols

def main(plano, t0):
    base = os.path.join("resultados", plano)
    with open(os.path.join(base, "tempo.csv"), encoding="utf-8") as f:
        t = [float(l["dias"]) * 24 for l in csv.DictReader(f)]
    Q = ler(os.path.join(base, "Reference_Lines__Flow.csv"))
    W = ler(os.path.join(base, "Reference_Lines__Water_Surface.csv"))
    i0 = min(range(len(t)), key=lambda i: abs(t[i] - t0))
    linhas = []
    for nome in Q:
        m = re.match(r"P(\d+)", nome)
        if not m:
            continue
        n = int(m.group(1))
        if n == 9 and plano not in ("p09", "p10"):
            ref = PEEXT_P09
        elif n in PEEXT:
            ref = PEEXT[n]
        else:
            continue
        q, w = Q[nome][i0:], W[nome][i0:]
        tt = t[i0:]
        iq = max(range(len(q)), key=q.__getitem__); iw = max(range(len(w)), key=w.__getitem__)
        subida = w[iw] - w[0]
        ich = next((i for i, v in enumerate(w) if v - w[0] >= 0.2 * subida), None) if subida > 0 else None
        r = dict(linha=nome, km_peext=ref[0],
                 Qmax=round(q[iq]), Qmax_peext=ref[1], dQ_pct=round(100 * (q[iq] / ref[1] - 1), 1),
                 Nmax=round(w[iw], 2), Nmax_peext=ref[2], dN_m=round(w[iw] - ref[2], 2),
                 tQmax=round(tt[iq] - t0, 2), tNmax=round(tt[iw] - t0, 2), tNmax_peext=ref[3],
                 chegada=round(tt[ich] - t0, 2) if ich is not None else None, chegada_peext=ref[4])
        r["dCheg_pct"] = round(100 * (r["chegada"] / ref[4] - 1), 1) if r["chegada"] is not None and ref[4] else None
        r["ok_N"] = abs(r["dN_m"]) <= 3
        r["ok_Q"] = abs(r["dQ_pct"]) <= 25
        r["ok_cheg"] = r["dCheg_pct"] is not None and abs(r["dCheg_pct"]) <= 30
        linhas.append(r)
    linhas.sort(key=lambda r: r["km_peext"])
    out = os.path.join(base, "comparacao_peext.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w_ = csv.DictWriter(f, fieldnames=list(linhas[0].keys())); w_.writeheader(); w_.writerows(linhas)
    print(f"\n{plano.upper()} vs PEExt (t0 = {t0} h)   critério até Alcoutim: N ±3 m | Q ±25 % | chegada ±30 %\n")
    print(f"{'linha':<16}{'km':>6}{'Qmax':>9}{'PEExt':>8}{'dQ%':>7}{'Nmax':>8}{'PEExt':>8}{'dN':>7}"
          f"{'tNmax':>7}{'PEExt':>7}{'cheg':>7}{'PEExt':>7}{'dC%':>7}  ok(N,Q,C)")
    for r in linhas:
        crit = r["km_peext"] <= 122.7
        ok = "".join("✓" if r[k] else "✗" for k in ("ok_N", "ok_Q", "ok_cheg")) if crit else "(fora)"
        print(f"{r['linha']:<16}{r['km_peext']:>6.1f}{r['Qmax']:>9}{r['Qmax_peext']:>8}{r['dQ_pct']:>7}"
              f"{r['Nmax']:>8}{r['Nmax_peext']:>8}{r['dN_m']:>7}{r['tNmax']:>7}{r['tNmax_peext']:>7}"
              f"{str(r['chegada']):>7}{r['chegada_peext']:>7}{str(r['dCheg_pct']):>7}  {ok}")
    crit = [r for r in linhas if r["km_peext"] <= 122.7]
    passa = all(r["ok_N"] and r["ok_Q"] and r["ok_cheg"] for r in crit)
    print(f"\nCumpre o critério em todas as linhas até Alcoutim: {'SIM' if passa else 'NÃO'}"
          f"  ({sum(r['ok_N'] and r['ok_Q'] and r['ok_cheg'] for r in crit)}/{len(crit)})")
    print("Gravado:", out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "p11", float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
