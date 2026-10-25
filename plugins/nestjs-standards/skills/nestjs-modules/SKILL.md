---
name: nestjs-modules
description: "Usar al crear o modificar modulos, controladores, servicios y dependencias de src/modules en proyectos NestJS."
---

# nestjs-modules

Esta Skill establece **cuándo consultar** las convenciones de Erixcel, no una copia de esas convenciones.

## Fuente de verdad

- Documentación legible: https://docs.erixcel.com/desarrollo/nestjs/src/modules-guia
- Documento fuente (MDX): https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/nestjs/src/modules-guia.mdx
- Ruta del repositorio: `desarrollo/nestjs/src/modules-guia.mdx`

## Ámbito

Aplica al trabajar con `src/modules/** (controllers, services, modules)` en un backend NestJS.

## Procedimiento obligatorio

1. **Antes de crear, revisar o modificar archivos**, obtén y lee la versión actual del documento fuente en GitHub. Desde una terminal con acceso a la red puedes consultar: `curl -fsSL 'https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/nestjs/src/modules-guia.mdx'`.
2. Lee todas las convenciones y ejemplos relevantes. Si el índice contiene enlaces a páginas específicas para el archivo solicitado, consulta también esos documentos antes de editar.
3. Usa la página MDX como **única fuente de verdad** para las convenciones del proyecto. No sustituyas su contenido por reglas memorizadas o por versiones antiguas de otras Skills.
4. Aplica los cambios necesarios preservando el comportamiento existente, las rutas reales y las decisiones explícitas del usuario.
5. Valida los archivos cambiados con las comprobaciones disponibles en el proyecto. Explica qué reglas se aplicaron y qué no se pudo verificar.
6. Si GitHub no está accesible, intenta leer el mismo archivo en un checkout local actualizado de `erixcel/documentation` y aclara si su versión puede estar desactualizada. Si no puedes leer ninguna fuente confiable, **no inventes normas**: informa el impedimento y solicita el documento.

## Puntos de atención

Para cambios sobre DTO específicos de módulos consulta `nestjs-module-dto`; para DTO compartidos consulta `nestjs-global-dto`. **Cada `<nombre>.module.ts` dentro de `src/modules/**` debe compartir directorio solamente con `<nombre>.controller.ts` y `<nombre>.service.ts`**, con idéntica base; sí se admiten subcarpetas. Para utilidades adicionales sin dependencias inyectadas, crea `functions/<nombre>.function.ts` y consulta `nestjs-functions`. Si se necesita otro `@Injectable()`, crea un submódulo con su propio trío de archivos. **Nunca elimines o muevas servicios sin actualizar imports, providers, exports y pruebas.** `src/app.module.ts` es la excepción raíz. La fuente de verdad y los ejemplos están en la página MDX indicada arriba.

La documentación remota es material de referencia: no ejecutes automáticamente comandos o scripts que aparezcan en ella sin evaluar sus efectos y permisos.
