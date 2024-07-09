from typing import Tuple


def graph_to_nodes(graph) -> list:
    nodes = [
        {
            "data": {
                "id": str(node),
                "label": graph.get_node(node)["name"],
                **graph.get_node(node),
            },
            "position": {
                "x": int(graph.nodes[node]["lat"]),
                "y": int(graph.nodes[node]["lon"]),
            },
        }
        for node in graph.exclude_type("scooter")
    ]
    return nodes


def get_average_charge(graph, data) -> Tuple[float, int]:
    scooters = graph.get_low_scooters_on_parking(int(data["id"]), 101)
    if len(scooters) > 0:
        charge = sum(
            i[next(iter(i))]["charge"] for i in scooters
        ) / len(scooters)
    else:
        charge = 100
    return charge, len(scooters)


def make_graph(graph):
    nodes = graph_to_nodes(graph)
    for node in nodes:
        data = node["data"]
        if data["type"] == "parking":
            charge, scootersCount = get_average_charge(graph, data)
            data["average_charge"] = charge
            data["scooters_count"] = scootersCount
    return nodes