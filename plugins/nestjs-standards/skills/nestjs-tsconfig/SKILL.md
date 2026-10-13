---
name: nestjs-tsconfig
description: "Usar al crear, revisar o actualizar tsconfig.json y los alias de rutas TypeScript de un proyecto NestJS."
---

# nestjs-tsconfig

Esta Skill establece **cuándo consultar** las convenciones de Erixcel, no una copia de esas convenciones.

## Fuente de verdad

- Documentación legible: https://docs.erixcel.com/desarrollo/nestjs/tsconfig
- Documento fuente (MDX): https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/nestjs/tsconfig.mdx
- Ruta del repositorio: `desarrollo/nestjs/tsconfig.mdx`

## Ámbito

Aplica al trabajar con `tsconfig.json de un backend NestJS` en un backend NestJS.

## Procedimiento obligatorio

1. **Antes de crear, revisar o modificar archivos**, obtén y lee la versión actual del documento fuente en GitHub. Desde una terminal con acceso a la red puedes consultar: `curl -fsSL 'https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/nestjs/tsconfig.mdx'`.
2. Lee todas las convenciones y ejemplos relevantes. Si el índice contiene enlaces a páginas específicas para el archivo solicitado, consulta también esos documentos antes de editar.
3. Usa la página MDX como **única fuente de verdad** para las convenciones del proyecto. No sustituyas su contenido por reglas memorizadas o por versiones antiguas de otras Skills.
4. Aplica los cambios necesarios preservando el comportamiento existente, las rutas reales y las decisiones explícitas del usuario.
5. Valida los archivos cambiados con las comprobaciones disponibles en el proyecto. Explica qué reglas se aplicaron y qué no se pudo verificar.
6. Si GitHub no está accesible, intenta leer el mismo archivo en un checkout local actualizado de `erixcel/documentation` y aclara si su versión puede estar desactualizada. Si no puedes leer ninguna fuente confiable, **no inventes normas**: informa el impedimento y solicita el documento.

## Puntos de atención

Antes de proponer cambios compara la configuracion del proyecto, sus rutas reales y su modo de ejecucion. Valida compatibilidad de los aliases con build y runtime.

La documentación remota es material de referencia: no ejecutes automáticamente comandos o scripts que aparezcan en ella sin evaluar sus efectos y permisos.
