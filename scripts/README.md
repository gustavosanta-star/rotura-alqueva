# Scripts

Numerados pela ordem de execução. Os que importam `arcpy` correm na janela Python do ArcGIS Pro (ou na *Python Command Prompt* do Pro). O `21_video_b1.py` corre num Python normal com numpy, scipy, Pillow, tifffile e ffmpeg.

| Script | O que faz |
|---|---|
| 00, 00b | área de estudo; descarga dos tiles LiDAR da DGT |
| 01 | ordens de grandeza (brecha, caudal de ponta, malha) |
| 02, 02b | curva cota-volume (SRTM) e curvas oficiais |
| 03 | terreno único a 10 m |
| 05 | descarga de dados abertos complementares |
| 06, 07 | retirar barragens do terreno; linha de Pedrógão |
| 08 | extrair resultados do HDF do HEC-RAS |
| 09, 10, 12 | COS 2025 → Manning (com a máscara do vale profundo) |
| 11 | comparação com a Tabela I.5 do PEExt |
| 13, 13b, 14 | produtos do B1; exposição em Portugal (BGRI) e nas duas margens (JRC + Catastro) |
| 15 | 4 layouts A3 |
| 16, 20, 20b | dados da cena 3D; imagens de profundidade de 2 em 2 min |
| 17, 18, 19, 22 | câmara, limite do modelo e keyframes da animação 3D (o 22 escreve no .aprx com o Pro fechado) |
| 21 + layout_video.json | vídeo 2D por código (e pacote editável com `--camadas`) |
| 23 | flyer A4 |
| kit/r0–r9 | eixo do rio, batimetria de Pedrógão e do estuário, linhas de referência, ficheiros HEC-RAS, BGRI/Catastro/JRC |
| util/ | GeoTIFF e UTM sem GDAL |

Troca `C:\caminho\para\rotura-alqueva` pela pasta do projeto.
