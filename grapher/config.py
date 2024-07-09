from colour import Color

from GraphDB.functions import read_graph
from GraphDB.models import Locker
from main import Charger
from neomodel import config
from scripts.db_update import Updater

config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"


graph = read_graph()
start_pos = Locker.nodes.get(name="Locker 1")
charger = Charger(graph, start_pos.node_id)
updater = Updater()


DEFAULT_JSON = {
    "parkingCount": 40,
    "lockerCount": 10,
    "scooterCount": 150,
    "squareSize": 1000,
}

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