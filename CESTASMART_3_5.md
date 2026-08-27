# CestaSmart 3.5 — comparabilidad estricta

## Regla principal
El objetivo no es encontrar la cesta con menor suma parcial, sino la cesta completa más barata
con productos realmente equivalentes.

## Cambios

### Detergente
- Si el usuario escribe solo "detergente", por defecto se usa detergente EN POLVO.
- Líquido, cápsulas/pastillas o lavado a mano solo entran si el usuario los pide.
- Variantes especiales (prendas delicadas, ropa oscura, bebé, etc.) no entran salvo petición.

### Huevos
- Se permite equivalencia por packs: por ejemplo 30 uds pueden cubrir una petición de 12 uds,
  usando el coste equivalente correspondiente.
- Si se pide campero/ecológico/suelo o calibre específico, debe respetarse.

### Ranking
- Solo una cesta con 0 líneas sin resolver puede competir por el primer puesto.
- Las cestas incompletas se muestran, pero quedan fuera del ranking.
- El optimizador trabaja únicamente con cestas completas.

### Objetivo
Que cualquier diferencia de precio entre supermercados sea consecuencia de precios reales,
no de productos ausentes, formatos distintos ni cantidades no comparables.
