"""
00b - Descarregar o LiDAR da DGT (Centro de Dados, cdd.dgterritorio.gov.pt)
para a area de estudo, sem sair do ArcGIS Pro.

Correr na "Python Command Prompt" do ArcGIS Pro (usa arcpy + requests, ambos
incluidos no Pro):

  python 00b_descarregar_lidar_dgt.py <aoi> <pasta_saida> [colecoes] [--so-listar]

  aoi          feature class do corredor (saida do script 00: aoi_vale_jusante)
  pasta_saida  ex.: dados\\mdt            (cria uma subpasta por colecao)
  colecoes     por omissao MDT-2m  (outras: MDS-2m, MDT-50cm, MDS-50cm, LAZ)
  --so-listar  so conta os ficheiros por colecao, sem descarregar
               (o login e pedido na mesma: a pesquisa tambem exige sessao)

O utilizador e a palavra-passe da tua conta gratuita do Centro de Dados sao
pedidos no terminal e ficam so em memoria: nada e gravado em disco.

Como funciona (o portal nao tem documentacao publica da API; o fluxo foi
reconstituido a partir do plugin de codigo aberto "DGT CDD Downloader"):
  1. login pelo formulario do portal (sessao por cookies);
  2. pesquisa STAC por pequenas caixas que tocam no corredor;
  3. descarregamento dos GeoTIFF, saltando os que ja existem.

NAO FOI TESTADO: nao tenho conta nem acesso de rede ao portal deste lado.
Comecar por --so-listar. Se o portal mudar, o ponto fragil e o login.
"""
import getpass
import math
import os
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urljoin

SITE = "https://cdd.dgterritorio.gov.pt"
AUTH = "https://auth.cdd.dgterritorio.gov.pt/realms/dgterritorio/protocol/openid-connect/auth"
STAC = SITE + "/dgt-be/v1/search"
PASSO_GRAUS = 0.1          # caixas de ~9 x 11 km (~100 km2), abaixo do limite de 200 km2
PAUSA_S = 2.0              # pausa entre descarregamentos, para nao sobrecarregar o servidor
VALIDADE_SESSAO_S = 25 * 60


