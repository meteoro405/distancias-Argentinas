# ¿A CUÁNTO QUEDA? — Documento de referencia integral v8

> Este documento está pensado para que **cualquier instancia nueva de Claude** (en otro chat) pueda retomar este proyecto sin que Ariel tenga que re-explicar nada. Contiene: qué es la app, cómo se generaron los datos, el estado exacto del código v5, el historial completo de decisiones v1→v5, los invariantes que no hay que romper, los problemas conocidos, y cómo se integra con el resto del "ecosistema Meteoro405".

---

## 1. Qué es esta app

**"¿A cuánto queda?"** es una PWA de una sola página (sin frameworks, sin backend) que muestra **distancia por ruta y tiempo de viaje entre 751 ciudades argentinas**, con autocompletado, "más cercanas", link a Google Maps, compartir por WhatsApp, y una calculadora de costo de combustible. Vive en GitHub bajo la cuenta `meteoro405`.

- **Repo**: `https://github.com/meteoro405/distancias-Argentinas`
- **URL pública (GitHub Pages)**: `https://meteoro405.github.io/distancias-Argentinas/`
- **Estado actual**: v5, subido y funcionando (Ariel confirmó v1-v4 visualmente; v5 es el paquete que se entrega con este documento, todavía no confirmado en producción).

### Origen de los datos

Todo nace de un PDF de **3.726 páginas** (`Distancias_en_ciudades_Argentina.pdf`, exportado de Excel) que contiene tres matrices en mosaico de **751×751 ciudades**, cada una en 54 bloques-columna × 23 páginas:
- Páginas 1–1242: distancia en **km**
- Páginas 1243–2484: distancia en **millas** (se descarta, redundante)
- Páginas 2485–3726: **tiempo de viaje** (H:MM:SS)

La matriz es **direccional**: `d(i,j) ≠ d(j,i)` en general. Esto no es un error — el caso extremo es **Cachí** (Salta): Cachí→Cafayate son 157 km (RN40 directa), pero Cafayate→Cachí son 696 km (rodeo pavimentado, el motor de rutas original evitaba el ripio en un sentido). 276 pares difieren >150 km entre ida y vuelta. **Nunca "simetrizar" la matriz.**

---

## 2. Estructura de archivos (v5)

```
Distancias_v5/
├── index.html              (752 líneas — toda la app: HTML+CSS+JS)
├── ciudades.js              (N_CIUDADES=751, array CIUDADES)
├── data.bin                  (2.256.004 bytes — dos matrices Uint16 751×751)
├── generar_datos.py         (regenera data.bin + ciudades.js desde el PDF)
├── manifest.json             (PWA)
├── sw.js                      (Service Worker, cache 'acq-v5')
├── icons/
│   ├── icon-192.png
│   ├── icon-512.png
│   ├── icon-maskable-512.png
│   ├── apple-touch-icon.png
│   └── favicon.png
└── DISTANCIAS_REFERENCIA_v5.md   (este archivo)
```

Todos van **juntos en la raíz del repo** (no en subcarpetas), para que `https://meteoro405.github.io/distancias-Argentinas/` sirva `index.html` directamente y todas las rutas relativas (`ciudades.js`, `data.bin`, `icons/...`, `manifest.json`, `sw.js`) resuelvan bien.

---

## 3. Formato de `data.bin` (INVARIANTE — no cambiar sin actualizar `index.html` Y `generar_datos.py` a la vez)

- Dos matrices 751×751 consecutivas, **row-major, Uint16 little-endian**.
- Bytes `0` a `1.128.001`: **distancia en km × 10** (precisión 0,1 km). Lectura: `KM[i*751+j] / 10`.
- Bytes `1.128.002` a `2.256.003`: **tiempo en minutos** (segundos redondeados). Lectura: `MIN[i*751+j]`.
- Diagonal = 0 en ambas matrices.
- Máximos observados: 4.512,6 km y 3.065 min (51h) — ambos entran en Uint16 (<65536).

En `index.html`, la carga es:
```js
fetch('data.bin').then(r=>r.arrayBuffer()).then(buf=>{
  const n=N_CIUDADES*N_CIUDADES;
  KM=new Uint16Array(buf,0,n);
  MIN=new Uint16Array(buf,n*2,n);
});
```

---

## 4. `ciudades.js`

