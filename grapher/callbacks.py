import json

from dash import Input, Output, State, callback
from main import get_next_path
from GraphDB.functions import make_random_graph, delete_all
from grapher.misc import graph_to_nodes, get_average_charge, make_graph

from grapher.config import *


@callback(
    [Output("json-output", "children"), Output("textarea-submit-button", "disabled")],
    Input("json-input", "value"),
)
def validate_json_output(json_string):
    try:
        json.loads(json_string)
        return "", False
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}", True


@callback(
    Output("city_graph", "elements", allow_duplicate=True),
    Input("textarea-submit-button", "n_clicks"),
    State("json-input", "value"),
    prevent_initial_call=True,
)
def submit_json(n_clicks, value):
    global graph, start_pos, charger
    if n_clicks > 0:
        delete_all()
        make_random_graph(json.loads(value))
        graph = read_graph()
        start_pos = Locker.nodes.get(name="Locker 1")
        charger = Charger(graph, start_pos.node_id)
        return make_graph(graph)


@callback(
    [
        Output("city_graph", "elements"),
        Output("graph_output", "children"),
        Output("charge_data", "children"),
    ],
    Input("next_button", "n_clicks"),
    State("city_graph", "elements"),
    prevent_initial_call=True,
)
def on_button_click(n_clicks, elements):
    charge_level = graph.get_average_charge_level()
    if charge_level < 80:
        path, next_vertex, distance = get_next_path(graph, charger, updater, 80)
        updater.update_lockers(distance)
        ids = set(i["data"]["id"] for i in elements)
        elements = [i for i in elements if "source" not in i["data"].keys()]
        for element in elements:
            data = element["data"]
            if data["type"] == "parking":
                charge, scooterCount = get_average_charge(graph, data)
                data["average_charge"] = charge
                data["scooterCount"] = scooterCount
            if data["type"] == "locker":
                node = graph.get_node(int(data["id"]))
                data["status"] = node["status"]
                data["time_charge_remaining"] = node["time_charge_remaining"]
        for i in range(len(path) - 1):
            time_to_travel = graph[path[i]][path[i + 1]]["time_to_travel"]
            if str(path[i]) + str(path[i + 1]) not in ids:
                elements.append(
                    {
                        "data": {
                            "id": str(path[i]) + str(path[i + 1]),
                            "source": str(path[i]),
                            "target": str(path[i + 1]),
                            "time_to_travel": time_to_travel,
                        },
                    }
                )

        return elements, "", charge_level
    return (
        elements,
        f"Зарядка зоны завершена. Заряд зоны: {graph.get_average_charge_level():.2f}",
        charge_level,
    )


@callback(
    Output("hover_data", "children"),
    Input("city_graph", "mouseoverNodeData"),
)
def displayHoverNodeData(data):
    if data:
        data.pop("label")
        data.pop("timeStamp")
        return json.dumps(data, indent=4)


@callback(
    Output("hover_data", "children", allow_duplicate=True),
    Input("city_graph", "tapEdgeData"),
    prevent_initial_call=True,
)
def displayClickEdgeData(data):
    if data:
        data.pop("id")
        data.pop("timeStamp")
        source = graph.nodes[int(data["source"])]
        target = graph.nodes[int(data["target"])]
        data["source"] = source
        data["target"] = target
        return json.dumps(data, indent=4)
