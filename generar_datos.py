#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos para "¿A cuánto queda?" — v1
Extrae las matrices de distancia (km) y tiempo desde
Distancias_en_ciudades_Argentina.pdf y produce data.bin + ciudades.js

Uso: python3 generar_datos.py ruta/al/Distancias_en_ciudades_Argentina.pdf
Requiere: pip install pymupdf
Salida en /tmp/ (copiar manualmente a la carpeta de la app, como en Caminos)
"""
import fitz, re, json, struct, sys
from collections import Counter

PDF = sys.argv[1] if len(sys.argv) > 1 else 'Distancias_en_ciudades_Argentina.pdf'
doc = fitz.open(PDF)
WORD_FLAGS = fitz.TEXTFLAGS_WORDS & ~fitz.TEXT_MEDIABOX_CLIP
DICT_FLAGS = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_MEDIABOX_CLIP
KM, TIME = re.compile(r'^\d+\.\d{2}$'), re.compile(r'^\d+:\d{2}:\d{2}$')
KM_TAIL = re.compile(r'^(.*?)(\d+\.\d{2})$')
TIME_TAIL = re.compile(r'^(.*?)(\d+:\d{2}:\d{2})$')
FIRSTVAL = re.compile(r'\d+\.\d{2}')

# Estructura del PDF: 3 matrices de 54 bloques-columna x 23 páginas c/u
# [0-1241]=km  [1242-2483]=millas (se ignora)  [2484-3725]=tiempos
def parse_block(p0, val_re, tail_re):
    all_rows, col_xs = [], None
    for pi in range(p0, p0 + 23):
        raw = doc[pi].get_text('words', flags=WORD_FLAGS)
        vals = []
        for w in raw:
            if val_re.match(w[4]):
                vals.append(w)
            else:
                m = tail_re.match(w[4])
                if m and m.group(1) and not val_re.match(m.group(1)):
                    vals.append((w[0], w[1], w[2], w[3], m.group(2)))  # nombre pegado al valor
        if not vals: continue
        if col_xs is None:
            xs, cols = sorted(round(w[2], 1) for w in vals), []
            for x in xs:
                if not cols or x - cols[-1][-1] > 8: cols.append([x])
                else: cols[-1].append(x)
            col_xs = [sum(c) / len(c) for c in cols]
        vals.sort(key=lambda w: w[1]); rows = []
        for w in vals:
            if rows and abs(w[1] - rows[-1][0]) < 5: rows[-1][1].append(w)
            else: rows.append([w[1], [w]])
        for y, ws in rows:
            vrow = {}
            for w in ws:
                ci = min(range(len(col_xs)), key=lambda i: abs(col_xs[i] - w[2]))
                vrow[ci] = w[4]
            all_rows.append(vrow)
    return all_rows, len(col_xs)

def extract_matrix(start, val_re, tail_re, label):
    blocks, g, N = [], 0, None
    for b in range(54):
        rows, ncols = parse_block(start + b * 23, val_re, tail_re)
        if N is None: N = len(rows)
        assert len(rows) == N, f"{label} b{b}: {len(rows)} filas != {N}"
        for k in range(ncols):  # validación por diagonal vacía
            assert k not in rows[g + k], f"{label} b{b}: diagonal rota fila {g+k}"
        blocks.append((g, rows)); g += ncols
    assert g == N, f"{label}: {g} columnas != {N} filas"
    M = [[None] * N for _ in range(N)]
    for g0, rows in blocks:
        for ri, vrow in enumerate(rows):
            for ci, v in vrow.items(): M[ri][g0 + ci] = v
    falt = sum(1 for i in range(N) for j in range(N) if i != j and M[i][j] is None)
    print(f"  {label}: {N}x{N}, faltantes={falt}")
    assert falt == 0
    return M, N

def extract_names(N):
    names = []
    for pi in range(23):
        page = doc[pi]
        vws = sorted([w for w in page.get_text('words', flags=WORD_FLAGS) if KM.match(w[4])],
                     key=lambda w: w[1])
        rows = []
        for w in vws:
            if rows and abs(w[1] - rows[-1]) < 5: continue
            rows.append(w[1])
        row_cy = [y + 5 for y in rows]
        frags = []
        for b in page.get_text('dict', flags=DICT_FLAGS)['blocks']:
            for l in b.get('lines', []):
                if l['bbox'][0] > 100: continue
                txt = ''.join(s['text'] for s in l['spans'])
                m = FIRSTVAL.search(txt)
                label = (txt[:m.start()] if m else txt).strip()
                cy = (l['bbox'][1] + l['bbox'][3]) / 2
                if not label or cy < rows[0] - 8: continue
                frags.append((cy, label))
        page_names = {i: [] for i in range(len(row_cy))}
        for cy, label in frags:
            page_names[min(range(len(row_cy)), key=lambda k: abs(row_cy[k] - cy))].append((cy, label))
        for i in range(len(row_cy)):
            names.append(' '.join(t for _, t in sorted(page_names[i])).strip())
    assert len(names) == N and all(names)
    return names

# Homónimos verificados a mano (índice -> provincia). NO MODIFICAR sin revalidar.
PROV = {"BA":"Buenos Aires","CBA":"Córdoba","SF":"Santa Fe","MZA":"Mendoza","SJ":"San Juan",
"SL":"San Luis","CAT":"Catamarca","SE":"Santiago del Estero","SAL":"Salta","FOR":"Formosa",
"COR":"Corrientes","MIS":"Misiones","ER":"Entre Ríos","NQN":"Neuquén","RN":"Río Negro","LP":"La Pampa"}
DUP_PROV = {14:"CBA",15:"MIS",60:"MIS",61:"COR",87:"MIS",88:"SL",247:"SAL",248:"FOR",
257:"RN",258:"CBA",380:"COR",381:"MIS",397:"BA",398:"SL",419:"BA",420:"COR",
444:"BA",445:"SJ",446:"COR",478:"BA",479:"CBA",526:"CAT",527:"SF",562:"MIS",563:"CBA",
584:"SF",585:"ER",589:"MZA",590:"SJ",595:"BA",596:"MIS",597:"SE",612:"SJ",613:"COR",
616:"LP",617:"COR",626:"SF",627:"COR",681:"BA",682:"MIS",683:"LP"}

print("Extrayendo km...");      KM_M, N = extract_matrix(0, KM, KM_TAIL, "km")
print("Extrayendo tiempos..."); T_M, _ = extract_matrix(2484, TIME, TIME_TAIL, "tiempo")
print("Extrayendo nombres..."); names = extract_names(N)

display = list(names)
for i, p in DUP_PROV.items(): display[i] = f"{names[i]} ({PROV[p]})"
assert max(Counter(display).values()) == 1, "quedan nombres duplicados"

def t2min(s):
    h, m, sec = s.split(':')
    return int(h) * 60 + int(m) + (1 if int(sec) >= 30 else 0)

km10, mins = [], []
for i in range(N):
    for j in range(N):
        km10.append(0 if i == j else round(float(KM_M[i][j]) * 10))
        mins.append(0 if i == j else t2min(T_M[i][j]))
assert max(km10) < 65536 and max(mins) < 65536

with open('/tmp/data.bin', 'wb') as f:
    f.write(struct.pack(f'<{N*N}H', *km10))
    f.write(struct.pack(f'<{N*N}H', *mins))
with open('/tmp/ciudades.js', 'w', encoding='utf-8') as f:
    f.write("// Generado desde Distancias_en_ciudades_Argentina.pdf — v1\n")
    f.write(f"const N_CIUDADES = {N};\n")
    f.write("const CIUDADES = " + json.dumps(display, ensure_ascii=False) + ";\n")
print(f"OK -> /tmp/data.bin ({N*N*4:,} bytes) y /tmp/ciudades.js ({N} ciudades)")