```js
const N_CIUDADES = 751;
const CIUDADES = [...]; // 751 strings, índice == posición en data.bin
```

### Homónimos (19 grupos, 41 ciudades)

Desambiguados con sufijo `" (Provincia)"`, verificado por huella de distancias a capitales provinciales + geografía real. Casos limítrofes NO obvios, ya resueltos — **no volver a tocar sin re-validar**:
- General Roca → **Río Negro** (no Neuquén, aunque la capital NQN quede a 46 km)
- Santo Tomé → **Corrientes**
- Veinticinco de Mayo → **La Pampa**

La tabla completa de asignaciones (`DUP_PROV`, 41 entradas índice→provincia) está hardcodeada dentro de `generar_datos.py` con el comentario "NO MODIFICAR sin revalidar".

### Función `paraMaps()` (en index.html)

Convierte `"Mercedes (Corrientes)"` → `"Mercedes, Corrientes, Argentina"` y `"Ushuaia"` → `"Ushuaia, Argentina"`, para armar queries de Google Maps sin ambigüedad.

---

## 5. `generar_datos.py` — regeneración desde el PDF

```bash
pip install pymupdf --break-system-packages
python3 generar_datos.py ruta/al/Distancias_en_ciudades_Argentina.pdf
```

Escribe a `/tmp/data.bin` y `/tmp/ciudades.js` (convención: copiar manualmente a la carpeta de la app, como en los generadores de De Cuestas). Internamente:

1. `parse_block()`: por cada bloque de 23 páginas, extrae valores numéricos (`KM` o `TIME` regex) con **PyMuPDF** usando `~fitz.TEXT_MEDIABOX_CLIP` (sin esto, los nombres largos quedan recortados por el clip del PDF — bug ya resuelto).
2. Maneja nombres pegados al valor numérico ("Buenos Aires2739.63") separándolos con `KM_TAIL`/`TIME_TAIL` regex.
3. `extract_matrix()`: valida que **la diagonal de cada bloque esté vacía** — si no, `assert` falla. Esto confirma que el orden de columnas == orden de filas (es la validación de integridad automática).
4. `extract_names()`: extrae los 751 nombres desde las primeras 23 páginas (sección km), cortando en el primer valor numérico de cada línea.
5. Aplica `DUP_PROV` para desambiguar homónimos.
6. Empaqueta a `data.bin` (ver formato arriba) y `ciudades.js`.
7. Asserts finales: 0 celdas faltantes, máximos < 65536, 0 nombres duplicados tras desambiguar.

**Reproducibilidad verificada**: corrida completa produce `data.bin` y `ciudades.js` byte-a-byte idénticos a los entregados.

---

## 6. Arquitectura de `index.html`

Un solo archivo. Estructura HTML (`.envoltura`):

1. **`<header>`**: escudo verde "RN" (pentágono CSS, mismo motivo que los íconos PWA) + `<h1>¿A cuánto queda?</h1>` (Playfair Display) + `.firma` "BY METEORO405" (Saira Condensed, color `--acento`) + subtítulo + botón de tema `#btnTema`.
2. **Panel de búsqueda** (`.panel`): dos campos con autocompletado (`#campoO`/`#campoD`, función `armarCampo()`), botón invertir `#btnInvertir`.
3. **`#estado`**: mensaje cuando falta elegir origen/destino.
4. **`#resultado`** (oculto hasta tener ruta válida):
   - `.cartel` — el "cartel de ruta" verde estilo señalética vial: destino, km, tiempo, velocidad media.
   - `.aviso` — caja amarilla, visible solo si `|ida - vuelta| > 5 km` (caso Cachí).
   - `.acciones` — botón `#btnMaps` (abre modal) + link `#lnkWsp` (WhatsApp).
   - `.costo` — panel colapsable "⛽ Calcular costo del viaje" (`#costoToggle`/`#costoCuerpo`).
5. **`#cercanas`**: top-10 ciudades más cercanas al origen — **solo visible si no hay destino válido elegido** (se oculta apenas se completa destino, v4).
6. **`#instalarBanner`**: banner de instalación PWA (aparece con `beforeinstallprompt`).
7. **`<footer>`**: texto legal + "v5 · By Meteoro405" + botón persistente `#btnInstalar`.
8. **`#mapaModal`**: modal con iframe de Google Maps (fuera de `.envoltura`, overlay fixed).

