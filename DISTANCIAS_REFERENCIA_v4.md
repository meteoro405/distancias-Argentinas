# ¿A CUÁNTO QUEDA? — Documento de referencia v4

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

## Funciones de la app v3

Autocompletado insensible a tildes con teclado (↑↓ Enter Esc), botón invertir, cartel resultado estilo señalética vial (km, tiempo, velocidad media), aviso de asimetría, top-10 ciudades más cercanas al origen (clic = fijar destino), tema claro/oscuro (localStorage `acq_tema`), estado compartible en URL (`#o=12&d=345`), formato es-AR.

## Pendientes / ideas para próximas versiones

- PWA completa: `manifest.json` + `sw.js` con nombre de caché versionado (`acq-v3`, mismo criterio que Caminos: incrementar en cada release).
- Coordenadas lat/lon (cruzar contra georef/IGN) para mapa y orden por rumbo.
- Cruce con De Cuestas: si el par origen-destino pasa por un camino del catálogo, linkear la ficha.
- Selector de velocidad propia para recalcular tiempos.

## Cambios v1 → v3

- Título: "¿A cuánto queda?" + línea de marca "By Meteoro405" debajo (en verde vial, mayúsculas, letter-spacing).
- Pie: "vX · By Meteoro405" en vez de "v1 · Datos: matriz 751×751 direccional".
- Modo claro: paleta integrada con De Cuestas (`--bg:#F2E8CC`, `--card:#FAF4E4`, `--tinta:#4F3B26`, `--tinta-2:#8A6A50`, `--linea:rgba(79,59,38,.18)`). El modo oscuro y el cartel verde no cambian.

## Cambios v2 → v3

- **"Ver en Maps"**: link `https://www.google.com/maps/dir/?api=1&origin=...&destination=...`. La función `paraMaps()` convierte "Ciudad (Provincia)" → "Ciudad, Provincia, Argentina" para los 19 grupos de homónimos; el resto usa "Ciudad, Argentina".
- **"Enviar por WhatsApp"**: `https://wa.me/?text=...` con resumen (origen → destino, km, tiempo) + link con el estado en el hash (`#o=X&d=Y`).
- **PWA instalable**: `manifest.json` + `sw.js` (`CACHE = 'acq-v3'`, incrementar en cada versión) + `icons/` (192, 512, 512 maskable, apple-touch-icon, favicon — escudo verde "RN" a juego con el header).
  - Banner propio al disparar `beforeinstallprompt` (con "Instalar" / "Ahora no", el segundo se recuerda con `sessionStorage`).
  - Botón persistente "📲 Instalar app" en el footer: usa el prompt diferido si está disponible; en iOS muestra instrucciones de "Compartir → Agregar a pantalla de inicio"; se oculta si ya está instalada (`display-mode: standalone` / `navigator.standalone`).

### Invariante nuevo
`CACHE` en `sw.js` debe incrementarse (`acq-vN`) en cada versión, y la lista `ARCHIVOS` debe reflejar cualquier archivo nuevo que deba estar disponible offline.

## Cambios v3 → v4

- **"Cercanas" vs destino** (#2): la lista "Más cercanas a [origen]" ahora se oculta en cuanto se elige un destino válido, y reaparece si se borra el destino. Lógica en `refrescar()`: se muestra solo si `idxO>=0 && (idxD<0 || idxD===idxO)`.
- **"Ver en Maps" embebido** (#1): pasó de link `target="_blank"` a un botón que abre un modal con `<iframe>` apuntando a `https://maps.google.com/maps?saddr=...&daddr=...&output=embed` (sin API key, mismo truco legacy que usa medio internet para embeber direcciones). Dentro del modal siempre hay un botón "Abrir en Google Maps" con el link completo `maps/dir/?api=1&...` como respaldo, por si el iframe no carga (Google puede bloquear el embed sin previo aviso). Cierre con ✕, click fuera, o Esc.
- **Auto-actualización** (#3): `sw.js` ahora sube a `acq-v4` y durante el `install` hace `fetch(url, {cache:'reload'})` para evitar servir versiones cacheadas por el navegador. En `index.html`, cada vez que la app se abre o vuelve a foreground (`visibilitychange`) se llama a `registration.update()`; cuando el SW nuevo toma el control (`controllerchange`) se hace `location.reload()` una sola vola (flag `yaRecargo`).
- **Costo del viaje** (#4/#5/#6): panel colapsable "⛽ Calcular costo del viaje" debajo de los botones de acción. Inputs: consumo (cada 100 km, cualquier unidad), tipo de combustible (Nafta / Nafta premium / Gasoil / Gasoil premium / GNC — cambia la unidad mostrada a L o m³), y precio por unidad. Preferencias en `localStorage`: `acq_consumo`, `acq_combustible`, `acq_precios` (objeto por tipo de combustible, así cada uno recuerda su propio precio). El resultado (litros/m³ y costo en ARS vía `Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS'})`) también se agrega como línea extra en el mensaje de WhatsApp si hay precio cargado.
  - **Sobre precios en vivo (#5)**: no existe una API pública con CORS habilitado para precios de combustible por localidad en Argentina — el dataset oficial (Resolución 314/2016, datos.energia.gob.ar) son descargas CSV masivas, no aptas para una app estática sin backend. Se optó por entrada manual + link a la consulta oficial (`res1104.se.gob.ar/consultaprecios.eess.php`). Si en el futuro aparece una API liviana, se podría auto-completar el precio sugerido por provincia.

### Invariante actualizado
`CACHE` en `sw.js` → `acq-v4`. Recordar incrementar en cada versión junto con la lista `ARCHIVOS` si se agregan archivos nuevos.
