# -*- coding: utf-8 -*-
"""
21_video_b1.py (v2) - vídeo da rotura hipotética de Alqueva (cenário B1) gerado por código, sem o ArcGIS Pro.

Entradas (scripts 16 e 20, pasta resultados\\p13\\cena3d):
  frames_2min\\prof_tMMMM.tif (usa os de 10 em 10 min = registos do HEC-RAS e interpola entre eles)
  cid_30m.tif, terreno_cena_20m.tif
  scripts\\kit_p11\\eixo.npy (eixo do Guadiana: x, y, km desde a barragem)
Layout: layout_video.json (posições, tamanhos, cores, textos, durações). Se não existir, usa o LAYOUT abaixo
        e grava-o, para poderes editar.

Uso:
  python 21_video_b1.py <pasta cena3d> <eixo.npy> <saida.mp4> [--layout layout_video.json] [--camadas <pasta>]
  --camadas: em vez do vídeo final, grava um pacote para editor de vídeo:
      mapa.mp4 (mapa animado, sem painéis), relogio.mov, enquadramento.mov, barra_tempo.mov, escala.mov
      (ProRes 4444 com transparência) e titulo.png, legenda.png, rodape.png, balanco_final.png.
Precisa de: numpy, scipy, Pillow, tifffile e ffmpeg.
"""
import os, sys, json, math, subprocess, time, copy
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree
from scipy import ndimage
import tifffile

LAYOUT = {
    "video": {"largura": 1920, "altura": 1080, "fps": 30,
              "intro_s": 3.0, "segue_s": 44.0, "fim_s": 7.0, "hold_s": 5.0, "fade_s": 0.8,
              "horas_segue": 12.0, "largura_vista_km": 30.0, "km_a_frente": 2.0},
    "cores": {"fundo": "#E4E1DA", "relevo_baixo": "#F1EEE6", "relevo_alto": "#D6CAB0", "limite_modelo": "#7A7A7A",
              "profundidade": ["#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#084594"],
              "agua_alpha": 235, "painel": "#FFFFFF", "painel_alpha": 220, "texto": "#141414",
              "texto_2": "#505050", "destaque": "#D7301F"},
    "profundidade": {"limites": [0.05, 0.5, 1, 2, 5, 10, 20],
                     "rotulos": ["< 0,5", "0,5 – 1", "1 – 2", "2 – 5", "5 – 10", "10 – 20", "> 20"]},
    "fonte": {"normal": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "negrito": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"},
    "titulo": {"mostrar": True, "x": 30, "y": 26, "texto": "Rotura hipotética da barragem de Alqueva",
               "subtitulo": "Cenário B1 · profundidade da água · modelo HEC-RAS 2D", "tamanho": 40, "tamanho_sub": 24},
    "relogio": {"mostrar": True, "x": 30, "y": 146, "rotulo": "tempo desde a rotura", "tamanho": 64},
    "legenda": {"mostrar": True, "x": 30, "y": -330, "titulo": "Profundidade (m)", "texto_limite": "limite do modelo"},
    "enquadramento": {"mostrar": True, "x": -40, "y": 150, "altura": 820, "titulo": "Vale do Guadiana"},
    "barra_tempo": {"mostrar": True, "x": 310, "y": -110, "largura": 1000, "titulo": "horas desde a rotura"},
    "escala": {"mostrar": True, "x": 310, "y": -40},
    "rodape": {"mostrar": True, "x": -40, "y": -14,
               "texto": "Cenário hipotético para estudo · terreno: SRTM, MDT DGT/CNIG · ETRS89/UTM 29N", "tamanho": 17},
    "localidades": {"mostrar": True, "tamanho": 24,
                    "lista": [["Barragem de Alqueva", 38.1975, -7.4964, 1], ["Pedrógão", 38.1185, -7.6455, 1],
                              ["Pulo do Lobo", 37.8030, -7.6330, 2], ["Mértola", 37.6390, -7.6610, 1],
                              ["Pomarão", 37.5560, -7.5250, 2], ["Alcoutim", 37.4710, -7.4710, 1],
                              ["Sanlúcar de Guadiana", 37.4730, -7.4650, 2], ["Castro Marim", 37.2180, -7.4430, 1],
                              ["Ayamonte", 37.2130, -7.4070, 1], ["Vila Real de Santo António", 37.1940, -7.4160, 1],
                              ["Monte Gordo", 37.1800, -7.4500, 2]]},
    "chegadas": {"Pedrógão": 0.7, "Mértola": 4.3, "Alcoutim": 7.2, "Vila Real de Santo António": 11.5},
    "chegadas_curto": {"Pedrógão": "Pedrógão", "Mértola": "Mértola", "Alcoutim": "Alcoutim",
                       "Vila Real de Santo António": "VRSA"},
    "balanco_final": {"mostrar": True, "x": 30, "y": 280, "titulo": "Profundidade máxima nas 24 h",
                      "linhas": ["área inundada pela onda: 22 631 ha",
                                 "residentes em zona inundada: ~28 800 (PT + ES)"]},
}

REGISTOS = list(range(0, 1441, 10))


# ------------------------------------------------------------------ utilitários
def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def utm29(lat, lon):
    a = 6378137.0; f = 1 / 298.257222101; e2 = f * (2 - f); ep2 = e2 / (1 - e2); k0 = 0.9996
    e4, e6 = e2 * e2, e2 ** 3
    phi, lam = math.radians(lat), math.radians(lon); lam0 = math.radians(-9.0)
    M = a * ((1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
             + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi) - (35 * e6 / 3072) * math.sin(6 * phi))
    N = a / math.sqrt(1 - e2 * math.sin(phi) ** 2); T = math.tan(phi) ** 2; C = ep2 * math.cos(phi) ** 2
    A = (lam - lam0) * math.cos(phi)
    x = 500000 + k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120)
    y = k0 * (M + N * math.tan(phi) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24))
    return x, y