### Funciones JS clave (todo dentro de un único IIFE)

| Función | Qué hace |
|---|---|
| `armarCampo(campo, alElegir)` | Autocompletado: filtra `CIUDADES` sin tildes (`norm()`), navegación con teclado, callback `alElegir(índice)` |
| `refrescar()` | Función central: lee `idxO`/`idxD`, actualiza cartel, aviso, cercanas, costo, WhatsApp, hash de URL |
| `renderCercanas(o)` | Top-10 más cercanas a `o`, click fija destino |
| `km(i,j)` / `min(i,j)` | Lectura directa de `KM`/`MIN` (Uint16Array) |
| `paraMaps(nombre)` | "Ciudad (Provincia)" → "Ciudad, Provincia, Argentina" |
| `actualizarWsp()` | Arma el mensaje de WhatsApp (ruta + km + tiempo + costo si está cargado + link con hash) |
| `calcularCosto()` / `actualizarCosto()` | Calculadora de combustible (ver sección 8) |
| `abrirMapa()` / `cerrarMapa()` | Modal de Google Maps embebido (ver sección 7) |
| `actualizarHash()` / `leerHash()` | Estado compartible en URL: `#o=66&d=181` |

---

## 7. "Ver en Maps" — modal embebido (v4)

`#btnMaps` abre un modal (`#mapaModal`) con:
- `<iframe id="mapaFrame">` → `https://maps.google.com/maps?saddr=...&daddr=...&output=embed` (truco legacy sin API key — **sin garantía oficial de Google**, puede dejar de funcionar sin aviso).
- `#mapaFallback` → siempre visible, link completo `https://www.google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=driving` que abre en pestaña/app nueva. **Es el respaldo si el iframe no carga.**
- Cierre: botón ✕, click fuera del modal, o tecla Esc.

**Pendiente de verificar en producción**: si el iframe se muestra en blanco en el celu de Ariel, ya está cubierto por el fallback — no es bloqueante, pero conviene preguntarle cómo se ve.

---

## 8. Calculadora de costo de combustible (v4)

Panel colapsable bajo los botones de acción:

- **Consumo** (`#inConsumo`, "cada 100 km") — número genérico, persiste en `localStorage.acq_consumo`.
- **Combustible** (`#inCombustible`): Nafta / Nafta premium / Gasoil / Gasoil premium / GNC. Persiste en `localStorage.acq_combustible`. Cambia la unidad mostrada: L para naftas/gasoil, m³ para GNC (`UNIDADES` map).
- **Precio** (`#inPrecio`, "$/L" o "$/m³") — **manual**, un valor recordado *por tipo de combustible* en `localStorage.acq_precios` (JSON `{nafta: 1200, gnc: 800, ...}`).
- Resultado: `litros = km × consumo/100`; `costo = litros × precio` formateado con `Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS'})`.
- Si hay precio cargado, se agrega una línea `⛽ X L · $Y` al mensaje de WhatsApp.
- Nota con link a la consulta oficial: `https://res1104.se.gob.ar/consultaprecios.eess.php`.

**Por qué no hay precio automático/en vivo**: investigado y descartado. No existe API pública con CORS habilitado para precios de combustible por localidad en Argentina. El dataset oficial (Resolución 314/2016, `datos.energia.gob.ar`) son descargas CSV masivas mensuales, no aptas para un sitio estático sin backend. Si en el futuro aparece algo liviano, se podría auto-sugerir precio por provincia.

---

## 9. PWA: instalación y auto-actualización (v3/v4)

- **`manifest.json`**: `name`, `short_name`, `start_url: ./index.html`, `display: standalone`, `background_color: #F2E8CC`, `theme_color: #0a6b3d`, íconos 192/512/512-maskable.
- **`sw.js`** (cache `acq-v5`):
  - `install`: hace `fetch(url, {cache:'reload'})` de cada archivo en `ARCHIVOS` (evita servir versiones cacheadas por el navegador) y los guarda en la cache nueva; luego `self.skipWaiting()`.
  - `activate`: borra caches viejas, `self.clients.claim()`.
  - `fetch`: cache-first con fallback a red.
