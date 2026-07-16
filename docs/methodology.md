# Metodología

Yo trabajo con un flujo iterativo de pequeños incrementos verificables:

1. Yo defino el riesgo, el presupuesto de latencia y el criterio de aceptación.
2. Yo escribo o actualizo una prueba del dominio.
3. Yo implemento detrás de un puerto hexagonal.
4. Yo ejecuto formato, análisis estático, pruebas y compilación.
5. Yo mido en hardware y comparo p50/p95 con el presupuesto.
6. Yo registro una ADR cuando cambio una decisión estructural.

Yo aplico SOLID de esta forma: mantengo una responsabilidad por clase, extiendo mediante nuevos adaptadores, conservo sustitución entre proveedores, diseño puertos pequeños y hago que las dependencias apunten al dominio.

Yo uso trunk-based development con ramas breves, PR obligatorio y `main` desplegable. Yo versiono con SemVer y mantengo cada release reproducible mediante tags y artefactos CI.

