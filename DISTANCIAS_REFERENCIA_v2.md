# ¿A CUÁNTO QUEDA? — Documento de referencia v2

App de distancias y tiempos de viaje entre 751 ciudades argentinas, derivada del PDF `Distancias_en_ciudades_Argentina.pdf` (3.726 páginas, Excel exportado vía ilovepdf, oct-2024). Pensada para GitHub Pages bajo `meteoro405`, sin frameworks ni backend, en línea con De Cuestas y MiGarage.

## Archivos del proyecto

| Archivo | Rol |
|---|---|
| `index.html` | App completa (HTML+CSS+JS en un solo archivo, estilo MiGarage) |
| `ciudades.js` | `N_CIUDADES` (751) y `CIUDADES` (array de nombres, índice = posición en la matriz) |
| `data.bin` | Matrices binarias: 2.256.004 bytes |
| `generar_datos.py` | Regenera `data.bin` y `ciudades.js` desde el PDF (requiere `pymupdf`) |

## Formato de data.bin (INVARIANTE — no cambiar sin tocar index.html)

- Dos matrices 751×751 consecutivas, fila-mayor (row-major), **Uint16 little-endian**.
- Bytes 0 a 1.128.001: **distancia en km × 10** (precisión 0,1 km). Lectura: `KM[i*751+j]/10`.
- Bytes 1.128.002 a 2.256.003: **tiempo en minutos** (segundos redondeados). Lectura: `MIN[i*751+j]`.
- Diagonal = 0. La matriz es **direccional**: `d(i,j) ≠ d(j,i)` en general.
- Máximos: 4.512,6 km y 3.065 min (51 h) — ambos entran en Uint16.

## Estructura del PDF de origen (para regenerar)

- 3 matrices en mosaico: cada una son 54 bloques-columna × 23 páginas.
- Páginas 1–1242: km · 1243–2484: millas (= km × 0,621, se descarta) · 2485–3726: tiempos H:MM:SS.
- Validación automática del parser: la **diagonal vacía** de cada bloque confirma la alineación de columnas (el orden de columnas = orden de filas). El script aborta con `assert` si algo no cierra.
- Trampas resueltas en el parser: nombres largos pegados al primer valor ("Buenos Aires2739.63"), glifos recortados por el clip del PDF (se extrae con `~fitz.TEXT_MEDIABOX_CLIP`), nombres envueltos en 2 líneas.

## Homónimos (19 grupos, 41 ciudades)

Desambiguados con sufijo de provincia en `CIUDADES`, verificados por huella de distancias a capitales + geografía real. Casos limítrofes corregidos a mano: General Roca #257 es **Río Negro** (no Neuquén, aunque la capital NQN quede a 46 km), Santo Tomé #627 es **Corrientes**, Veinticinco de Mayo #683 es **La Pampa**. La tabla completa está en `DUP_PROV` dentro de `generar_datos.py` — **no modificar sin revalidar**.

## Característica del dato: asimetría direccional

276 pares difieren en más de 150 km entre ida y vuelta, concentrados en **Cachí** (123 pares) y el corredor RN40 Cachí–Cafayate: ida 157 km (RN40 directa), vuelta 696 km (rodeo pavimentado). El motor de rutas original evitaba ripio en un sentido. La app lo muestra con el aviso amarillo cuando ida y vuelta difieren en más de 5 km. **No es un error: no "simetrizar" la matriz.**

## Verificación de cordura (valores comprobados)

Buenos Aires→Córdoba 697,3 km / 7h12 · BA→Mar del Plata 411,6 km / 4h35 · BA→Ushuaia 3.119,7 km / 34h28 · Morón→BA 27,1 km / 0h26. Velocidades implícitas: mediana 89 km/h, p1 63, p99 98 — coherente con rutas nacionales.

## Funciones de la app v2

Autocompletado insensible a tildes con teclado (↑↓ Enter Esc), botón invertir, cartel resultado estilo señalética vial (km, tiempo, velocidad media), aviso de asimetría, top-10 ciudades más cercanas al origen (clic = fijar destino), tema claro/oscuro (localStorage `acq_tema`), estado compartible en URL (`#o=12&d=345`), formato es-AR.

## Pendientes / ideas para próximas versiones

- PWA completa: `manifest.json` + `sw.js` con nombre de caché versionado (`acq-v2`, mismo criterio que Caminos: incrementar en cada release).
- Coordenadas lat/lon (cruzar contra georef/IGN) para mapa y orden por rumbo.
- Cruce con De Cuestas: si el par origen-destino pasa por un camino del catálogo, linkear la ficha.
- Selector de velocidad propia para recalcular tiempos.

## Cambios v1 → v2

- Título: "¿A cuánto queda?" + línea de marca "By Meteoro405" debajo (en verde vial, mayúsculas, letter-spacing).
- Pie: "vX · By Meteoro405" en vez de "v1 · Datos: matriz 751×751 direccional".
- Modo claro: paleta integrada con De Cuestas (`--bg:#F2E8CC`, `--card:#FAF4E4`, `--tinta:#4F3B26`, `--tinta-2:#8A6A50`, `--linea:rgba(79,59,38,.18)`). El modo oscuro y el cartel verde no cambian.