- **En `index.html`**:
  - Registra `sw.js`, llama `registration.update()` al cargar y cada vez que la pestaña vuelve a foreground (`visibilitychange`).
  - Listener `controllerchange` → `location.reload()` **una sola vez** (flag `yaRecargo`) cuando un SW nuevo toma control. Esto da auto-actualización silenciosa al reabrir la app.
- **Instalación**:
  - `beforeinstallprompt` → muestra `#instalarBanner` (botones "Instalar"/"Ahora no", el segundo se recuerda con `sessionStorage`).
  - Botón persistente `#btnInstalar` en el footer: usa el prompt diferido si existe; en iOS muestra alert con instrucciones "Compartir → Agregar a pantalla de inicio"; se oculta si `matchMedia('(display-mode: standalone)')` o `navigator.standalone`.

### INVARIANTE: checklist para cada versión nueva

1. Incrementar `CACHE` en `sw.js` (`acq-vN`).
2. Si se agregan/quitan archivos, actualizar el array `ARCHIVOS` en `sw.js`.
3. Actualizar "vN · By Meteoro405" en el footer de `index.html`.
4. Si cambia `data.bin`/`ciudades.js`, regenerar con `generar_datos.py` y verificar 0 faltantes / 0 duplicados.

---

## 10. Sistema de diseño / paleta (v5) — **compartida con "De Cuestas, Abras y Quebradas"**

v5 integró visualmente esta app con la paleta de la app hermana **"De Cuestas, Abras y Quebradas"** (`meteoro405.github.io/caminos-argentina`, ver su propio `PROYECTO_REFERENCIA_vXX.md`). Paleta "parch/leather/ink":

| Variable CSS | Modo claro | Modo oscuro | Origen / uso |
|---|---|---|---|
| `--bg` | `#E9DAB4` (**valor con gotero/eyedropper sobre De Cuestas, v7** — el `--parch` puro de DevTools es `#E8D880`, pero hay textura/overlay que aclara el píxel final) | `#1E1008` (ink) | Fondo de página |
| `--card` | `#F2E8CC` (parch-light — antes usado por error como `--bg` en v5) | `#4A1E08` (leather-dk) | Tarjetas/inputs |
| `--tinta` | `#1E1008` (ink) | `#F2E8CC` (parch-light) | Texto principal |
| `--tinta-2` | `#7A5A38` (ink-lt) | `#C8A878` (derivado, sin equivalente directo en De Cuestas) | Texto secundario |
| `--linea` | `rgba(90,58,26,.22)` (border) | `rgba(232,216,128,.16)` | Bordes |
| `--acento` | `#A0552A` (bronze) | `#C8845A` (bronze-lt) | Links, firma, resultado de costo |
| `--acento-claro` | `#C8845A` (bronze-lt) | `#E0AC82` | Hover de acento |
| `--verde-vial` / `--verde-vial-osc` | `#0a6b3d` / `#085530` | `#0e7a47` / `#0a5c36` | **Sin cambios** — color del cartel de ruta, escudo "RN", íconos PWA, highlight de autocompletado |
| `--verde-borde` | `#f4f6f3` | (heredado) | Borde blanco del cartel verde |
| `--amarillo` | `#ffd100` | (heredado) | Aviso de asimetría |

**Tipografías**: `Archivo` (cuerpo), `Saira Condensed` (firma, valores del cartel, "más cercanas" — identidad "señalética vial"), **`Playfair Display`** (nuevo en v5, solo el `<h1>`, para emparentar visualmente con el título serif de De Cuestas).

**Identidad mantenida adrede**: el cartel verde de resultado, el escudo "RN", y el verde de selección en el autocompletado **no cambiaron** — son la identidad propia de "¿A cuánto queda?" (tema "cartel de ruta"), mientras que fondo/tarjetas/texto/acentos ahora son "familia" con De Cuestas (tema "mapa/cuero viejo"). Es la misma lógica que un cartel verde de ruta sobre un mapa de papel.

---

## 11. Historial de versiones (changelog completo)

