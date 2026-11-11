# Cómo trabajamos

`main` siempre tiene que andar: es lo que se publica. Nadie commitea directo ahí.

## Flujo

```bash
git checkout main
git pull
git checkout -b <nombre>/<tema>      # por ejemplo: paulina/seccion-datos
# ... trabajar, probar ...
git add <archivos>
git commit -m "Describe qué cambió"
git push -u origin <nombre>/<tema>
```

Después se abre un pull request hacia `main` y otra persona del grupo lo revisa antes de mergear.

## Reglas

- Una rama por tema, chica y de corta vida. Mejor varios cambios chicos que uno enorme.
- Antes de empezar, `git pull` en `main`. Si `main` cambió, traelo a tu rama (`git merge main`).
- Los notebooks se pisan fácil al mergear: si dos personas tocan el mismo, avisen antes.
- No subir el `.venv`, claves ni archivos pesados nuevos sin avisar.
- Todos tienen que poder explicar cualquier parte de la app: la evaluación es individual.

## Sugerencia de reparto inicial

Es solo un punto de partida, el grupo decide.

| Tema | Qué incluye |
|---|---|
| Portada y tallo: Los datos | Título, gráfico y «Cómo lo sabemos» (Entrega 1) |
| Tallo: Lo que encontramos | Título, gráfico y «Cómo lo sabemos» (Entrega 2) |
| Tallo: El modelo | Título, gráfico y «Cómo lo sabemos» (Entrega 3) |
| Copa: Explorá | Panorama, filtros y detalle con la predicción del modelo |
| Copa: Probá el modelo | Formulario de caso nuevo y aviso de valores fuera de rango |
| Infraestructura | `build_app.py`, README, publicación y prueba desde otra computadora |
