# CestaSmart 2.7 — multi-query + equivalencias ampliadas

## Mercadona
Cada producto se busca con varias expresiones de la misma categoría:
- detergente 40 lavados -> detergente lavadora / detergente ropa / detergente
- papel higiénico 12 rollos -> papel higiénico / papel WC / rollos papel higiénico
- huevos -> huevos frescos / huevos
- yogur -> yogur natural / yogur

Si el catálogo no incluye la cantidad en el título, detergente y papel pueden entrar como
PROBABLE siempre que la categoría sea segura y no haya términos incompatibles.

Se mantienen exclusiones duras:
- amoníaco/lejía/desengrasante no son detergente de lavadora
- papel húmedo/toallitas no son rollos de papel higiénico
- pasta/nidos/chocolate/etc. no son huevos

## Equivalencia funcional
Tolerancias más prácticas:
- lavados: mínimo 70% de proximidad; siempre normalizado €/lavado cuando se conoce
- rollos/hojas: mínimo 50% y se corrige por unidades equivalentes
- peso/volumen: mínimo 80%

## Lidl
Usa ambos caminos:
1. `search`
2. `batch --candidates 25`

y acepta más variantes del JSON del conector.

Diagnóstico:
`/api/diagnose/lidl`

Debe mostrar `search_ok` y `batch_ok`, además del stdout/stderr.
