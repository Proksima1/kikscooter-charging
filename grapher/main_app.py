import json
from textwrap import dedent as d

import dash
import dash_cytoscape as cyto
import networkx as nx
import plotly.graph_objects as go
from colour import Color
from dash import Input, Output, State, callback, dcc, html

from callbacks import (
    displayHoverNodeData,
    on_button_click,
    validate_json_output,
    submit_json,
)
from grapher.config import graph, DEFAULT_JSON, nodes_stylesheet
from grapher.misc import get_average_charge, graph_to_nodes, make_graph

# Создаем Dash приложение

nodes = make_graph(graph)

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Граф города"

app.layout = html.Div(
    [
        html.Div(
            [html.H1("Граф заряда зоны")],
            className="row",
            style={"textAlign": "center"},
        ),
        html.Div(
            className="row",
            children=[
                html.Div(
                    className="three columns",
                    children=[
                        dcc.Markdown(
                            d(
                                """
                            **Кнопки перемещения к следующей точке**\n
                            Кнопка "Дальше" для перехода к следующей итерации зарядки
                            """
                            )
                        ),
                        html.Div(
                            className="twelve columns",
                            children=[
                                html.Button("Дальше", id="next_button"),
                                html.Br(),
                            ],
                            style={"height": "200px"},
                        ),
                        html.Div(
                            className="twelve columns",
                            children=[
                                dcc.Markdown(
                                    d(
                                        """
                            **Сгенерировать граф**\n
                            Введите данные для генерации графа.
                            """
                                    )
                                ),
                                dcc.Textarea(
                                    id="json-input",
                                    value=json.dumps(DEFAULT_JSON, indent=4),
                                    style={
                                        "width": "100%",
                                        "height": "150px",
                                        "resize": "none",
                                    },
                                ),
                                html.Div(id="json-output", style={"color": "red"}),
                                html.Button(
                                    "Сгенерировать",
                                    id="textarea-submit-button",
                                    disabled=False,
                                    n_clicks=0,
                                ),
                            ],
                            style={"height": "300px"},
                        ),
                    ],
                ),
                html.Div(
                    className="five columns",
                    children=[
                        cyto.Cytoscape(
                            id="city_graph",
                            layout={"name": "preset"},
                            className="twelve columns",
                            style={"height": "550px"},
                            elements=nodes,
                            stylesheet=nodes_stylesheet
                        ),
                        html.Pre(
                            className="twelve columns",
                            id="graph_output",
                            style={"textAlign": "center"},
                        ),
                    ],
                ),
                html.Div(
                    className="three columns",
                    children=[
                        html.Div(
                            className="twelve columns",
                            children=[
                                dcc.Markdown(
                                    d(
                                        """
                            **Данные вершин**\n
                            При наведении на вершину ниже будут показаны данные вершины.
                            """
                                    )
                                ),
                                html.Pre(
                                    id="hover_data",
                                    style={
                                        "height": "300px",
                                        "overflow-y": "auto",
                                        "width": "300px",
                                        "padding": "10px",
                                        "background-color": "white",
                                        "border": "1px solid #ccc",
                                        "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                                    },
                                ),
                                html.Br(),
                                html.Div(
                                    className="twelve columns",
                                    style={
                                        "display": "flex",
                                        "align-items": "center",
                                        "justify-content": "space-between",
                                    },
                                    children=[
                                        html.P(
                                            "Заряд зоны: ",
                                            style={"font-weight": "bold"},
                                        ),
                                        html.P(
                                            id="charge_data",
                                        ),
                                    ],
                                ),
                            ],
                            style={"height": "400px"},
                        ),
                    ],
                ),
            ],
        ),
    ]
)


if __name__ == "__main__":
    app.run_server(debug=True)
