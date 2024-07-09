import math
from typing import Dict, List, Tuple

from networkx import Graph as BaseGraph
import networkx as nx
from GraphDB.models import Scooter, Locker, Parking


class Graph(BaseGraph):
    LOW_CHARGE_ZONE = 50
    AVERAGE_CHARGER_SPEED_IN_MS = 2.5
    TYPES = {"locker", "parking", "scooter"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def exclude_type(self, node_type: str | set) -> List[int]:
        if not isinstance(node_type, set):
            node_type = {node_type}
        return [
            node
            for node in self.nodes
            if self.nodes[node]["type"] in Graph.TYPES.difference(node_type)
        ]

    def exclude_edges(self, type: str) -> List[Tuple[int, int]]:
        return [
            i
            for i in self.edges
            if i[0] in self.exclude_type(type) and i[1] in self.exclude_type(type)
        ]

    def get_node(self, node_id) -> dict:
        return self.nodes[node_id]

    def add_node(self, node, **attr) -> None:
        instance = attr.get("instance", None)
        if isinstance(instance, Locker):
            super().add_node(
                node,
                lat=instance.lat,
                lon=instance.lon,
                capacity=instance.capacity,
                time_charge_remaining=instance.time_charge_remaining,
                status=instance.status,
                name=instance.name,
                type="locker",
            )
        elif isinstance(instance, Scooter):
            super().add_node(
                node,
                charge=instance.charge,
                name=instance.name,
                parking=instance.parking,
                type="scooter",
            )
        elif isinstance(instance, Parking):
            super().add_node(
                node,
                lat=instance.lat,
                lon=instance.lon,
                capacity=instance.capacity,
                name=instance.name,
                type="parking",
            )
        else:
            raise ValueError(
                f"Expected instance: Scooter, Locker, Parking. Given instance: {instance}"
            )

    def get_nodes_by_type(self, type: str) -> List[int]:
        return [node for node in self.nodes if self.nodes[node]["type"] == type.lower()]

    def get_average_charge_level(self) -> float:
        scooters = self.get_nodes_by_type("scooter")
        if len(scooters) == 0:
            return 100
        return round(sum(self.nodes[i]["charge"] for i in scooters) / len(scooters), 2)

    def find_available_chargers(self) -> List[int]:
        return [
            v
            for v in self.get_nodes_by_type("locker")
            if self.nodes[v]["status"] == "0"
        ]

    def get_new_info_scooters(self) -> None:
        visited_scooters = set()
        for scooter in Scooter.nodes.all():
            node_id = scooter.node_id
            visited_scooters.add(node_id)
            is_replaced = (
                node_id in self.nodes
            )
            if is_replaced:
                self.get_node(node_id)["charge"] = scooter.charge
                self.get_node(node_id)["parking"] = scooter.parking
                self.remove_edge(*list(self.edges(node_id))[0])
            else:
                # Добавление
                self.add_node(node_id, instance=scooter)
            self.add_edge(node_id, scooter.parking)
        for scooter in self.get_nodes_by_type("scooter"):
            if scooter not in visited_scooters:
                self.remove_edge(scooter, self.get_node(scooter)["parking"])
                self.remove_node(scooter)

    def get_new_info_lockers(self) -> None:
        for locker in Locker.nodes.all():
            node_id = locker.node_id
            self.nodes[node_id]["status"] = locker.status
            self.nodes[node_id]["time_charge_remaining"] = locker.time_charge_remaining

    def get_low_scooters_on_parking(self, parking_node_id: int, target_level: int) -> List[Dict[int, Dict[str, int | str]]]:
        scooters = [
            {i: self.nodes[i]}
            for _, i in self.edges(parking_node_id)
            if self.nodes[i]["type"] == "scooter"
        ]
        sorted_scooters = sorted(scooters, key=lambda x: x[list(x.keys())[0]]["charge"])
        low_scooters = list(
            filter(
                lambda x: x[list(x.keys())[0]]["charge"] < target_level, sorted_scooters
            )
        )
        return low_scooters

    def update_node(self, node_id: int, data: Dict[str, str | int]) -> None:
        node = self.nodes[node_id]
        for i in data:
            node[i] = data[i]
        match node["type"]:
            case "locker":
                db_node = Locker.nodes.get(node_id=node_id)
            case "scooter":
                db_node = Scooter.nodes.get(node_id=node_id)
            case _:
                raise ValueError(f"Unknown node type {node['type']}")
        for i in data:
            setattr(db_node, i, data[i])
        db_node.save()

    def find_low_level_vertices(self, target_level: int) -> List[int]:
        data = []
        for node in self.exclude_type({"scooter", "locker"}):
            s = 0
            count = 0
            for _, i in self.edges(node):
                if self.nodes[i]["type"] == "scooter":
                    s += self.nodes[i]["charge"]
                    count += 1

            if count > 0:
                if s / count < target_level:
                    data.append((count, s / count, node))
        data.sort(reverse=True)
        data = list(map(lambda x: x[-1], data))
        return data
