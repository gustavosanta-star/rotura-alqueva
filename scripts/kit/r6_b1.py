"""Cenário completo B1 (à maneira do PEExt) a partir do modelo congelado G06/P12.
U05: aquecimento 0–6 h com 5 000 m³/s na linha Entrada_PEExt (enche Pedrógão de 84,8 a ~93 m: ΔV ≈ 105 hm³);
     depois 0. Foz com nível imposto de 2,0 m. IC iguais ao U04 (Albufeira 154; Pedrógão 84,8; jusante 60,5; foz 2,0).
P13: G06 + U05; 01JAN2026 01:00 → 03JAN2026 09:00 (56 h). Rotura de Alqueva às 09:00 (fim do aquecimento + 2 h
     de estabilização); Pedrógão rompe quando o nível na barragem chega a 94 m (1 m acima do coroamento).
     Mapas de 10 em 10 min; hidrogramas de 1 em 1 min."""
import re
H = '/mnt/user-data/uploads/rotura-alqueva/hecras/rotura_alqueva.'
O = '/home/claude/kit/b1/rotura_alqueva.'
rd = lambda ext: open(H + ext, encoding='latin-1', newline='').read().split('\r\n')
def wr(ext, L):
    with open(O + ext, 'w', encoding='latin-1', newline='') as f: f.write('\r\n'.join(L))
def bloco(vals):
    s = [f'{v:8g}' if len(f'{v:g}') <= 8 else f'{v:8.1f}' for v in vals]
    return [''.join(s[i:i + 10]) for i in range(0, len(s), 10)]

# ---------- U05
U = rd('u04')
U[0] = 'Flow Title=U05_B1_completo'
i = next(k for k, l in enumerate(U) if l.startswith('Boundary Location=') and 'Entrada_PEExt' in l)
assert U[i + 1] == 'Interval=1MIN' and U[i + 2].startswith('Flow Hydrograph=')
n_old = int(U[i + 2].split('=')[1]); nl = -(-n_old // 10)
n = 56 * 6 + 1                      # 10 em 10 min durante 56 h
q = [0.0] + [5000.0] * 35 + [0.0] * (n - 36)   # 0 em t=0; 5000 de 0:10 a 5:50; 0 a partir das 6:00
vol = sum((q[k] + q[k + 1]) / 2 * 600 for k in range(n - 1)) / 1e6
U[i + 1:i + 3 + nl] = ['Interval=10MIN', f'Flow Hydrograph= {n} '] + bloco(q)
k = next(j for j, l in enumerate(U) if l.startswith('Boundary Location=') and 'Foz_Guadiana' in l)
assert U[k + 1] == 'Interval=1HOUR' and U[k + 2].startswith('Stage Hydrograph=')
ns_old = int(U[k + 2].split('=')[1]); nls = -(-ns_old // 10)
ns = 58
U[k + 2:k + 3 + nls] = [f'Stage Hydrograph= {ns} '] + [''.join(['       2'] * 10)[:8 * min(10, ns - j)] for j in range(0, ns, 10)]
wr('u05', U)
print('U05: volume de aquecimento', round(vol, 1), 'hm3')

# ---------- P13
P = rd('p12')
P[0] = 'Plan Title=P13_B1_completo'
P[2] = f'Short Identifier={"p13b1":<64}'
P[3] = 'Simulation Date=01JAN2026,0100,03JAN2026,0900'
assert P[4] == 'Geom File=g06' and P[5] == 'Flow File=u04'
P[5] = 'Flow File=u05'
P = ['Mapping Interval=10MIN' if l.startswith('Mapping Interval=') else l for l in P]
ia = next(j for j, l in enumerate(P) if l.startswith('Breach Loc=') and 'Barragem_Alqueva' in l)
P[ia] = P[ia].replace(',False,Barragem_Alqueva', ',True,Barragem_Alqueva')
assert P[ia + 3].startswith('Breach Start=')
P[ia + 3] = 'Breach Start=False,,01JAN2026,0900,False,,,0'
ip = next(j for j, l in enumerate(P) if l.startswith('Breach Loc=') and 'Pedrogao' in l)
assert ',True,Pedrogao' in P[ip] and P[ip + 3].startswith('Breach Start=')
P[ip + 3] = 'Breach Start=True,94,,,False,,,0'
wr('p13', P)

# ---------- prj
J = rd('prj')
def add(prefix, novos):
    last = max(j for j, l in enumerate(J) if l.startswith(prefix))
    for x in reversed(novos): J.insert(last + 1, prefix + x)
add('Unsteady File=', ['u05']); add('Plan File=', ['p13'])
J = [('Current Plan=p13' if l.startswith('Current Plan=') else l) for l in J]
wr('prj', J)
print('ok')