| Versión | Cambios principales |
|---|---|
| **v1** | Extracción inicial de las matrices km/tiempo desde el PDF (3.726 páginas), desambiguación de 19 grupos de homónimos, generación de `data.bin`+`ciudades.js`, app base: autocompletado, cartel de resultado estilo señalética vial, top-10 cercanas, tema claro/oscuro, formato es-AR, estado en URL (`#o=X&d=Y`). |
| **v2** | Branding: título "¿A cuánto queda?" + línea "By Meteoro405"; pie "vX · By Meteoro405"; primera integración de paleta clara con De Cuestas (bg `#F2E8CC`, card `#FAF4E4`, tinta `#4F3B26` — *luego refinado en v5*). |
| **v3** | PWA instalable: `manifest.json`, `sw.js` (cache `acq-v3`), set de íconos (escudo "RN" verde, 192/512/512-maskable/apple-touch/favicon). Banner de instalación en `beforeinstallprompt` + botón persistente en footer con fallback iOS. |
| **v4** | (1) "Ver en Maps" pasó a modal con iframe embebido + fallback de link directo. (2) "Más cercanas" se oculta al elegir destino válido. (3) Auto-actualización: `sw.js` fetch con `cache:'reload'` + `registration.update()` periódico + reload-on-controllerchange. (4)-(6) Calculadora de costo de combustible (consumo/tipo/precio, persistido en localStorage, integrado a WhatsApp). Investigado y descartado: API de precios de combustible en vivo (no existe opción CORS-friendly para sitio estático). |
| **v5** | Integración visual completa con la paleta "parch/leather/ink" de De Cuestas (modo claro Y oscuro, antes solo claro y con tonos aproximados). Nuevo `--acento`/`--acento-claro` (leather/bronze) para firma, links de costo, hovers. Tipografía Playfair Display en el `<h1>`. Este documento de referencia integral (reemplaza a los `DISTANCIAS_REFERENCIA_v1-4.md` previos, que quedan obsoletos). |
| **v8** | Texto del cartel: `#cRuta` pasó de `"Desde [origen]"` a `"Desde [origen] hasta"`, para que se lea como una sola frase junto con `#cDestino` ("Desde San Carlos de Bariloche hasta **EL CALAFATE**"). Confirmado por Ariel: el `--bg` de v7 (`#E9DAB4`) "casi lo mismo" que el de De Cuestas con gotero (`#EADCB7`) — diferencia atribuible a la captura, **paleta considerada cerrada**. |
| **v7** | Segunda corrección de `--bg`: comparando con gotero (no DevTools) sobre capturas alineadas de ambas apps, el píxel real de De Cuestas es `#E9DAB4`, no `#E8D880`. Se actualizó `--bg` y `manifest.json.background_color` a `#E9DAB4`. Hipótesis: textura/overlay de papel sobre `--parch` que aclara el resultado final. |
| **v6** | **Corrección de paleta**: Ariel comparó lado a lado con captura + DevTools de De Cuestas y se detectó que los valores de v5 eran de una versión anterior del .md, no los reales. Valores verificados por inspección del `body` en `meteoro405.github.io/caminos-argentina`: `--bg` real es `#E8D880` (parch, más dorado/saturado — en v5 usábamos `#F2E8CC`, que en realidad es `--parch-light`, el color de **tarjetas**). Actualizados también `--tinta` (`#1E1008`, antes `#2A1A0A`), `--tinta-2` (`#7A5A38`, antes `#8A6A50`) y `--linea` (`rgba(90,58,26,.22)`, antes `rgba(160,85,42,.18)`). `--acento`/`--acento-claro` (bronze `#A0552A` / bronze-lt `#C8845A`) no cambiaron, coinciden. Modo oscuro derivado de `--ink`/`--leather-dk` (De Cuestas no tiene modo oscuro de referencia). `manifest.json` → `background_color: #E8D880`. |

---

## 12. Problemas conocidos / best-effort

- **`--bg` es un valor "ojo" (v7), no una variable CSS de De Cuestas**: `#E9DAB4` viene de samplear con gotero el píxel final renderizado, porque el `--parch` (`#E8D880`) que reporta DevTools no coincide con el píxel real — De Cuestas probablemente tiene una textura/gradiente de papel sobre el color sólido que no estamos replicando. Si en algún momento se agrega esa textura a "¿A cuánto queda?", reconsiderar si `--bg` debería volver a `#E8D880`.

- **Paleta compartida**: los valores de la sección 10 fueron corregidos en v6 tras inspección directa del DOM de De Cuestas (DevTools). Si De Cuestas cambia su paleta en el futuro, esta tabla puede volver a desactualizarse — ante cualquier duda visual, lo más confiable es inspeccionar el `:root` y el `body` computado de `meteoro405.github.io/caminos-argentina` directamente.

