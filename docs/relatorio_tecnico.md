# Rotura hipotética da barragem de Alqueva — relatório técnico (cenário B1)

*Gustavo Santa · novembro de 2026 · versão 1.0*

> **Aviso.** Este trabalho é um **cenário hipotético**, feito para estudo e portefólio, apenas com dados abertos. **Não é um plano de emergência**, não usa informação reservada e **não substitui** o Plano de Emergência Externo (PEExt) da barragem de Alqueva, que é o documento oficial. O PEExt foi usado apenas como referência para validar a propagação da onda.

## 1. Resumo

Simulou-se, com um modelo hidráulico bidimensional (HEC-RAS 7.0.2), a rotura em série das barragens de **Alqueva** e **Pedrógão** e a propagação da onda de cheia pelo vale do Guadiana até à foz, ao longo de 24 h. Os resultados foram tratados em ArcGIS Pro 3.6 e em Python: mapas de profundidade, perigosidade, tempo de chegada e exposição da população, uma animação 3D e um vídeo 2D.

| Indicador (cenário B1) | Valor |
|---|---|
| Caudal máximo a jusante de Alqueva | ~210 000 m³/s |
| Área inundada pela onda (além da água já existente) | **22 631 ha** |
| Área com perigosidade extrema (h·v > 4 m²/s) | 10 351 ha |
| Área atingida nos primeiros 30 min | 1 319 ha |
| Residentes em zona inundada (PT + ES) | **~28 800** (até ~32 100) |
| Chegada da onda (subida ≥ 0,3 m) | Pedrógão 0 h 42 · Mértola 4 h 18 · Alcoutim 7 h 12 · VRSA 11 h 30 |

## 2. Cenário

- **Alqueva:** rotura com a albufeira a 154 m. Brecha de 148 m de base e 96 m de altura, taludes de 1:1,979 e tempo de formação de 8,7 min (Cd = 1,44). Os parâmetros foram testados num estudo de sensibilidade (planos P03–P06).
- **Pedrógão:** rotura desencadeada quando o nível chega a 94 m. No B1, isso acontece **29 min depois** da rotura de Alqueva.
- **Condições iniciais:** um aquecimento de 6 h com 5 000 m³/s enche Pedrógão até ~93 m e põe o rio a correr até à foz antes da rotura (às 09:00 do dia simulado).
- **Foz:** nível fixo de 2,0 m (sem maré nem sobre-elevação).
- **Duração:** 56 h de simulação; os produtos usam as 24 h seguintes à rotura (mapas de 10 em 10 min).

## 3. Dados (todos abertos)

| Tema | Fonte | Uso |
|---|---|---|
| Terreno do vale | MDT LiDAR 2 m, DGT (voo 2024), reamostrado a 10 m | terreno principal |
| Terreno em Espanha | MDT 5 m, CNIG | margem espanhola |
| Fundo das albufeiras | SRTM 1″ (NASA/USGS), de 2000, antes do enchimento | fundo de Alqueva e de Pedrógão |
| Estuário | canal parabólico calibrado com profundidades médias publicadas (Garel, UAlg/CIMA) | o LiDAR só vê a superfície da água |
| Ocupação do solo | COS 2025, DGT | rugosidade de Manning (18 grupos) |
| População (PT) | BGRI 2021 e ficheiro síntese dos Censos 2021, INE | exposição por subsecção |
| População (PT e ES) | JRC-ESTAT Census Population Grid 2021, 100 m | exposição nas duas margens |
| Edifícios (ES) | Catastro INSPIRE (D.G. del Catastro), 7 municípios de Huelva | edifícios e habitações expostos |
| Referência | PEExt de Alqueva (ANEPC), Tabela I.5 | validação da propagação |

Sistema de referência: **ETRS89 / UTM 29N (EPSG 25829)**, comum aos dois lados da fronteira.

## 4. Modelo hidráulico

