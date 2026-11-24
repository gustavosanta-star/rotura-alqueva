"""Gera g05, g06, u04, p11, p12 e o .prj atualizado a partir dos ficheiros atuais do PC (g04, u03, p10, prj)."""
import json, re
H = '/mnt/user-data/uploads/rotura-alqueva/hecras/rotura_alqueva.'
O = '/home/claude/kit/ras/rotura_alqueva.'
import os; os.makedirs('/home/claude/kit/ras', exist_ok=True)
rd = lambda ext: open(H + ext, encoding='latin-1', newline='').read().split('\r\n')
def wr(ext, L):
    with open(O + ext, 'w', encoding='latin-1', newline='') as f: f.write('\r\n'.join(L))
LN = json.load(open('linhas_novas.json'))

def ref_block(nome, A, B):
    mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    f = lambda v: f'{v:16.4f}'.replace(' ', ' ')
    return [f'Reference Line Name={nome:<32}',
            'Reference Line Storage Area=Perimeter 1     ',
            f'Reference Line Start Position= {A[0]:.4f} , {A[1]:.4f} ',
            f'Reference Line Middle Position= {mx:.4f} , {my:.4f} ',
            f'Reference Line End Position= {B[0]:.4f} , {B[1]:.4f} ',
            'Reference Line Arc= 2 ',
            f'{A[0]:16.4f}{A[1]:16.4f}{B[0]:16.4f}{B[1]:16.4f}',
            f'Reference Line Text Position= {mx:.4f} , {my:.4f} ']

def geom(titulo):
    L = rd('g04')
    assert L[0].startswith('Geom Title=G04_cos')
    L[0] = 'Geom Title=' + titulo
    # substituir o bloco da P09
    i = next(k for k, l in enumerate(L) if l.startswith('Reference Line Name=P09_Pedrogao'))
    j = next(k for k in range(i + 1, len(L)) if L[k].startswith('Reference Line Text Position'))
    v = LN['P09_Pedrogao_jus']
    L[i:j + 1] = ref_block('P09_Pedrogao', v['A'], v['B'])
    # linhas novas a seguir à última linha de referência
    last = max(k for k, l in enumerate(L) if l.startswith('Reference Line Text Position'))
    novas = []
    for n in ['P14', 'P20', 'P24', 'P28', 'P43', 'P52']:
        novas += ref_block(n, LN[n]['A'], LN[n]['B'])
    L[last + 1:last + 1] = novas
    return L

wr('g05', geom('G05_batim'))
wr('g06', geom('G06_batim_vale'))

# U04 = U03 + nível de 2,0 m na foz (49 valores horários = 48 h) + IC Foz_estuario a 2,0
U = rd('u03')
U[0] = 'Flow Title=U04_foz_2m'
U = [re.sub(r'^(IC Point Elev=Foz_estuario\s*,)0\.5,', r'\g<1>2,', l) for l in U]
assert any(l.startswith('IC Point Elev=Foz_estuario') and ',2,' in l for l in U)
k = next(i for i, l in enumerate(U) if l.startswith('Boundary Location=') and 'Foz_Guadiana' in l)
assert U[k + 1].startswith('Friction Slope=')
n = 49; vals = ['       2'] * n
data = [''.join(vals[i:i + 10]) for i in range(0, n, 10)]
U[k + 1:k + 2] = ['Interval=1HOUR', f'Stage Hydrograph= {n} '] + data + [
    'DSS Path=', 'Use DSS=False', 'Use Fixed Start Time=False', 'Fixed Start Date/Time=,',
    'Is Critical Boundary=False', 'Critical Boundary Flow=']
wr('u04', U)

# planos
for ext, tit, sid, g in [('p11', 'P11_batim', 'p11batim', 'g05'), ('p12', 'P12_batim_vale', 'p12vale', 'g06')]:
    P = rd('p10')
    P[0] = 'Plan Title=' + tit
    P[2] = f'Short Identifier={sid:<64}'
    assert P[4] == 'Geom File=g04' and P[5] == 'Flow File=u03'
    P[4] = 'Geom File=' + g; P[5] = 'Flow File=u04'
    wr(ext, P)

# .prj
J = rd('prj')
def add(prefix, novos):
    last = max(i for i, l in enumerate(J) if l.startswith(prefix))
    for n_ in reversed(novos): J.insert(last + 1, prefix + n_)
add('Geom File=', ['g05', 'g06']); add('Unsteady File=', ['u04']); add('Plan File=', ['p11', 'p12'])
J = [('Current Plan=p11' if l.startswith('Current Plan=') else l) for l in J]
wr('prj', J)
print('ok')
