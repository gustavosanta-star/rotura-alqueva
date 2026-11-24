"""
01 - Estimativas preliminares (ordens de grandeza) para o cenario hipotetico
de rotura da barragem de Alqueva.

Nao substitui o modelo hidraulico: serve para (1) fixar a geometria da brecha
a introduzir no HEC-RAS, (2) ter um intervalo plausivel para o caudal de ponta
e (3) dimensionar a malha, o passo de tempo e a duracao da simulacao.

So usa a biblioteca padrao. Correr:  python 01_estimativas_preliminares.py
"""
import csv
import math
from pathlib import Path

G = 9.81

# --- Barragem e albufeira (ver docs/dados_base.md para as fontes) -----------
COTA_COROAMENTO = 154.0      # m
ALTURA_BARRAGEM = 96.0       # m acima da fundacao
NPA = 152.0                  # m
VOLUME_NPA = 4150e6          # m3
COMP_COROAMENTO = 458.0      # m

# --- Brecha do cenario oficial (PEI 2010, citado no PEExt de out. 2024) -----
BRECHA_BASE = 148.0          # m
BRECHA_ALTURA = 96.0         # m (rotura total)
BRECHA_Z = 1.979             # H:V de cada lado
BRECHA_TEMPO_MIN = 8.7       # min
Q_PONTA_OFICIAL = 166462.0   # m3/s na seccao da barragem
KM_BARRAGEM = 5.0            # a origem das distancias oficiais esta 5 km a montante

CSV_REF = Path(__file__).resolve().parent.parent / "data" / "referencia_peext.csv"


def geometria_brecha():
    cota_soleira = COTA_COROAMENTO - BRECHA_ALTURA
    largura_topo = BRECHA_BASE + 2 * BRECHA_Z * BRECHA_ALTURA
    largura_media = BRECHA_BASE + BRECHA_Z * BRECHA_ALTURA
    return cota_soleira, largura_topo, largura_media


def q_ritter(h0, largura):
    """Rotura instantanea, canal retangular, leito seco (limite superior)."""
    return (8.0 / 27.0) * math.sqrt(G) * h0 ** 1.5 * largura


def q_froehlich_1995(volume, hw):
    """Regressao empirica (barragens de aterro) - so como ordem de grandeza."""
    return 0.607 * volume ** 0.295 * hw ** 1.24


def main():
    cota_soleira, largura_topo, largura_media = geometria_brecha()
    hw = NPA - cota_soleira

    print("== Brecha (cenario oficial) ==")
    print(f"Cota da soleira da brecha : {cota_soleira:.1f} m")
    print(f"Largura na base / media / topo : {BRECHA_BASE:.0f} / {largura_media:.0f} / {largura_topo:.0f} m")
    print(f"(coroamento tem {COMP_COROAMENTO:.0f} m -> a brecha toma toda a abobada)")
    print(f"Tempo de formacao : {BRECHA_TEMPO_MIN} min = {BRECHA_TEMPO_MIN / 60:.3f} h")
    print(f"Carga sobre a soleira com a albufeira no NPA : {hw:.0f} m")

    print("\n== Caudal de ponta: intervalo plausivel ==")
    q_r = q_ritter(hw, largura_media)
    q_f = q_froehlich_1995(VOLUME_NPA, hw)
    print(f"Froehlich (1995), empirico      : {q_f:>10,.0f} m3/s")
    print(f"Estudo oficial (PEI 2010)       : {Q_PONTA_OFICIAL:>10,.0f} m3/s")
    print(f"Ritter, rotura instantanea      : {q_r:>10,.0f} m3/s")
    print("-> um modelo 2D bem montado deve dar um pico dentro deste intervalo.")

    print("\n== Duracao da simulacao ==")
    t_min = VOLUME_NPA / Q_PONTA_OFICIAL / 3600
    print(f"Volume / caudal de ponta = {t_min:.1f} h (minimo teorico para esvaziar)")
    print("O hidrograma real tem cauda longa -> simular 48 a 72 h.")

    print("\n== Velocidade da frente de onda (tabela oficial) ==")
    with open(CSV_REF, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    print(f"{'Local':<32}{'km da barragem':>15}{'chegada (h)':>13}{'media (km/h)':>14}")
    for r in linhas:
        if not r["t_chegada_h"]:
            continue
        d = float(r["km_origem"]) - KM_BARRAGEM
        t = float(r["t_chegada_h"])
        if d <= 0:
            continue
        v = d / t
        print(f"{r['local']:<32}{d:>15.1f}{t:>13.2f}{v:>14.1f}")

    print("\n== Malha e passo de tempo (HEC-RAS 2D, equacoes completas) ==")
    v_ref = max(float(r["vmax_ms"]) for r in linhas)   # velocidade maxima do escoamento
    for dx in (25, 50, 100):
        dt = dx / v_ref                                 # Courant ~ 1
        print(f"celula {dx:>3} m -> passo de tempo <= {dt:4.1f} s  (V max = {v_ref} m/s)")
    print("Sugestao: malha base 100 m, refinada a 25-50 m no leito e nas povoacoes;")
    print("passo de tempo adaptativo (Courant) com maximo de 5 s.")


if __name__ == "__main__":
    main()
