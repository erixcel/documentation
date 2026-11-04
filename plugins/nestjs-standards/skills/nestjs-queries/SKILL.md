---
name: nestjs-queries
description: "Usar al crear, modificar o revisar consultas de base de datos en src/queries/** y archivos *.query.ts o *-join.query.ts de proyectos Erixcel NestJS."
---

# nestjs-queries

## Fuente de verdad

- Guía de Queries: https://docs.erixcel.com/desarrollo/nestjs/src/queries-guia
- MDX fuente: https://raw.githubusercontent.com/erixcel/documentation/main/desarrollo/nestjs/src/queries-guia.mdx
- Contexto de base de datos: https://docs.erixcel.com/desarrollo/nestjs/src/db/index
- Validación publicada: `plugins/nestjs-standards/hooks/validate-query.py` (**Query Validator**, ya existente).

## Ámbito

Aplica a `src/queries/**`, incluidas las consultas `*.query.ts` y `*-join.query.ts`, y cuando un service necesita operaciones de datos encapsuladas en una Query. Es una Skill **independiente de React**. No modifica tablas, migrations ni seeds sin una solicitud explícita.

## Procedimiento obligatorio

1. Lee la versión actual de `desarrollo/nestjs/src/queries-guia.mdx` antes de decidir la organización de queries. Si no está disponible, usa una copia local actualizada y declara la limitación; no inventes convenciones.
2. Identifica la tabla base y todas las relaciones que necesita la consulta; consulta los archivos reales `src/db/tables/*.table.ts` para comprobar los nombres, columnas y tipos.
3. Crea una carpeta por tabla, `src/queries/<tabla>/`, con **como máximo** `<tabla>.query.ts` y `<tabla>-join.query.ts`, solo los archivos necesarios.
4. Implementa `*.query.ts` para operaciones atómicas **de una sola tabla**, con `SELECT`, `INSERT`, `UPDATE` y `DELETE` cuando corresponda. No importes otras tablas ni uses JOIN aquí.
5. Implementa `*-join.query.ts` para consultas con relaciones: **solo lectura/SELECT**, con JOIN cuando sea necesario. Nunca incluyas `INSERT`, `UPDATE` ni `DELETE`.
6. En ambos archivos permite **solamente imports, decoradores de clase y exactamente una clase de Query a nivel superior**. No declares `const`, `let`, `var`, `type`, `interface`, funciones auxiliares ni otras clases a nivel de módulo. Las variables locales **dentro de los métodos** sí son válidas; configuraciones compartidas van en propiedades o métodos privados de la clase.
7. Usa las clases `<Tabla>Query` y `<Tabla>JoinQuery`, según corresponda. Respeta la inyección de dependencias de NestJS y la conexión Drizzle real; no traslades operaciones SQL directas a services.
8. Ten presente que `*.table.ts` **no exporta tipos independientes** por la convención actual de Erixcel. Si necesitas la forma de una fila o de inserción, utiliza `typeof tabla.$inferSelect` / `typeof tabla.$inferInsert` en posiciones de tipo o contratos externos; no añadas `export type` al archivo de tabla.
9. Preserva comportamiento, transacciones, condiciones de filtrado, borrado lógico, paginación y reglas de seguridad. Valida imports y tipos con el compilador/lint disponibles y ejecuta **Query Validator** (Hook Stop o `python3 hooks/validate-query.py --check <archivo>`). Corre las pruebas existentes cuando sea posible.

## Ejemplos de decisión

- `users.query.ts`: `database.select().from(users)`, `database.update(users)`, etc., sin JOIN ni otras tablas.
- `users-join.query.ts`: `database.select().from(users).leftJoin(roles, ...)`, exclusivamente de lectura.
- Una lista de `fields` usada por varios métodos se guarda como miembro de la clase o dentro de los propios métodos, **nunca como constante independiente al nivel superior**.

La Skill guía la generación; **el Query Validator sigue siendo el mismo Hook**. Sus chequeos estáticos son heurísticos y no sustituyen pruebas de integración ni análisis semántico completo.
