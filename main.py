import math
import time
from typing import List, Tuple

import networkx as nx
from matplotlib import pyplot as plt
from matplotlib.widgets import Button

from GraphDB.functions import read_graph, Graph
from GraphDB.models import Parking, Scooter, Locker
from neomodel import config
from scripts.db_update import Updater
from constants import *

import heapq


class Charger:
    def __init__(self, graph, start_vertex):
        self.graph = graph
        self.current_location = start_vertex
        self.available_batteries = 0
        self.refill_batteries(start_vertex)

    def move_to(self, next_vertex):
        self.current_location = next_vertex

    def refill_batteries(self, charger_vertex):
        self.available_batteries = self.graph.nodes[charger_vertex]["capacity"]
        self.graph.update_node(
            charger_vertex, {"status": "1", "time_charge_remaining": TIME_FOR_CHARGE}
        )

    def distribute_batteries(self, parking_vertex, target_level):
        scooters = self.graph.get_low_scooters_on_parking(parking_vertex, target_level)
        if self.available_batteries < len(scooters):
            for scooter in scooters:
                node_id = next(iter(scooter))
                self.graph.update_node(node_id, {"charge": 100})
            self.available_batteries = 0
        else:
            for scooter in scooters[: self.available_batteries]:
                node_id = next(iter(scooter))
                self.graph.update_node(node_id, {"charge": 100})
                self.available_batteries -= 1


def dijkstra(graph: Graph, start: int, end: int, to_charge) -> Tuple[List[int], int]:
    """
    Реализация алгоритма Дейкстры для поиска кратчайшего пути.
    Учитывается как расстояние, так и время зарядки.
    """
    # Инициализация
    nodes = graph.exclude_type("scooter")
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
        for neighbor in graph.neighbors(current_vertex):
            time_to_travel = graph[current_vertex][neighbor].get("time_to_travel", None)
            if time_to_travel is not None:
                new_dist = current_dist + time_to_travel
                if to_charge and neighbor == end:
                    new_dist += (
                        graph.nodes[neighbor]["time_charge_remaining"]
                        if graph.nodes[neighbor]["type"] == "locker"
                        else 0
                    )
                if new_dist < dist[neighbor]:
                    dist[neighbor] = new_dist
                    prev[neighbor] = current_vertex
                    heapq.heappush(pq, (new_dist, neighbor))

    # Если целевая вершина не была достигнута, возвращаем None
    return None


def evaluate_heuristic(graph, charger, target_charge):
    """
    Эвристическая оценка перспективности посещения данного зарядного шкафа.
    """
    zone_level = sum(
        graph.nodes[scooter]["charge_level"]
        for scooter in graph.get_nodes_by_type("scooter")
    ) / len([n for n in graph.get_nodes_by_type("scooter")])
    discharged_scooters = [
        n
        for n in graph.get_nodes_by_type("scooter")
        and graph.nodes[n]["charge_level"] < 50
    ]
    num_to_charge = min(len(discharged_scooters), graph.nodes[charger]["capacity"])
    distance_to_target = abs(zone_level - target_charge)
    heuristic = distance_to_target - num_to_charge
    return heuristic


def draw_plot(graph, path, start_pos, end_pos, distance, ax):
    nodes = graph.exclude_type("scooter")
    pos = {n: (graph.nodes[n]["lat"], graph.nodes[n]["lon"]) for n in nodes}
    ax.clear()

    node_colors = ["lightblue" if i != start_pos else "red" for i in nodes]
    nx.draw(
        graph,
        pos,
        nodelist=nodes,
        node_color=node_colors,
        labels={i: graph.nodes[i]["name"] for i in nodes},
        edgelist=graph.exclude_edges("scooter"),
        font_color="red",
    )
    plt.plot(
        [pos[node][0] for node in path],
        [pos[node][1] for node in path],
        color="r",
        linewidth=4,
    )
    plt.title(
        f"Оптимальный маршрут от {graph.nodes[start_pos]['name']} до {graph.nodes[end_pos]['name']}. Время маршрута: {distance:.2f}"
    )
    plt.draw()
    plt.pause(0.5)


