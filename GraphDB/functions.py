import math
import random
import time
from typing import Dict

import networkx as nx

from GraphDB.models import Parking, Locker, Scooter
from GraphDB.graph import Graph
from neomodel import config, db, Traversal, EITHER
import itertools


def delete_all():
    for i in Parking.nodes.all():
        i.delete()
    for i in Locker.nodes.all():
        i.delete()
    for i in Scooter.nodes.all():
        i.delete()


def _make_connections():
    query = (
        "{time_to_travel: round((sqrt((l1.lat-l2.lat)^2 + (l1.lon-l2.lon)^2) / 8.5) + rand() * 1000 %"
        " sqrt((l1.lat-l2.lat)^2 + (l1.lon-l2.lon)^2) / 2.5 * 4, 2)}"
    )
    # query = """{time_to_travel: sqrt((l1.lat - l2.lat) ^ 2 + (l1.lon-l2.lon) ^ 2) / 2.5 +rand() % (abs(l1.lat-l2.lat)-abs(l1.lon-l2.lon))}"""
    db.cypher_query(
        f"""MATCH (l1:Parking) WITH l1 MATCH (l2:Parking) WHERE l1.node_id < l2.node_id AND NOT EXISTS ((l1)-[:PATH]->(l2))
            CREATE (l1)-[:PATH {query}]->(l2);"""
    )
    db.cypher_query(
        f"""MATCH (l1:Locker) WITH l1 MATCH (l2:Locker) WHERE l1.node_id < l2.node_id AND NOT EXISTS ((l1)-[:PATH]->(l2))
            CREATE (l1)-[:PATH {query}]->(l2);"""
    )
    db.cypher_query(
        f"""MATCH (l1:Parking)
            WITH l1
            MATCH (l2:Locker)
            WHERE (NOT ((l1)-[:PATH]->(l2)))
            CREATE (l1)-[:PATH {query}]->(l2);"""
    )


def make_static_graph() -> None:
    Locker(name="Locker 1", lat=0, lon=0, capacity=5).save()
    p = Parking(name="Parking 1", lat=20, lon=0, capacity=5).save()
    for i in range(5):
        s = Scooter(
            name=f"Scooter {i}",
            charge=random.choices(
                range(45, 100), weights=(100 - i * 3 for i in range(100 - 45)), k=1
            )[0],
        )
        s.set_parking(p.node_id)
        s.save()
        p.has_scooter.connect(s)
    p = Parking(name="Parking 2", lat=40, lon=35, capacity=5).save()
    for i in range(10):
        s = Scooter(
            name=f"Scooter {i}",
            charge=random.choices(
                range(45, 100), weights=(100 - i * 3 for i in range(100 - 45)), k=1
            )[0],
        )
        s.set_parking(p.node_id)
        s.save()
        p.has_scooter.connect(s)
    Parking(name="Parking 3", lat=15, lon=2, capacity=5).save()
    Parking(name="Parking 4", lat=12, lon=16, capacity=5).save()
    Parking(name="Parking 5", lat=34, lon=10, capacity=5).save()
    Parking(name="Parking 6", lat=0, lon=22, capacity=5).save()
    Locker(name="Locker 2", lat=10, lon=10, capacity=5).save()
    _make_connections()


@db.transaction
def make_random_graph(params: Dict) -> None:
    """ "
    :param params: Dictionary of parameters(parkingCount, lockerCount, scooterCount, squareSize)
    """
    squareSize = params.get("squareSize", 1000)
    getRandomPos = lambda: random.randint(0, squareSize)
    for i in range(params.get("parkingCount", 20)):
        Parking(name=f"Parking {i}", lat=getRandomPos(), lon=getRandomPos()).save()
    for i in range(params.get("lockerCount", 10)):
        Locker(name=f"Locker {i}", lat=getRandomPos(), lon=getRandomPos()).save()
    for i in range(params.get("scooterCount", 15)):
        parking = random.choice(Parking.nodes.all())
        scooter = Scooter(
            name=f"Scooter {i}",
            charge=random.choices(
                range(45, 100), weights=(100 - i * 3 for i in range(100 - 45)), k=1
            )[0],
            # parking=parking.node_id
        )
        scooter.set_parking(parking.node_id)
        parking.has_scooter.connect(scooter)
    _make_connections()


def read_graph() -> Graph:
    graph = Graph()
    for parking in Parking.nodes.all():
        graph.add_node(parking.node_id, instance=parking)
        for scooter in parking.has_scooter.all():
            graph.add_node(scooter.node_id, instance=scooter)
            graph.add_edge(scooter.node_id, parking.node_id)
    for locker in Locker.nodes.all():
        graph.add_node(locker.node_id, instance=locker)
    for parking in Parking.nodes.all():
        for connection in parking.parkingPath.all():
            r = parking.parkingPath.relationship(connection)
            graph.add_edge(
                parking.node_id, connection.node_id, time_to_travel=r.time_to_travel
            )
        for connection in parking.lockerPath.all():
            r = parking.lockerPath.relationship(connection)
            graph.add_edge(
                parking.node_id, connection.node_id, time_to_travel=r.time_to_travel
            )
    for locker in Parking.nodes.all():
        for connection in locker.lockerPath.all():
            r = locker.lockerPath.relationship(connection)
            graph.add_edge(
                locker.node_id, connection.node_id, time_to_travel=r.time_to_travel
            )
    return graph


if __name__ == "__main__":
    config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"

    # load_dotenv("../.env")
    # print(os.path.abspath("../.env"))
    # USERNAME = os.getenv("NEO4J_USERNAME")
    # PASSWORD = os.getenv("NE04J_PASSWORD")
    # print(USERNAME)
    # driver = Neo4jDriver((USERNAME, PASSWORD))
    # params = {"lockerCount": 5,
    #           "lockerCapacity": 20,
    #           "parkingCount": 20,
    #           "parkingCapacity": 15,
    #           "averageChargerSpeed": 2.5,
    #           "readyStatus": LockerStatus.ready.value}
    # make_graph(driver, params=params)
    # params = {"scootersCount": 20, "minCharge": 45}
    # make_scooters(driver, params)
    # print(get_average_zone_charge(driver))
    # # read_graph(driver)
    # # Закрытие соединения
    # driver.close()
    delete_all()
    # params = {
    #     # "parkingCount": 40,
    #     # "lockerCount": 10,
    #     # "scooterCount": 150,
    #     # "squareSize": 1000,
    # # }
    # # make_random_graph(params=params)
    # make_static_graph()
    # read_graph()
    print("Done")