def ler_tif(p):
    with tifffile.TiffFile(p) as t:
        pg = t.pages[0]
        try:
            a = pg.asarray().astype(np.float32)
        except Exception:                       # LZW sem imagecodecs -> Pillow
            a = np.array(Image.open(p)).astype(np.float32)
        sx, sy = pg.tags["ModelPixelScaleTag"].value[:2]
        tp = pg.tags["ModelTiepointTag"].value
        nod = pg.tags["GDAL_NODATA"].value if "GDAL_NODATA" in pg.tags else None
    if nod not in (None, ""):
        a[a == float(str(nod).strip("\x00"))] = np.nan
    a[a > 1e30] = np.nan
    return a, tp[3] - tp[0] * sx, tp[4] + tp[1] * sy, sx


def suave(v, n):
    if n < 2: return v
    p = np.pad(v, (n // 2, n - 1 - n // 2), mode="edge")
    return np.convolve(p, np.ones(n) / n, mode="valid")


def mesclar(base, novo):
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            mesclar(base[k], v)
        else:
            base[k] = v
    return base


# ------------------------------------------------------------------ principal
def main(pasta, eixo_p, saida, layout_p=None, camadas=None):
    t0 = time.time()
    log = lambda m: print("[%6.1f s] %s" % (time.time() - t0, m), flush=True)
    L = copy.deepcopy(LAYOUT)
    if layout_p:
        if os.path.exists(layout_p):
            with open(layout_p, encoding="utf-8") as f:
                mesclar(L, json.load(f))
            log("layout lido de %s" % layout_p)
        else:
            with open(layout_p, "w", encoding="utf-8") as f:
                json.dump(LAYOUT, f, ensure_ascii=False, indent=2)
            log("layout por defeito gravado em %s" % layout_p)
    V, C = L["video"], L["cores"]
    W, H, FPS = V["largura"], V["altura"], V["fps"]
    LIM = L["profundidade"]["limites"]
    COR_FUNDO = hexrgb(C["fundo"])

    # ---------------- grelha do modelo (30 m) e profundidades
    cid, gx0, gy0, c30 = ler_tif(os.path.join(pasta, "cid_30m.tif"))
    NR, NC = cid.shape
    valido = np.isfinite(cid) & (cid >= 0)
    idx = np.flatnonzero(valido.ravel())
    pilha = np.empty((len(REGISTOS), idx.size), np.float16)
    for k, m in enumerate(REGISTOS):
        a, _, _, _ = ler_tif(os.path.join(pasta, "frames_2min", "prof_t%04d.tif" % m))
        pilha[k] = a.ravel()[idx]
    log("%d imagens de profundidade lidas" % len(REGISTOS))

    # ---------------- frente da onda
    e = np.load(eixo_p)
    r_, c_ = np.divmod(idx, NC)
    dist, j = cKDTree(e[:, :2]).query(np.c_[gx0 + (c_ + 0.5) * c30, gy0 - (r_ + 0.5) * c30])
    kmc = e[j, 2]
    d0 = np.nan_to_num(pilha[0].astype(np.float32), nan=0)
    frente = []
    for k in range(len(REGISTOS)):
        m = ((np.nan_to_num(pilha[k].astype(np.float32), nan=0) - d0) >= 1.0) & (dist < 8000)
        frente.append(np.percentile(kmc[m], 98) if m.sum() > 50 else 0.0)
    frente = np.maximum.accumulate(np.array(frente))
    km_max = e[-1, 2]

    def eixo_xy(km):
        km = float(np.clip(km, 0, km_max))
        return np.interp(km, e[:, 2], e[:, 0]), np.interp(km, e[:, 2], e[:, 1])

    # ---------------- base a 20 m: relevo sombreado + tinta hipsométrica + limite do modelo
    T, tx0, ty0, c20 = ler_tif(os.path.join(pasta, "terreno_cena_20m.tif"))
    TR, TC = T.shape
    Tz = np.nan_to_num(T, nan=0.0)
    gy, gx = np.gradient(Tz * 3.0, c20)
    az, alt = math.radians(315), math.radians(45)
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    sh = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)
    lo, hi = np.array(hexrgb(C["relevo_baixo"]), np.float32), np.array(hexrgb(C["relevo_alto"]), np.float32)
    tt = np.clip(Tz / 350.0, 0, 1)[..., None]
    base = (lo * (1 - tt) + hi * tt) * (0.50 + 0.50 * sh[..., None])
    base[np.isnan(T)] = COR_FUNDO
    del gx, gy, slope, aspect, sh, tt
    # limite do modelo no grid de 20 m
    rr = ((gy0 - (ty0 - (np.arange(TR) + 0.5) * c20)) / c30).astype(int)
    cc = (((tx0 + (np.arange(TC) + 0.5) * c20) - gx0) / c30).astype(int)
    okr, okc = (rr >= 0) & (rr < NR), (cc >= 0) & (cc < NC)
    v20 = np.zeros((TR, TC), bool)
    v20[np.ix_(okr, okc)] = valido[np.ix_(rr[okr], cc[okc])]
    borda = v20 ^ ndimage.binary_erosion(v20, iterations=1)
    borda = ndimage.binary_dilation(borda, iterations=1)
    base[borda] = hexrgb(C["limite_modelo"])
    BASE = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    del base, Tz, v20, borda
    log("base de relevo pronta (%dx%d a %d m)" % (TC, TR, c20))

    lut = np.zeros((len(LIM) + 1, 4), np.uint8)
    for i, c in enumerate(C["profundidade"]):
        lut[i + 1] = hexrgb(c) + (C["agua_alpha"],)

    pmax = np.nanmax(np.where(np.isnan(pilha), -1, pilha).astype(np.float32), axis=0)
    GMAX = np.full(NR * NC, -1.0, np.float32); GMAX[idx] = pmax; GMAX = GMAX.reshape(NR, NC)

    cache = {}
    def prof(minutos):
        minutos = float(np.clip(minutos, 0, REGISTOS[-1]))
        k = min(int(minutos // 10), len(REGISTOS) - 2); f = (minutos - REGISTOS[k]) / 10.0
        for kk in (k, k + 1):
            if kk not in cache:
                if len(cache) > 3: cache.pop(min(cache))
                g = np.full(NR * NC, -1.0, np.float32)
                g[idx] = np.nan_to_num(pilha[kk].astype(np.float32), nan=-1.0)
                cache[kk] = g.reshape(NR, NC)
        return cache[k] * (1 - f) + cache[k + 1] * f

    def caixa(xmin, ymin, xmax, ymax, x0, y0, c):
        return ((xmin - x0) / c, (y0 - ymax) / c, (xmax - x0) / c, (y0 - ymin) / c)

    # ---------------- guião: tempo simulado, centro e largura da vista
    n_i, n_s, n_f, n_h = [int(round(V[k] * FPS)) for k in ("intro_s", "segue_s", "fim_s", "hold_s")]
    N = n_i + n_s + n_f + n_h
    HS = V["horas_segue"]
    sim = np.zeros(N)
    for i in range(N):
        if i < n_i:
            sim[i] = 0.0
        elif i < n_i + n_s:
            sim[i] = 60 * HS * ((i - n_i) / (n_s - 1)) ** 1.25
        elif i < n_i + n_s + n_f:
            u = (i - n_i - n_s) / (n_f - 1)
            sim[i] = 60 * (HS + (24 - HS) * (0.5 - 0.5 * math.cos(math.pi * u)))
        else:
            sim[i] = 1440.0
    alvo = np.interp(sim, REGISTOS, frente) + V["km_a_frente"]
    cx = np.array([eixo_xy(k)[0] for k in alvo]); cy = np.array([eixo_xy(k)[1] for k in alvo])
    larg = np.full(N, V["largura_vista_km"] * 1000.0)
    xb, yb = eixo_xy(0); xa, ya = xb - 4000, yb + 9000
    for i in range(min(N, n_i + int(3 * FPS))):
        w_ = 1.0 if i < n_i else 0.5 + 0.5 * math.cos(math.pi * (i - n_i) / (3 * FPS))
        cx[i] = xa * w_ + cx[i] * (1 - w_); cy[i] = ya * w_ + cy[i] * (1 - w_)
        larg[i] = 42000 * w_ + larg[i] * (1 - w_)
    cx = suave(cx, FPS); cy = suave(cy, FPS)
    y_min = gy0 - NR * c30
    for i in range(N):
        cy[i] = max(cy[i], y_min + larg[i] * H / W / 2 - 1500)
    xg, yg = gx0 + NC * c30 / 2, gy0 - NR * c30 / 2
    lg = NR * c30 * W / H * 1.02
    for i in range(n_i + n_s, N):
        u = min(1.0, (i - n_i - n_s) / (n_f - 1)); u = 0.5 - 0.5 * math.cos(math.pi * u)
        cx[i] = cx[i] * (1 - u) + xg * u; cy[i] = cy[i] * (1 - u) + yg * u
        larg[i] = math.exp(math.log(larg[i]) * (1 - u) + math.log(lg) * u)
    larg = suave(larg, FPS // 2)

    # ---------------- fontes e elementos gráficos
    FN, FB = L["fonte"]["normal"], L["fonte"]["negrito"]
    fnt = lambda s, b=False: ImageFont.truetype(FB if b else FN, int(s))
    TXT, TXT2, DEST = hexrgb(C["texto"]), hexrgb(C["texto_2"]), hexrgb(C["destaque"])
    PAINEL = hexrgb(C["painel"]) + (C["painel_alpha"],)

    def painel(img, box):
        ImageDraw.Draw(img).rounded_rectangle(box, 12, fill=PAINEL, outline=(0, 0, 0, 40), width=1)

    def pos(cfg, w, h):     # x/y negativos contam a partir da direita/baixo
        x = cfg["x"] if cfg["x"] >= 0 else W + cfg["x"] - w
        y = cfg["y"] if cfg["y"] >= 0 else H + cfg["y"] - h
        return int(x), int(y)

    # tamanhos dos elementos
    OV_H = L["enquadramento"]["altura"]; esc_ov = OV_H / TR; OV_W = int(TC * esc_ov)
    ov_base = BASE.resize((OV_W, OV_H), Image.LANCZOS)
    S_TIT = (int(fnt(L["titulo"]["tamanho"], True).getlength(L["titulo"]["texto"])) + 50,
             int(L["titulo"]["tamanho"] * 1.3 + L["titulo"]["tamanho_sub"] * 1.5 + 28))
    S_REL = (int(fnt(L["relogio"]["tamanho"], True).getlength("00 h 00 min")) + 46, int(L["relogio"]["tamanho"] * 1.25 + 46))
    S_LEG = (int(fnt(24, True).getlength(L["legenda"]["titulo"])) + 44, 300)
    S_OV = (OV_W + 28, OV_H + 66)
    BT_W = L["barra_tempo"]["largura"]; S_BT = (BT_W + 40, 92)
    S_ESC = (380, 44)
    S_BAL = (max(int(fnt(22).getlength(t)) for t in L["balanco_final"]["linhas"] + [L["balanco_final"]["titulo"]]) + 50,
             50 + 32 * len(L["balanco_final"]["linhas"]))
    F_ROD = fnt(L["rodape"]["tamanho"])
    S_ROD = (int(F_ROD.getlength(L["rodape"]["texto"])) + 12, int(L["rodape"]["tamanho"] * 1.6))

    def el_titulo(img, x, y):
        c = L["titulo"]; painel(img, (x, y, x + S_TIT[0], y + S_TIT[1]))
        d = ImageDraw.Draw(img)
        d.text((x + 22, y + 12), c["texto"], font=fnt(c["tamanho"], True), fill=TXT)
        d.text((x + 24, y + 18 + c["tamanho"] * 1.25), c["subtitulo"], font=fnt(c["tamanho_sub"]), fill=TXT2)

    def el_relogio(img, x, y, m):
        c = L["relogio"]; painel(img, (x, y, x + S_REL[0], y + S_REL[1]))
        d = ImageDraw.Draw(img)
        d.text((x + 22, y + 8), c["rotulo"], font=fnt(18), fill=TXT2)
        hh, mm = int(m // 60), int(round(m % 60))
        if mm == 60: hh, mm = hh + 1, 0
        d.text((x + 22, y + 32), "%02d h %02d min" % (hh, mm), font=fnt(c["tamanho"], True), fill=TXT)

    def el_legenda(img, x, y):
        c = L["legenda"]; painel(img, (x, y, x + S_LEG[0], y + S_LEG[1]))
        d = ImageDraw.Draw(img)
        d.text((x + 20, y + 14), c["titulo"], font=fnt(24, True), fill=TXT)
        for q, (cor, rt) in enumerate(zip(C["profundidade"], L["profundidade"]["rotulos"])):
            yy = y + 52 + q * 31
            d.rectangle((x + 20, yy, x + 58, yy + 22), fill=hexrgb(cor), outline=(120, 120, 120))
            d.text((x + 72, yy + 1), rt, font=fnt(22), fill=TXT)
        d.line((x + 20, y + 282, x + 58, y + 282), fill=hexrgb(C["limite_modelo"]), width=3)
        d.text((x + 72, y + 272), c["texto_limite"], font=fnt(18), fill=TXT2)

    def el_enquadramento(img, x, y, pm, box20, m):
        painel(img, (x, y, x + S_OV[0], y + S_OV[1]))
        d = ImageDraw.Draw(img)
        d.text((x + S_OV[0] / 2, y + 26), L["enquadramento"]["titulo"], font=fnt(18), fill=TXT, anchor="mm")
        ox, oy = x + 14, y + 50
        # profundidade (grid 30 m) reamostrada para a área da base (grid 20 m)
        b30 = caixa(tx0, ty0 - TR * c20, tx0 + TC * c20, ty0, gx0, gy0, c30)
        ovp = np.asarray(Image.fromarray(pm, "F").transform((OV_W, OV_H), Image.EXTENT, b30, Image.BILINEAR, fillcolor=-1.0))
        ov = ov_base.convert("RGBA"); ov.alpha_composite(Image.fromarray(lut[np.digitize(ovp, LIM)], "RGBA"))
        img.alpha_composite(ov, (ox, oy))
        d = ImageDraw.Draw(img)
        bx = [v * esc_ov for v in box20]
        d.rectangle((max(ox + bx[0], ox), max(oy + bx[1], oy), min(ox + bx[2], ox + OV_W), min(oy + bx[3], oy + OV_H)),
                    outline=DEST, width=2)
        if m > 0:
            fx, fy = eixo_xy(np.interp(m, REGISTOS, frente))
            px_, py_ = ox + (fx - tx0) / c20 * esc_ov, oy + (ty0 - fy) / c20 * esc_ov
            d.ellipse((px_ - 6, py_ - 6, px_ + 6, py_ + 6), fill=DEST, outline="white", width=2)

    def el_barra(img, x, y, m):
        c = L["barra_tempo"]; painel(img, (x, y, x + S_BT[0], y + S_BT[1]))
        d = ImageDraw.Draw(img)
        x0, x1, yb_ = x + 20, x + 20 + BT_W, y + 58
        d.text((x1, y + 6), c["titulo"], font=fnt(16), fill=TXT2, anchor="ra")
        d.rounded_rectangle((x0, yb_ - 5, x1, yb_ + 5), 5, fill=(205, 205, 205))
        xc = x0 + (x1 - x0) * min(m, 1440) / 1440
        d.rounded_rectangle((x0, yb_ - 5, max(xc, x0 + 10), yb_ + 5), 5, fill=hexrgb(C["profundidade"][5]))
        for h in range(0, 25, 3):
            xx = x0 + (x1 - x0) * h / 24
            d.line((xx, yb_ + 7, xx, yb_ + 12), fill=TXT2, width=1)
            d.text((xx, yb_ + 14), "%d" % h, font=fnt(14), fill=TXT2, anchor="mt")
        for n, hc in L["chegadas"].items():
            xx = x0 + (x1 - x0) * hc / 24
            passou = m / 60 >= hc
            cor = DEST if passou else (150, 150, 150)
            d.polygon([(xx, yb_ - 7), (xx - 6, yb_ - 17), (xx + 6, yb_ - 17)], fill=cor)
            d.text((xx, yb_ - 20), L["chegadas_curto"].get(n, n), font=fnt(15, passou), fill=TXT if passou else TXT2, anchor="mb")
        d.ellipse((xc - 8, yb_ - 8, xc + 8, yb_ + 8), fill="white", outline=hexrgb(C["profundidade"][6]), width=3)

    def el_escala(img, x, y, k_px):
        km_bar = max(b for b in (1, 2, 5, 10, 20, 50) if b * 1000 * k_px <= 320)
        bar = km_bar * 1000 * k_px
        d = ImageDraw.Draw(img)
        d.rectangle((x + 4, y + 26, x + 4 + bar, y + 34), fill=(40, 40, 40))
        d.rectangle((x + 4, y + 26, x + 4 + bar / 2, y + 34), fill=(255, 255, 255), outline=(40, 40, 40))
        d.text((x + 4 + bar / 2, y + 20), "%d km" % km_bar, font=fnt(18), fill=TXT, anchor="mb",
               stroke_width=3, stroke_fill="white")

    def el_rodape(img, x, y):
        ImageDraw.Draw(img).text((x + 6, y + 2), L["rodape"]["texto"], font=F_ROD, fill=TXT2,
                                 stroke_width=2, stroke_fill="white")

    def el_balanco(img, x, y):
        c = L["balanco_final"]; painel(img, (x, y, x + S_BAL[0], y + S_BAL[1]))
        d = ImageDraw.Draw(img)
        d.text((x + 22, y + 12), c["titulo"], font=fnt(24, True), fill=TXT)
        for q, t in enumerate(c["linhas"]):
            d.text((x + 22, y + 48 + q * 32), t, font=fnt(22), fill=TXT)

    locais = [(n, *utm29(la, lo), pr) for n, la, lo, pr in L["localidades"]["lista"]]
    F_LOC1, F_LOC2 = fnt(L["localidades"]["tamanho"], True), fnt(L["localidades"]["tamanho"] - 3)

    # zonas ocupadas pelos painéis (para não pôr rótulos por baixo)
    zonas = []
    def reg(cfg, s):
        if cfg.get("mostrar", True):
            x, y = pos(cfg, *s); zonas.append((x, y, x + s[0], y + s[1]))
    for k, s in (("titulo", S_TIT), ("relogio", S_REL), ("legenda", S_LEG), ("enquadramento", S_OV),
                 ("barra_tempo", S_BT), ("escala", S_ESC), ("rodape", S_ROD)):
        reg(L[k], s)

    def sobrepoe(b, lst, f=4):
        return any(not (b[2] + f < z[0] or b[0] - f > z[2] or b[3] + f < z[1] or b[1] - f > z[3]) for z in lst)

    def el_localidades(img, x0w, y1w, k_px, m):
        d = ImageDraw.Draw(img)
        postos = list(zonas)
        for n, x, y, pr in sorted(locais, key=lambda t: t[3]):
            sx = (x - x0w) * k_px; sy = (y1w - y) * k_px
            if not (0 < sx < W and 0 < sy < H): continue
            f = F_LOC1 if pr == 1 else F_LOC2
            lab = n
            if n in L["chegadas"] and m / 60 >= L["chegadas"][n]:
                hc = L["chegadas"][n]
                lab = "%s · chegada %d h %02d" % (n, int(hc), round(hc % 1 * 60))
            tw, th = f.getlength(lab), f.size
            ok = None
            for ax, ay, anc in ((12, 0, "lm"), (-12, 0, "rm"), (0, -12, "mb"), (0, 14, "mt")):
                if anc == "lm": b = (sx + ax, sy - th / 2, sx + ax + tw, sy + th / 2)
                elif anc == "rm": b = (sx + ax - tw, sy - th / 2, sx + ax, sy + th / 2)
                elif anc == "mb": b = (sx - tw / 2, sy + ay - th, sx + tw / 2, sy + ay)
                else: b = (sx - tw / 2, sy + ay, sx + tw / 2, sy + ay + th)
                if b[0] > 5 and b[2] < W - 5 and b[1] > 5 and b[3] < H - 8 and not sobrepoe(b, postos):
                    ok = (ax, ay, anc, b); break
            if ok is None: continue
            r = 6 if pr == 1 else 4
            d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(40, 40, 40), outline=(255, 255, 255), width=2)
            d.text((sx + ok[0], sy + ok[1]), lab, font=f, fill=TXT, stroke_width=3, stroke_fill="white", anchor=ok[2])
            postos.append(ok[3])

    # ---------------- saídas
    def ff_mp4(path, w, h):
        return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (w, h),
                                 "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)

    def ff_alpha(path, w, h):
        return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "%dx%d" % (w, h),
                                 "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                                 "-pix_fmt", "yuva444p10le", "-vendor", "apl0", path], stdin=subprocess.PIPE)

    teste = os.environ.get("TESTE")
    quadros = [int(q) for q in teste.split(",")] if teste else range(N)
    pipes = {}
    if camadas:
        os.makedirs(camadas, exist_ok=True)
        for nome, el, s in (("titulo.png", el_titulo, S_TIT), ("legenda.png", el_legenda, S_LEG),
                            ("rodape.png", el_rodape, S_ROD), ("balanco_final.png", el_balanco, S_BAL)):
            im = Image.new("RGBA", s, (0, 0, 0, 0)); el(im, 0, 0); im.save(os.path.join(camadas, nome))
        if not teste:
            pipes["mapa"] = ff_mp4(os.path.join(camadas, "mapa.mp4"), W, H)
            for nome, s in (("relogio", S_REL), ("enquadramento", S_OV), ("barra_tempo", S_BT), ("escala", S_ESC)):
                pipes[nome] = ff_alpha(os.path.join(camadas, nome + ".mov"), s[0] + s[0] % 2, s[1] + s[1] % 2)
    elif not teste:
        pipes["final"] = ff_mp4(saida, W, H)
    log("a renderizar %d fotogramas (%.1f s de vídeo)%s" % (len(quadros), N / FPS, " em camadas" if camadas else ""))

    n_fade = int(V["fade_s"] * FPS)
    for i in quadros:
        m = sim[i]
        xmin = cx[i] - larg[i] / 2; xmax = cx[i] + larg[i] / 2
        hv = larg[i] * H / W; ymin = cy[i] - hv / 2; ymax = cy[i] + hv / 2
        k_px = W / larg[i]
        box20 = caixa(xmin, ymin, xmax, ymax, tx0, ty0, c20)
        box30 = caixa(xmin, ymin, xmax, ymax, gx0, gy0, c30)
        fr = BASE.transform((W, H), Image.EXTENT, box20, resample=Image.BILINEAR, fillcolor=COR_FUNDO).convert("RGBA")
        if i >= n_i + n_s + n_f:
            v = min(1.0, (i - n_i - n_s - n_f) / FPS)
            pm = prof(m) * (1 - v) + np.maximum(prof(m), GMAX) * v
        else:
            pm = prof(m)
        p = np.asarray(Image.fromarray(pm, "F").transform((W, H), Image.EXTENT, box30, Image.BILINEAR, fillcolor=-1.0))
        fr.alpha_composite(Image.fromarray(lut[np.digitize(p, LIM)], "RGBA"))
        if L["localidades"]["mostrar"]:
            el_localidades(fr, xmin, ymax, k_px, m)

        if camadas:
            if teste:
                fr.convert("RGB").save(os.path.join(camadas, "teste_mapa_%04d.png" % i)); continue
            pipes["mapa"].stdin.write(fr.convert("RGB").tobytes())
            for nome, s, fn in (("relogio", S_REL, lambda im: el_relogio(im, 0, 0, m)),
                                ("enquadramento", S_OV, lambda im: el_enquadramento(im, 0, 0, pm, box20, m)),
                                ("barra_tempo", S_BT, lambda im: el_barra(im, 0, 0, m)),
                                ("escala", S_ESC, lambda im: el_escala(im, 0, 0, k_px))):
                im = Image.new("RGBA", (s[0] + s[0] % 2, s[1] + s[1] % 2), (0, 0, 0, 0)); fn(im)
                pipes[nome].stdin.write(im.tobytes())
        else:
            if L["enquadramento"]["mostrar"]: el_enquadramento(fr, *pos(L["enquadramento"], *S_OV), pm, box20, m)
            if L["titulo"]["mostrar"]: el_titulo(fr, *pos(L["titulo"], *S_TIT))
            if L["relogio"]["mostrar"]: el_relogio(fr, *pos(L["relogio"], *S_REL), m)
            if L["legenda"]["mostrar"]: el_legenda(fr, *pos(L["legenda"], *S_LEG))
            if L["barra_tempo"]["mostrar"]: el_barra(fr, *pos(L["barra_tempo"], *S_BT), m)
            if L["escala"]["mostrar"]: el_escala(fr, *pos(L["escala"], *S_ESC), k_px)
            if L["rodape"]["mostrar"]: el_rodape(fr, *pos(L["rodape"], *S_ROD))
            if L["balanco_final"]["mostrar"] and i >= n_i + n_s + n_f:
                el_balanco(fr, *pos(L["balanco_final"], *S_BAL))
            out = fr.convert("RGB")
            if n_fade and (i < n_fade or i >= N - n_fade):
                a_ = (i + 1) / n_fade if i < n_fade else (N - i) / n_fade
                out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, max(0.0, min(1.0, a_)))
            if teste:
                out.save("teste_%04d.png" % i); continue
            pipes["final"].stdin.write(out.tobytes())
        if i % 150 == 0:
            log("  fotograma %d/%d  (T+%.1f h)" % (i, N, m / 60))
    for p_ in pipes.values():
        p_.stdin.close(); p_.wait()
    log("feito: %s" % (camadas or saida))


if __name__ == "__main__":
    args = sys.argv[1:]
    def opt(nome):
        if nome in args:
            k = args.index(nome); v = args[k + 1]; del args[k:k + 2]; return v
        return None
    lay = opt("--layout"); cam = opt("--camadas")
    main(args[0], args[1], args[2], lay, cam)
