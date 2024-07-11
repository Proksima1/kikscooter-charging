from GraphDB.constants import TIME_FOR_CHARGE
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