- **Domínio:** duas áreas 2D, a **albufeira de Alqueva** (contorno SRTM a 158 m) e o **vale** da barragem à foz (*Perimeter 1*). Estão ligadas pela estrutura `Barragem_Alqueva` (ligação SA/2D com brecha). Pedrógão é uma ligação 2D interna com brecha.
- **Malha:** 100 m de base, refinada a **50 m** no canhão do Guadiana (de Pedrógão até 2 km a jusante de Mértola), com ~113 mil pontos no vale e ~12,5 mil na albufeira.
- **Terreno composto**, por ordem de prioridade: fundo de Pedrógão (SRTM) > canal do estuário > fundo de Alqueva (SRTM, correção vertical de −1 m) > LiDAR/MDT a 10 m. Verificação: volume de Alqueva a 152 m = 4 042 hm³ (oficial 4 150; −2,6 %); Pedrógão a 84,6 m = 91,6 hm³ (EDIA 99,1; −7,6 %).
- **Rugosidade:** n da COS 2025, e n = 0,040 nas encostas do canhão abaixo de talvegue + 30 m. Na prática, leito ~0,035 e estuário ~0,025.
- **Equações:** SWE completas, passo de tempo adaptativo.

## 5. Validação com o PEExt

Antes do cenário completo, correu-se um **teste de propagação**: o hidrograma do PEExt foi imposto 5 km a jusante da barragem e os resultados foram comparados com a Tabela I.5. Depois de uma ronda de melhorias (batimetria de Pedrógão e do estuário, foz a 2 m, rugosidade da COS), o modelo foi **congelado** no plano P12, com estes resultados:

| Perfil | Qmax P12 / PEExt (m³/s) | Nmax P12 − PEExt | Chegada P12 / PEExt (h) |
|---|---|---|---|
| Pedrógão (+0,5 km) | 37 148 / 56 471 | +2,0 m | 0,50 / 0,42 |
| Enxoé | 24 928 / 35 302 | +0,5 m | 1,08 / 0,79 |
| P20 (km 55) | 22 611 / 30 498 | +2,5 m | 1,58 / 1,01 |
| Pulo do Lobo | 20 672 / 27 549 | +19,2 m | 2,33 / 1,69 |
| Mértola | 19 971 / 25 500 | +10,1 m | 3,58 / 1,82 |
| Alcoutim | 18 932 / 22 883 | +8,5 m | 5,17 / 2,64 |

- **Níveis:** dentro de ±3 m até ao km 55. A partir do **Pulo do Lobo** ficam 8 a 19 m acima. A hipótese é que a garganta é mais estreita do que as células de 50 m e funciona como estrangulamento.
- **Caudais:** dentro de ±25 % a partir da linha P24 (logo a jusante do km 55); entre Pedrógão e o km 55 ficam 26 a 34 % abaixo.
- **Chegadas:** **1,4 a 2× mais lentas** do que no PEExt a jusante do Pulo do Lobo.

O critério de aceitação definido à partida (níveis ±3 m, chegadas ±30 %, Qmax ±25 %) **não foi cumprido** em todas as secções. Decidiu-se documentar os desvios e avançar. Os níveis mais altos estão do lado conservador; **as chegadas mais lentas não estão** (ver §8).

## 6. Resultados do cenário B1

| Local | Qmax (m³/s) | Nível máx. (m) | Pico (h) | Chegada (h) |
|---|---|---|---|---|
| Alqueva (0,2 km a jusante) | 210 239 | 145,4 | 0,2 | 0,2 |
| Pedrógão (+0,5 km) | 108 824 | 116,6 | 5,8 | 0,7 |
| Pulo do Lobo | 67 058 | 92,7 | 11,5 | 2,8 |
| Mértola | 63 975 | 67,9 | 15,2 | 4,3 |
| Alcoutim | 57 960 | 42,8 | 18,2 | 7,2 |
| Vila Real de Santo António | 55 535 | 9,5 | 21,5 | 11,5 |

*Horas contadas desde a rotura de Alqueva. Chegada = primeira subida ≥ 0,3 m acima do nível antes da rotura.*

- A albufeira de Alqueva esvazia quase toda (4 466 → 78 hm³). Por isso os caudais a jusante de Pedrógão são **2 a 2,5× os da Tabela I.5 do PEExt**, cujo pulso tem ~81 hm³. **Os dois cenários não são diretamente comparáveis.**
- **Área inundada pela onda:** 22 631 ha, contra 11 738 ha no PEExt (cenário menos gravoso).
- **Perigosidade (h·v, classes simplificadas da ARR 2019):** ≤ 0,3: 5 102 ha · 0,3–0,6: 1 609 · 0,6–1: 1 290 · 1–4: 4 269 · **> 4: 10 351 ha**.
- **Isócronas:** ≤ 30 min: 1 319 ha · 0,5–1 h: 1 718 · 1–2 h: 2 490 · 2–4 h: 3 734 · 4–8 h: 5 144 · 8–12 h: 4 632 · 12–24 h: 2 715.

