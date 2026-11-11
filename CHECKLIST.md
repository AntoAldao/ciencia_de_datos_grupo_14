# Checklist – Entrega 4

Todo lo que pide la consigna ([docs/consigna.md](docs/consigna.md)), en orden de trabajo.
Se marca con `[x]` a medida que se resuelve. Fecha de la exposición: **25 de noviembre**.

## 0. Base del proyecto

- [x] Repositorio creado con README, consigna y guía de ramas
- [x] Pipeline de la Entrega 1 dentro del repo (`pipeline/`)
- [x] Notebooks de las Entregas 2 y 3 dentro del repo (`notebooks/`)
- [x] Dataset en `data/`
- [x] Esqueleto de la app (`app.py`) y `requirements.txt`
- [ ] Remoto de GitHub configurado y rama subida
- [ ] Todos los integrantes pueden clonar y correr la app

## 1. Portada: El proyecto

- [x] Oración central: *«Más datos le ganan a la grilla, pero los abandonos esconden gran parte de esa ventaja.»*
- [x] Tres números que la sostienen (3,29 vs 3,49 · 10 % a 17 % · 1,73 vs 1,96)
- [x] Pregunta del proyecto como título de la app
- [ ] Los tres números calculados desde el código, no escritos a mano
- [ ] Confirmar los tres números contra la salida del notebook

## 2. Tallo – Los datos (cierra la Entrega 1)

- [x] Título que afirma algo de los datos
- [x] Gráfico en Altair que lo prueba
- [x] Unas pocas líneas que dicen qué mirar en el gráfico
- [ ] «Cómo lo sabemos» (cerrado por defecto) con:
  - [ ] De dónde salen los datos y cómo se obtienen (pipeline)
  - [ ] Fecha de los datos
  - [ ] Qué es una fila
  - [ ] Qué se filtró, paso por paso, con cuántas filas quedaron en cada paso y por qué
  - [ ] Qué columnas se descartaron por fuga

## 3. Tallo – Lo que encontramos (cierra la Entrega 2)

- [ ] Título que afirma el hallazgo principal del análisis
- [ ] Gráfico en Altair que lo prueba
- [ ] Unas pocas líneas que dicen qué mirar en el gráfico
- [ ] «Cómo lo sabemos» (cerrado por defecto) con:
  - [ ] Una hipótesis que se sostuvo, con su número
  - [ ] Una hipótesis que no se sostuvo, con su número
  - [ ] Cómo se construyó el gráfico, si hubo una transformación no obvia

## 4. Tallo – El modelo (cierra la Entrega 3)

- [ ] Título que afirma qué logró el modelo
- [ ] Gráfico en Altair que lo prueba
- [ ] Unas pocas líneas que dicen qué mirar en el gráfico
- [ ] «Cómo lo sabemos» (cerrado por defecto) con:
  - [ ] La métrica y por qué
  - [ ] El piso
  - [ ] Cómo se armó la validación
  - [ ] Tabla de comparación con media y desvío
  - [ ] Ajuste del modelo elegido
  - [ ] Resultado en el test
  - [ ] Dónde se equivoca
  - [ ] En qué se apoya
- [ ] El modelo de la app coincide con el del notebook (misma semilla)

## 5. Copa – Explorá

- [ ] Panorama: todos los datos en una vista
- [ ] Al menos dos controles que achican el universo y cambian el gráfico
- [ ] Detalle a pedido (mouse o selección) con lo que dijo el modelo sobre ese caso
- [ ] Predicciones del modelo calculadas para todos los casos

## 6. Copa – Probá el modelo

- [ ] El usuario carga un caso nuevo y ve qué predice el modelo
- [ ] Aviso (o bloqueo) cuando carga valores que el modelo nunca vio
- [ ] Decidir cómo se muestra un puesto, ya que el modelo ordena dentro de una carrera
- [ ] Clases propias del notebook (`Desgaste`, `PesarDistanciaLider`, `Interacciones`) disponibles para cargar el modelo
- [ ] Qué pasa si el usuario carga un caso raro: probado

## 7. Gráficos

- [ ] Todos hechos con Altair
- [ ] Cada uno se puede leer componente por componente: datos, mapeo, marca, transformaciones y escalas
- [ ] Colores, categorías y escalas significan lo mismo en toda la aplicación
- [ ] Cada gráfico del tallo dice lo suyo sin tocarlo
- [ ] La copa es interactiva

## 8. Proyecto integrado

- [ ] `build_app.py`: toma los datos del pipeline, carga o entrena el modelo con la misma semilla y genera la app
- [ ] Si los datos se actualizan, correr `build_app.py` actualiza la app
- [ ] Lo que muestra la app coincide con lo que da el notebook
- [ ] README que permite a otra persona regenerar todo

## 9. Publicación

- [ ] Elegir la forma: Streamlit Community Cloud (o HTML en GitHub Pages)
- [ ] App publicada en una URL pública
- [ ] URL probada desde otra computadora, sin instalar nada
- [ ] Sin errores al abrirla ni al usarla
- [ ] Plan para que siga andando hasta la exposición

## 10. Antes de la entrega

- [ ] Lo marcado por el profesor en la Entrega 3: resuelto o explicado (no hubo correcciones)
- [ ] Dos oraciones sobre qué cambió del modelo desde la Entrega 3
- [ ] URL abierta en el navegador antes de entrar
- [ ] Repositorio abierto en GitHub con README
- [ ] Ensayo del recorrido de 25 minutos

## 11. Cada integrante tiene que saber explicar (evaluación individual)

- [ ] Por qué cada título del tallo afirma lo que afirma y qué número lo sostiene
- [ ] Un gráfico de la app, componente por componente
- [ ] Una decisión de diseño que cambiamos: qué tenía la primera versión y por qué no funcionaba
- [ ] Qué componente del gráfico toca cada control de la copa
- [ ] Cómo llega el modelo a la aplicación y qué pasa con un caso raro
- [ ] Cómo se regenera la app desde el repositorio si cambian los datos

## Errores a evitar

- [ ] No es un tablero sin historia: cada sección tiene un mensaje
- [ ] No es el notebook con otra ropa: lo técnico va en los «Cómo lo sabemos»
- [ ] No corre solo en una notebook: la URL funciona desde afuera
- [ ] No habla uno solo: todos conocen todas las partes
