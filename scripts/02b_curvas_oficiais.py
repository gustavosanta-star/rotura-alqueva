"""
02b - Curvas cota-volume-area de Alqueva e Pedrogao a partir dos ajustes aos
dados do SNIRH publicados numa tese do IST (ver docs/dados_base.md).

Para a albufeira de Alqueva entrar no HEC-RAS como Storage Area. Dispensa o
SRTM ACIMA da cota 125 m. Abaixo de 125 m (o ajuste nao e valido e o volume
e de ~820 hm3, 20 % do total) a curva e EXTRAPOLADA com uma lei de potencia
que mantem o volume e a area a 125 m; e a parte a substituir pela curva do
SRTM (script 02) quando houver.

So biblioteca padrao.  python 02b_curvas_oficiais.py
"""
import csv
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "data"

# V em hm3, z em m (ajustes SNIRH); area A(V) em km2 com V em hm3 (ajuste SNIRH)
# O HEC-RAS so precisa da relacao cota-volume. A area e informativa: o ajuste
# cota-volume e o ajuste area-volume nao sao coerentes no fundo do intervalo,
# por isso a area vem de A(V) e fica em branco na parte extrapolada.
ALQ = dict(a=3.8228, b=-933.72, c=57805.0, z_min=125.0, z_max=155.0,
           z_fundo=58.0, z_ate=154.0, nome="alqueva",
           area=lambda v: -4e-7 * v * v + 0.0567 * v + 14.48)
PED = dict(a=0.3734, b=-51.766, c=1810.0, z_min=76.0, z_max=86.0,
           z_fundo=50.0, z_ate=93.0, nome="pedrogao",
           area=lambda v: -0.0004 * v * v + 0.1109 * v + 3.5029)


def quad(p, z):
    return p["a"] * z * z + p["b"] * z + p["c"]


def dquad(p, z):
    return 2 * p["a"] * z + p["b"]


def curva(p):
    z0, zf = p["z_min"], p["z_fundo"]
    v0, a0 = quad(p, z0), dquad(p, z0)
    k = a0 * (z0 - zf) / v0              # expoente que conserva V e dV/dz em z0
    linhas = []
    z = zf
    while z <= p["z_ate"] + 1e-9:
        if z >= z0:
            v = quad(p, z)
            a = p["area"](v) if z <= p["z_max"] else None
            origem = "ajuste SNIRH" if z <= p["z_max"] else "ajuste SNIRH extrapolado"
        else:
            v = v0 * ((z - zf) / (z0 - zf)) ** k
            a = None
            origem = "extrapolado (lei de potencia) - substituir por SRTM"
        linhas.append((z, a, max(v, 0.0), origem))
        z += 1.0
    return linhas, k


def main():
    PASTA.mkdir(exist_ok=True)
    for p in (ALQ, PED):
        linhas, k = curva(p)
        saida = PASTA / f"curva_cota_volume_{p['nome']}.csv"
        with open(saida, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["cota_m", "area_km2", "volume_hm3", "origem"])
            for z, a, v, o in linhas:
                w.writerow([f"{z:.0f}", "" if a is None else f"{a:.1f}", f"{v:.1f}", o])
        print(f"{p['nome']}: expoente abaixo de {p['z_min']:.0f} m = {k:.2f} -> {saida.name}")
        marcos = {p["z_min"], p["z_ate"], 152.0 if p is ALQ else 85.0, 100.0 if p is ALQ else 70.0}
        for z, a, v, o in linhas:
            if z in marcos:
                ta = "   -  " if a is None else f"{a:6.1f}"
                print(f"   {z:6.1f} m  {v:8.1f} hm3  {ta} km2  ({o})")


if __name__ == "__main__":
    main()