def find_nearest_from_array(
    graph: Graph, vertices: list, current_location: int, to_charge=False
) -> Tuple[List, int, int]:
    next_vertex = None
    min_distance = float("inf")
    min_path = []
    if current_location in vertices:
        vertices.remove(current_location)
    for vertex in vertices:
        path, distance = dijkstra(graph, current_location, vertex, to_charge=to_charge)
        if distance < min_distance:
            min_distance = distance
            next_vertex = vertex
            min_path = path
    return min_path, next_vertex, min_distance

def get_next_path(graph: Graph, charger: Charger, updater: Updater, target_level: int):
    low_level_vertices = graph.find_low_level_vertices(100)
    available_chargers = graph.find_available_chargers()


    if charger.available_batteries == 0:
        # Если у зарядника заканчиваются батареи, он возвращается к ближайшему доступному зарядному шкафу
        if len(available_chargers) == 0:
            available_chargers = graph.get_nodes_by_type("locker")
        path, next_vertex, distance = find_nearest_from_array(
            graph,
            available_chargers,
            charger.current_location,
            to_charge=True,
        )

        charger.refill_batteries(next_vertex)
    else:
        path, next_vertex, distance = find_nearest_from_array(
            graph, low_level_vertices, charger.current_location
        )

        if graph.nodes[next_vertex]["type"] == "parking":
            charger.distribute_batteries(next_vertex, target_level)
        else:
            charger.refill_batteries(next_vertex)

    charger.move_to(next_vertex)


    # updater.decrease_scooter_charge(DECREASE_PER_ITERATION)
    # updater.random_change_scooters()
    graph.get_new_info_lockers()
    graph.get_new_info_scooters()
    return path, next_vertex, distance


def main(graph: Graph, charger: Charger, updater: Updater, target_level: int):
    travelling_time = 0
    while graph.get_average_charge_level() < target_level:
        print("Нынешний заряд зоны: ", graph.get_average_charge_level())
        low_level_vertices = graph.find_low_level_vertices(100)
        available_chargers = graph.find_available_chargers()

        if len(low_level_vertices) == 0:
            print(
                "Заряд зоны невозможно довести до целевого. Не осталось сильно разряженных парковок"
            )
            break

        if charger.available_batteries == 0:
            # Если у зарядника заканчиваются батареи, он возвращается к ближайшему доступному зарядному шкафу
            if len(available_chargers) == 0:
                available_chargers = graph.get_nodes_by_type("locker")
            path, next_vertex, distance = find_nearest_from_array(
                graph,
                available_chargers,
                charger.current_location,
                to_charge=True,
            )

            charger.refill_batteries(next_vertex)
        else:
            path, next_vertex, distance = find_nearest_from_array(
                graph, low_level_vertices, charger.current_location
            )

            if graph.nodes[next_vertex]["type"] == "parking":
                charger.distribute_batteries(next_vertex, target_level)
            else:
                charger.refill_batteries(next_vertex)
        print(
            f"Путь из {graph.nodes[charger.current_location]['name']} в {graph.nodes[next_vertex]['name']}: ",
            distance,
        )
        charger.move_to(next_vertex)

        travelling_time += distance
        print(f"Время в пути: {travelling_time:.2f}")
        print("Батарей в кармане: ", charger.available_batteries)

        start = time.perf_counter()
        updater.decrease_scooter_charge(DECREASE_PER_ITERATION)
        updater.random_change_scooters()
        updater.update_lockers(distance)
        graph.get_new_info_lockers()
        print("Средний заряд до: ", graph.get_average_charge_level())
        graph.get_new_info_scooters()
        print("Средний заряд после: ", graph.get_average_charge_level())
        print(f"Время: {time.perf_counter() - start}")

    print("Нынешний заряд зоны: ", graph.get_average_charge_level())
    print(f"Время в пути: {travelling_time:.2f}")
    print("Батарей в кармане: ", charger.available_batteries)


if __name__ == "__main__":
    config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"
    graph = read_graph()
    start_pos = Locker.nodes.get(name="Locker 1")
    charger = Charger(graph, start_pos.node_id)
    updater = Updater()
    # pos = nx.spring_layout(graph)
    # print(graph.find_low_level_vertices(80))
    main(graph, charger, updater, 80)

    # p = nx.dijkstra_path(graph, start_pos.node_id, end_pos.node_id, weight=a)
    # d = dijkstra(graph, start_pos.node_id, end_pos.node_id)