### Exposição
- **Portugal (BGRI 2021, ponderação de área):** ~17 970 residentes (até 20 121), dos quais 4 631 com 65 anos ou mais; 6 227 edifícios; 607 ha de tecido urbano. Por concelho: VRSA 14 697 · Castro Marim 1 407 · Mértola 1 168 · Alcoutim 501.
- **Espanha (grelha JRC 100 m + Catastro):** 11 205 residentes (até 13 309); 2 303 edifícios e 10 762 habitações. Ayamonte 1 870 edifícios; Sanlúcar de Guadiana 376 (praticamente a aldeia toda).
- **Coerência:** em Portugal, a grelha JRC dá 17 626 residentes contra 17 968 da BGRI (−2 %).
- **Total das duas margens: ~28 800 residentes** (até ~32 100).

## 7. Produtos
- 4 mapas A3: profundidade, perigosidade, chegada e exposição (`scripts/15_layouts_b1.py`).
- **Vídeo 2D** (59 s, 1080p), gerado por código a partir das profundidades de 2 em 2 min (`21_video_b1.py`). A câmara segue a frente da onda, com relógio, barra de chegadas e enquadramento; há também um pacote editável por camadas.
- **Animação 3D** em ArcGIS Pro: exagero vertical 3×, câmara oblíqua a seguir a frente; keyframes gerados por `22_anim3d_aprx.py`.
- Flyer A4 (`23_flyer_b1.py`).

## 8. Limitações
1. **Chegadas a jusante do Pulo do Lobo 1,4–2× mais lentas** do que no PEExt (§5). Os tempos de chegada do Alentejo/Algarve interior **não devem ser lidos como tempos de aviso**.
2. **Níveis a jusante do Pulo do Lobo 8–19 m acima do PEExt** no teste de propagação: a malha de 50 m não resolve a garganta, e falta batimetria do leito.
3. **Erro de volume de 8,8 %** no B1, todo na contabilidade da ligação SA/2D da albufeira, depois das 12 h. Os **máximos não são afetados** (a água espúria chega a cada local depois do pico); só a recessão final fica inflacionada.
4. **Foz:** nível fixo de 2 m, sem maré nem sobre-elevação. Nos sapais de Castro Marim e nas marismas de Isla Cristina a cheia encosta ao **limite da malha** (parede), por isso a **área inundada na foz está subestimada**.
5. **Exposição:** população uniforme dentro de cada subsecção ou célula de 100 m; residentes, não população presente (turismo em VRSA e Monte Gordo); o país de cada célula é atribuído pela BGRI.
6. **Terreno:** o fundo de Alqueva e de Pedrógão vem do SRTM de 2000 (30 m, −1 m de correção); o estuário é um canal esquemático.
7. É **um** cenário de rotura; não se estudou a probabilidade nem outras combinações de brecha.

## 9. Reprodutibilidade
Os scripts estão em `scripts/`, numerados pela ordem de execução. Os dados e o modelo HEC-RAS não vão no repositório (vários GB); descarregam-se das fontes do §3 com `00b_descarregar_lidar_dgt.py` e `05_dados_abertos.py`. Os caminhos nos scripts apontam para `C:\caminho\para\rotura-alqueva`: troca-se pela pasta do projeto.

## 10. Referências
- ANEPC (2024). *Plano de Emergência Externo da Barragem de Alqueva*.
- EDIA (2010). *Plano de Emergência Interno do Aproveitamento Hidráulico de Alqueva*.
- US Army Corps of Engineers, Hydrologic Engineering Center. *HEC-RAS 2D User's Manual*, versão 7.
- Ball, J. et al. (eds.) (2019). *Australian Rainfall and Runoff* — Livro 6, perigosidade de cheias (classes h·v).
- DGT — MDT LiDAR 2 m e COS 2025; CNIG — MDT 5 m; NASA/USGS — SRTM 1″.
- INE — BGRI 2021 e Censos 2021; JRC/Eurostat — Census Population Grid 2021; Dirección General del Catastro — edifícios INSPIRE.
