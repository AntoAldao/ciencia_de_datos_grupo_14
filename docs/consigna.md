# Entrega 4 – La aplicación final

Resumen de la consigna del profesor. La pregunta de esta entrega: ¿alguien que no estuvo en el
proyecto puede entender lo que encontramos, creernos, y después hacerle sus propias preguntas a los datos?

Se entrega una **aplicación web publicada en una URL**, la misma que se muestra en la exposición final
del **25 de noviembre**. Tiene que ser **nuestra**: nuestra pregunta, nuestros datos y nuestros hallazgos.

## La forma: una copa de martini

| Parte | Sección | Qué tiene | Cierra |
|---|---|---|---|
| Portada | El proyecto | La pregunta, la idea central en una oración con sujeto y verbo, y tres números que la sostienen | La definición |
| Tallo | Los datos | Un título que afirma algo de los datos y un gráfico que lo muestra | Entrega 1 |
| Tallo | Lo que encontramos | Un título que afirma el hallazgo principal y un gráfico que lo muestra | Entrega 2 |
| Tallo | El modelo | Un título que afirma qué logró el modelo y un gráfico que lo muestra | Entrega 3 |
| Copa | Explorá | Los datos con el resultado del modelo, para recorrerlos | Todas |
| Copa | Probá el modelo | El usuario carga un caso nuevo y ve qué dice el modelo | Entrega 3 |

## El tallo: cada sección, un hallazgo

Cada sección del tallo tiene tres partes:

1. **Un título que afirma.** No «Distribución de los roles», sino una frase con una afirmación.
2. **Un gráfico que lo prueba**, y unas pocas líneas que dicen qué mirar.
3. **«Cómo lo sabemos»**: un desplegable, cerrado por defecto, con la evidencia técnica.

Qué va en cada «Cómo lo sabemos»:

- **Los datos:** de dónde salen (pipeline y fecha), qué es una fila, qué se filtró paso a paso con
  cuántas filas quedaron y por qué, y qué columnas se descartaron por fuga.
- **Lo que encontramos:** una hipótesis que se sostuvo y una que no, cada una con su número, y cómo se
  construyó el gráfico si hubo una transformación no obvia.
- **El modelo:** la métrica y por qué, el piso, cómo se armó la validación, la tabla de comparación con
  media y desvío, el ajuste del elegido, el resultado en el test, dónde se equivoca y en qué se apoya.

## La copa: lo que pregunta el usuario

**Explorá**, de lo general a lo particular:

- Un **panorama** con todos los datos en una vista.
- **Zoom y filtro:** al menos dos controles que cambien lo que muestra el gráfico.
- **Detalle a pedido:** la información de cada caso, incluido lo que dijo el modelo.

**Probá el modelo:** el usuario carga los valores de un caso nuevo y ve la predicción. No puede cargar
valores que el modelo nunca vio, o la aplicación le avisa cuando lo hace.

## Los gráficos

- Hechos con **Altair**. Cada uno tiene que poder leerse componente por componente: datos, mapeo, marca,
  transformaciones y escalas.
- Los colores, las categorías y las escalas significan **lo mismo en toda la aplicación**.
- La copa es interactiva. Cada gráfico del tallo tiene que decir lo suyo sin que nadie lo toque.

## Proyecto integrado

- Repositorio en GitHub con el código del pipeline, del análisis y del modelo, y un README que explique
  cómo se corre todo.
- Un script (`build_app.py`) que toma los datos del pipeline, carga o entrena el modelo con la misma
  semilla y genera la aplicación. Si los datos se actualizan, correrlo de nuevo actualiza la app.
- Lo que muestra la aplicación tiene que **coincidir con el notebook**.

## Qué hay que traer el día de la entrega

- La **URL pública ya abierta** en el navegador, probada desde otra computadora.
- El repositorio abierto en GitHub, con README.
- Lo marcado en la Entrega 3, resuelto o explicado.

## Los 25 minutos

| Min. | Momento | Qué pasa |
|---|---|---|
| 0–2 | Qué cambió | Qué se corrigió del modelo desde la Entrega 3 |
| 2–10 | El tallo | Se recorre la app de la portada al modelo, abriendo los «Cómo lo sabemos» |
| 10–15 | La copa | El docente explora y prueba el modelo con un caso propio |
| 15–22 | Preguntas dirigidas | Preguntas a integrantes puntuales, sobre la app o el repositorio |
| 22–25 | Devolución | Qué está bien y qué corregir antes de la exposición final |

## Lo que hay que saber explicar (la evaluación es individual)

- Por qué cada título del tallo afirma lo que afirma y qué número lo sostiene.
- Un gráfico de la app, componente por componente.
- Una decisión de diseño que cambiamos y por qué.
- Qué componente del gráfico toca cada control de la copa.
- Cómo llega el modelo a la aplicación y qué pasa si el usuario carga un caso raro.
- Cómo se regenera la aplicación desde el repositorio si cambian los datos.

## Cómo se aprueba

- La app abre en su URL pública y funciona sin errores.
- Portada con la oración y tres secciones del tallo completas.
- La copa: un panorama, al menos dos controles que cambian el gráfico, detalle con el resultado del
  modelo y una forma de probar el modelo.
- Gráficos con Altair que el grupo sabe leer.
- La app coincide con el notebook y el README permite regenerarla.
- Las respuestas no vienen de una sola persona.

## Errores a evitar

- **El tablero sin historia:** muchos filtros y gráficos y ninguna conclusión.
- **El notebook con otra ropa:** copiar las celdas del análisis. Lo técnico va en los «Cómo lo sabemos».
- **La app que solo corre en una notebook:** publicar con tiempo y probar desde otra computadora.
- **Que hable uno solo.**

Si algo no dio (el modelo no le gana al piso, un hallazgo no se sostuvo), la app lo puede contar igual.
Una historia honesta sobre un resultado modesto vale más que una app brillante que no se sabe de dónde salió.
