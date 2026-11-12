"""Gráficos de la aplicación (Altair).

Al importar el paquete se activa el tema «f1»: la tipografía de la app (Titillium Web) y letras
más grandes en ejes, leyendas y títulos de todos los gráficos. Los colores salen de
`graficos/colores.py`.
"""
import altair as alt

from graficos import colores as _C


@alt.theme.register("f1", enable=True)
def _tema_f1() -> alt.theme.ThemeConfig:
    f = _C.FUENTE
    return {"config": {
        "font": f,
        "title": {"font": f, "fontWeight": 700, "fontSize": 18, "subtitleFont": f,
                  "subtitleFontSize": 14, "color": _C.INK, "subtitleColor": _C.INK_MUTED},
        "axis": {"labelFont": f, "titleFont": f, "labelFontSize": 13, "titleFontSize": 14,
                 "labelColor": _C.INK_MUTED, "titleColor": _C.INK_MUTED},
        "legend": {"labelFont": f, "titleFont": f, "labelFontSize": 14, "titleFontSize": 14,
                   "labelColor": _C.INK, "symbolSize": 120},
        "text": {"font": f, "fontSize": 13, "color": _C.INK},
    }}
