import json

import neomodel
from colour import Color

from GraphDB.functions import read_graph, make_random_graph
from GraphDB.models import Locker
from GraphDB.charger import Charger
from neomodel import config
from scripts.db_update import Updater

config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"

DEFAULT_JSON = {
    "parkingCount": 40,
    "lockerCount": 10,
    "scooterCount": 150,
    "squareSize": 1000,
}

graph = read_graph()
if len(graph.nodes) == 0:
    make_random_graph(DEFAULT_JSON)
graph = read_graph()
start_pos = Locker.nodes.get(name="Locker 0")

charger = Charger(graph, start_pos.node_id)
updater = Updater()


nodes_stylesheet = [
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-color": "#333",
            "target-arrow-shape": "triangle",
            "line-color": "#333",
            "width": 2,
        },
    },
    {
        "selector": "node",
        "style": {
            "background-color": "#bdd7e7",
            "label": "data(label)",
            "width": 50,
            "height": 50,
        },
    },
]

colors = list(Color("red").range_to(Color("green"), 4))
for i in range(1, 5):
    nodes_stylesheet.append(
        {
            "selector": f"[average_charge > {25 * i}]",
            "style": {
                "background-color": colors[i - 1].hex,
            },
        }
    )