class FormularioLogin(HTMLParser):
    """Apanha o 'action' e os campos ocultos do formulario de login."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.campos = {}
        self._dentro = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("id") == "kc-form-login":
            self._dentro = True
            self.action = a.get("action")
        elif tag == "input" and self._dentro and a.get("type") == "hidden" and a.get("name"):
            self.campos[a["name"]] = a.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "form":
            self._dentro = False


def entrar(sessao, utilizador, palavra_passe):
    sessao.get(SITE, timeout=30)
    r = sessao.get(AUTH, timeout=30, params={
        "client_id": "aai-oidc-dgt",
        "response_type": "code",
        "redirect_uri": SITE + "/auth/callback",
        "scope": "openid profile email",
    })
    # Se a sessao no servidor de autenticacao ainda e valida, o portal devolve
    # logo ao site sem mostrar o formulario: ja estamos dentro.
    if r.url.startswith(SITE):
        return time.time()
    form = FormularioLogin()
    form.feed(r.text)
    if not form.action:
        raise RuntimeError("Formulario de login nao encontrado: o portal mudou?")
    dados = dict(form.campos, username=utilizador, password=palavra_passe)
    r = sessao.post(urljoin(r.url, form.action), data=dados, timeout=30)
    if not r.url.startswith(SITE):
        raise RuntimeError("Login recusado: confirmar utilizador e palavra-passe.")
    return time.time()


def renovar(sessao, utilizador, palavra_passe, t_anterior):
    """Renova a sessao; tenta 3 vezes antes de desistir, sem rebentar o programa."""
    for tentativa in (1, 2, 3):
        try:
            return entrar(sessao, utilizador, palavra_passe)
        except Exception as erro:          # rede ou portal
            print(f"\n[aviso] renovar sessao falhou: {erro} (tentativa {tentativa}/3)")
            time.sleep(30)
    sys.exit("Nao consegui renovar a sessao. Voltar a correr o comando retoma onde parou.")


def caixas_no_corredor(aoi):
    """Caixas WGS84 [oeste, sul, este, norte] que tocam no poligono da area de estudo."""
    import arcpy

    wgs84 = arcpy.SpatialReference(4326)
    geoms = [r[0].projectAs(wgs84) for r in arcpy.da.SearchCursor(aoi, ["SHAPE@"])]
    xmin = min(g.extent.XMin for g in geoms)
    ymin = min(g.extent.YMin for g in geoms)
    xmax = max(g.extent.XMax for g in geoms)
    ymax = max(g.extent.YMax for g in geoms)
    caixas = []
    for i in range(math.ceil((xmax - xmin) / PASSO_GRAUS)):
        for j in range(math.ceil((ymax - ymin) / PASSO_GRAUS)):
            o, s = xmin + i * PASSO_GRAUS, ymin + j * PASSO_GRAUS
            e, n = o + PASSO_GRAUS, s + PASSO_GRAUS
            cel = arcpy.Polygon(arcpy.Array(
                [arcpy.Point(*p) for p in ((o, s), (e, s), (e, n), (o, n), (o, s))]), wgs84)
            if any(not g.disjoint(cel) for g in geoms):
                caixas.append([o, s, e, n])
    return caixas, geoms


DIAG = {"sem_contorno": 0, "em_metros": 0, "exemplo": None}


def _coords(geom):
    """Todas as coordenadas de uma geometria GeoJSON (Polygon ou MultiPolygon)."""
    pilha, saida = [(geom or {}).get("coordinates")], []
    while pilha:
        c = pilha.pop()
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            saida.append(c)
        elif isinstance(c, (list, tuple)):
            pilha.extend(c)
    return saida


def contorno(item):
    """Caixa [o, s, e, n] do tile: da geometria do item ou, na falta, da sua bbox."""
    pts = _coords(item.get("geometry"))
    if pts:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return [min(xs), min(ys), max(xs), max(ys)]
    b = item.get("bbox")
    if b and len(b) >= 4:
        return [b[0], b[1], b[-2], b[-1]]
    return None


def toca_no_corredor(item, geoms):
    """So fica o tile cujo contorno toca no corredor."""
    import arcpy

    cx = contorno(item)
    if cx is None:
        DIAG["sem_contorno"] += 1
        return True                       # sem contorno: na duvida, fica
    if DIAG["exemplo"] is None:
        DIAG["exemplo"] = cx
    o, s, e, n = cx
    # graus com a ordem trocada (lat, lon): em Portugal a "longitude" seria ~37-42
    if 30 < o < 45 and -12 < s < 0:
        DIAG["trocados"] = DIAG.get("trocados", 0) + 1
        o, s, e, n = s, o, n, e
    # o portal pode dar as coordenadas em PT-TM06 (metros) em vez de graus
    if max(abs(o), abs(e)) > 180 or max(abs(s), abs(n)) > 90:
        DIAG["em_metros"] += 1
        sr = arcpy.SpatialReference(3763)
    else:
        sr = arcpy.SpatialReference(4326)
    cel = arcpy.Polygon(arcpy.Array(
        [arcpy.Point(*p) for p in ((o, s), (e, s), (e, n), (o, n), (o, s))]), sr)
    cel = cel.projectAs(geoms[0].spatialReference)
    return any(not g.disjoint(cel) for g in geoms)


def extensao(tipo):
    tipo = (tipo or "").lower()
    if "tiff" in tipo:
        return ".tif"
    if "laszip" in tipo or "las" in tipo:
        return ".laz"
    return None


def pesquisar(sessao, caixas, colecoes, geoms):
    """Devolve {colecao: {nome_ficheiro: url}} sem repeticoes, so tiles no corredor."""
    achados = {c: {} for c in colecoes}
    vistos, fora = set(), 0
    for k, caixa in enumerate(caixas, 1):
        r = sessao.post(STAC, json={"bbox": caixa, "collections": colecoes, "limit": 1000},
                        timeout=60)
        r.raise_for_status()
        itens = r.json().get("features", [])
        if len(itens) >= 1000:
            print(f"[aviso] caixa {k} devolveu 1000 itens: pode haver mais; reduzir PASSO_GRAUS")
        for item in itens:
            col = item.get("collection")
            if col not in achados:
                continue
            chave = (col, item.get("id"))
            if chave in vistos:
                continue
            vistos.add(chave)
            if not toca_no_corredor(item, geoms):
                fora += 1
                continue
            for asset in (item.get("assets") or {}).values():
                ext = extensao(asset.get("type"))
                if ext and asset.get("href"):
                    achados[col][item["id"] + ext] = asset["href"]
        print(f"  pesquisa {k}/{len(caixas)}", end="\r")
        time.sleep(0.2)
    print()
    print(f"{fora} tiles descartados por ficarem fora do corredor")
    print(f"[diag] sem contorno: {DIAG['sem_contorno']} | em metros: {DIAG['em_metros']} "
          f"| lat/lon trocados: {DIAG.get('trocados', 0)} "
          f"| exemplo de contorno: {DIAG['exemplo']}")
    return achados


def descarregar(sessao, url, destino):
    with sessao.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        if "text/html" in r.headers.get("Content-Type", ""):
            raise PermissionError("o servidor devolveu uma pagina em vez do ficheiro (sessao expirada?)")
        parcial = destino + ".parcial"
        with open(parcial, "wb") as f:
            for bloco in r.iter_content(1 << 20):
                f.write(bloco)
    os.replace(parcial, destino)


def main(argv):
    so_listar = "--so-listar" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) not in (2, 3):
        sys.exit(__doc__)
    aoi, pasta = args[0], args[1]
    colecoes = (args[2] if len(args) == 3 else "MDT-2m").split(",")

    import requests

    caixas, geoms = caixas_no_corredor(aoi)
    print(f"{len(caixas)} caixas de pesquisa sobre a area de estudo")

    utilizador = input("Utilizador do Centro de Dados da DGT: ").strip()
    palavra_passe = getpass.getpass("Palavra-passe (nao aparece no ecra): ")
    sessao = requests.Session()
    sessao.headers["User-Agent"] = "rotura-alqueva/0.1 (projeto academico; requests)"
    t_login = entrar(sessao, utilizador, palavra_passe)
    print("Sessao iniciada.")

    achados = pesquisar(sessao, caixas, colecoes, geoms)
    for col, fich in achados.items():
        print(f"{col}: {len(fich)} ficheiros")
    if so_listar:
        return

    for col, fich in achados.items():
        destino_col = os.path.join(pasta, col)
        os.makedirs(destino_col, exist_ok=True)
        for n, (nome, url) in enumerate(sorted(fich.items()), 1):
            destino = os.path.join(destino_col, nome)
            if os.path.exists(destino):
                continue
            if time.time() - t_login > VALIDADE_SESSAO_S:
                t_login = renovar(sessao, utilizador, palavra_passe, t_login)
            for tentativa in (1, 2, 3):
                try:
                    descarregar(sessao, url, destino)
                    break
                except PermissionError:
                    t_login = renovar(sessao, utilizador, palavra_passe, t_login)
                except requests.RequestException as erro:
                    print(f"\n[aviso] {nome}: {erro} (tentativa {tentativa}/3)")
                    time.sleep(5)
            else:
                print(f"\n[falhou] {nome}")
            print(f"  {col} {n}/{len(fich)}", end="\r")
            time.sleep(PAUSA_S)
        print()
    print("Concluido. Voltar a correr o comando retoma apenas o que faltar.")


if __name__ == "__main__":
    main(sys.argv[1:])