- **Modal de Maps**: el embed `maps.google.com/maps?...&output=embed` es un truco no oficial. Si Google lo bloquea, el usuario ve el iframe vacío pero el botón "Abrir en Google Maps" (fallback) siempre funciona. No reportado como roto aún, pero no probado a fondo.
- **Sin precio de combustible en vivo**: por diseño (ver sección 8), es manual.
- **GNC**: el consumo se trata genéricamente como "unidades cada 100 km" sin distinción real de eficiencia; es una aproximación aceptada.
- **wkhtmltoimage / testing visual**: en este entorno de desarrollo, `wkhtmltoimage` no puede acceder a `localhost` vía HTTP (sandbox de red) ni hacer `fetch()` de `data.bin` vía `file://` (CORS). Los previews de v5 se generaron sin datos cargados (solo se ve el layout vacío) — la paleta se validó visualmente así, pero el cartel de resultado con datos reales no se renderizó en este entorno. Si hace falta revalidar visualmente, conviene pedirle una captura a Ariel o usar el mismo método con un servidor que sirva por `file://` con CORS deshabilitado, o instalar un navegador headless con red habilitada.

---

## 13. Integración con el proyecto más grande ("ecosistema Meteoro405")

Ariel mantiene en paralelo (en otros chats):

- **"De Cuestas, Abras y Quebradas"** (`meteoro405.github.io/caminos-argentina`, v100+): PWA guía de 125+ caminos escénicos argentinos. Es la fuente de la paleta "parch/leather/ink" adoptada en v5. Su propio doc de referencia es `PROYECTO_REFERENCIA_vXX.md`.
- **"MiGarage"** (`meteoro405.github.io/mi-auto/`): PWA de mantenimiento de vehículos, localStorage `mg2_*`.

### Cómo encaja "¿A cuánto queda?" como módulo

- **Branding compartido**: "By Meteoro405" en título y pie, ahora con la misma paleta de colores y emparentamiento tipográfico (Playfair Display) que De Cuestas.
- **Estado en URL**: `#o=<índiceOrigen>&d=<índiceDestino>` — cualquier otra app puede generar un deep-link a una consulta específica (por ejemplo, desde una ficha de ruta en De Cuestas: "¿A cuánto queda desde acá hasta [ciudad]?" → link a `distancias-Argentinas/#o=X&d=Y`). Los índices son posiciones en `CIUDADES` (array de `ciudades.js`), estables mientras no se regenere `data.bin`.
- **Cruce pendiente (idea, no implementada)**: si De Cuestas conociera el índice de `CIUDADES` más cercano a cada extremo de un camino, podría linkear directo a "¿A cuánto queda?" con esos índices. Requeriría mapear las ~135 rutas de De Cuestas contra las 751 ciudades de esta app (por nombre o coordenadas — De Cuestas ya tiene coordenadas vía `mapsrc()`/iframes, esta app no).
- **Convención de versionado**: igual que en De Cuestas — cada cambio incrementa la versión (`vN`), se actualiza el cache de `sw.js`, y se mantiene un `DISTANCIAS_REFERENCIA_vN.md` único y autocontenido (este archivo reemplaza a los anteriores).

---

## 14. Backlog / ideas pendientes

- Coordenadas lat/lon por ciudad (vía API Georef de datos.gob.ar, gratuita, sin key, con `centroide` por localidad — ya investigada y confirmada viable) para: distancia en línea recta vs. por ruta, mapa con ambos puntos, cruce geográfico con De Cuestas.
- Verificar en producción cómo se comporta el modal de Maps en distintos navegadores/celulares.
- Posible: sugerencia de precio de combustible por provincia si aparece alguna fuente de datos liviana en el futuro.

---

## 15. Cómo desplegar

1. Todos los archivos de `Distancias_v5/` van a la raíz del repo `meteoro405/distancias-Argentina(s)` (sin subcarpetas).
2. GitHub Pages debe estar activo: Settings → Pages → Source: rama `main`, carpeta `/ (root)`.
3. URL resultante: `https://meteoro405.github.io/distancias-Argentinas/`.
4. Tarda 1-2 min en propagarse tras el primer deploy o cambios de configuración de Pages.
