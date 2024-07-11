import heapq
from typing import Dict, List, Tuple

from networkx import Graph as BaseGraph

from GraphDB.constants import CAN_WRITE
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
        # visited_scooters = set()
        for i in self.get_nodes_by_type("scooter"):
            self.remove_edge(i, self.nodes[i]["parking"])
            self.remove_node(i)
        for scooter in Scooter.nodes.all():
            self.add_node(scooter.node_id, instance=scooter)
            self.add_edge(scooter.node_id, scooter.parking)

    def get_new_info_lockers(self) -> None:
        for locker in Locker.nodes.all():
            node_id = locker.node_id
            self.nodes[node_id]["status"] = locker.status
            self.nodes[node_id]["time_charge_remaining"] = locker.time_charge_remaining

    def get_low_scooters_on_parking(
        self, parking_node_id: int, target_level: int
    ) -> List[Dict[int, Dict[str, int | str]]]:
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
        if CAN_WRITE:
            match node["type"]:
                case "locker":
                    db_node = Locker.nodes.get(node_id=node_id)
                case "scooter":
                    try:
                        db_node = Scooter.nodes.get(node_id=node_id)
                    except Exception:
                        return
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

    def dijkstra(self, start: int, end: int, to_charge) -> Tuple[List[int], int]:
        """
        Реализация алгоритма Дейкстры для поиска кратчайшего пути.
        Учитывается как расстояние, так и время зарядки.
        """
        # Инициализация
        nodes = self.exclude_type("scooter")
        dist = {v: float("inf") for v in nodes}
        dist[start] = 0
        prev = {v: None for v in nodes}
        pq = [(0, start)]

        while pq:
            # Извлекаем вершину с минимальным расстоянием
            current_dist, current_vertex = heapq.heappop(pq)

            # Если мы достигли целевой вершины, возвращаем путь
            if current_vertex == end:
                path = []
                v = end
                while v is not None:
                    path.append(v)
                    v = prev[v]
                path.reverse()
                return path, current_dist

            # Если текущее расстояние больше, чем уже найденное, пропускаем
            if current_dist > dist[current_vertex]:
                continue

            # Обновляем расстояния до соседних вершин
            for neighbor in self.neighbors(current_vertex):
                time_to_travel = self[current_vertex][neighbor].get(
                    "time_to_travel", None
                )
                if time_to_travel is not None:
                    new_dist = current_dist + time_to_travel
                    if to_charge and neighbor == end:
                        new_dist += (
                            self.nodes[neighbor]["time_charge_remaining"]
                            if self.nodes[neighbor]["type"] == "locker"
                            else 0
                        )
                    if new_dist < dist[neighbor]:
                        dist[neighbor] = new_dist
                        prev[neighbor] = current_vertex
                        heapq.heappush(pq, (new_dist, neighbor))

        # Если целевая вершина не была достигнута, возвращаем None
        return None

    def evaluate_heuristic(self, charger, target_charge):
        """
        Эвристическая оценка перспективности посещения данного зарядного шкафа.
        """
        zone_level = sum(
            self.nodes[scooter]["charge"]
            for scooter in self.get_nodes_by_type("scooter")
        ) / len([n for n in self.get_nodes_by_type("scooter")])
        discharged_scooters = [
            n
            for n in self.get_nodes_by_type("scooter")
            if self.nodes[n]["charge"] < 50
        ]
        num_to_charge = min(len(discharged_scooters), self.nodes[charger]["capacity"])
        distance_to_target = abs(zone_level - target_charge)
        heuristic = distance_to_target - num_to_charge
        return heuristic

    def find_nearest_from_array(
        self, vertices: list, current_location: int, to_charge=False
    ) -> Tuple[List, int, int]:
        next_vertex = None
        min_distance = float("inf")
        min_path = []
        if current_location in vertices:
            vertices.remove(current_location)
        for vertex in vertices:
            path, distance = self.dijkstra(
                current_location, vertex, to_charge=to_charge
            )
            heuristic = self.evaluate_heuristic(vertex, 80)
            # print(heuristic)
            if distance < min_distance:  # + heuristic: # c эвристикой 61, без эвристикой 62
                min_distance = distance
                next_vertex = vertex
                min_path = path
        return min_path, next_vertex, min_distance

    def charge_nearest_parking(self, charger, target_level: int):
        low_level_vertices = self.find_low_level_vertices(80)
        available_chargers = self.find_available_chargers()

        if charger.available_batteries == 0:
            # Если у зарядника заканчиваются батареи, он возвращается к ближайшему доступному зарядному шкафу
            if len(available_chargers) == 0:
                available_chargers = self.get_nodes_by_type("locker")
            path, next_vertex, distance = self.find_nearest_from_array(
                available_chargers,
                charger.current_location,
                to_charge=True,
            )

            charger.refill_batteries(next_vertex)
        else:
            path, next_vertex, distance = self.find_nearest_from_array(
                low_level_vertices, charger.current_location
            )

            if self.nodes[next_vertex]["type"] == "parking":
                charger.distribute_batteries(next_vertex, target_level)
            else:
                charger.refill_batteries(next_vertex)

        charger.move_to(next_vertex)

        # updater.decrease_scooter_charge(DECREASE_PER_ITERATION)
        # updater.random_change_scooters()

        return path, next_vertex, distance
