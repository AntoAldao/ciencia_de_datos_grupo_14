"""Gráficos de la aplicación (Altair).

Al importar el paquete se activa el tema «f1»: la tipografía de la app (Titillium Web) en ejes,
leyendas y títulos de todos los gráficos. Los colores siguen saliendo de `graficos/colores.py`.
"""
import altair as alt

from graficos import colores as _C


@alt.theme.register("f1", enable=True)
def _tema_f1() -> alt.theme.ThemeConfig:
    return {"config": {"font": _C.FUENTE,
                       "title": {"font": _C.FUENTE, "fontWeight": 700},
                       "axis": {"labelFont": _C.FUENTE, "titleFont": _C.FUENTE},
                       "legend": {"labelFont": _C.FUENTE, "titleFont": _C.FUENTE}}}
