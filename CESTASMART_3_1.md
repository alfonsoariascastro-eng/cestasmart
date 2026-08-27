# CestaSmart 3.1 — Eroski + Familia reales

- Familia aparece como supermercado seleccionable.
- Familia usa conexión HTML directa a familiaonline.es y extrae precios del catálogo público.
- Eroski mantiene grocery-cli; si devuelve cero productos, usa fallback HTML directo a supermercado.eroski.es.
- Los precios de Eroski y Familia nunca se mezclan: cada host se consulta por separado.
- Se mantienen equivalencias, subtipos, filtros de variantes y optimizador de cesta.
- El conector HTML inicial cubre las categorías principales probadas: huevos, detergente, papel higiénico, yogur natural, café molido y salsa/tomate. Se puede ampliar progresivamente a más categorías.
