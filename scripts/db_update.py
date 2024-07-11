import random
from time import sleep

from neomodel import config, db
from GraphDB.models import Locker, Scooter, Parking


class Updater:
    """Класс для обновления данных в базе. Не является обязательной частью системы"""
    TIME_BETWEEN_UPDATES = 10

    @db.transaction
    def decrease_scooter_charge(self, percent):
        for scooter in Scooter.nodes.all():
            scooter.charge -= percent
            scooter.save()

    @db.transaction
    def random_change_scooters(self):
        weights = {"change_parking": 45, "remove": 35, "add": 30}
        scooters = Parking.nodes.fetch_relations("has_scooter").all()
        if len(scooters) == 0:
            return
        scooters = list(map(lambda x: [x[0], x[1]], scooters))
        scooters_count = len(scooters)
        changes_count = random.randint(3, scooters_count)
        actions = random.choices(
            list(weights.keys()), weights=list(weights.values()), k=changes_count
        )
        parkings = Parking.nodes.all()
        for i in actions:
            match i:
                case "change_parking":
                    index = random.randint(0, scooters_count - 1)
                    prev_parking, scooter = scooters[index]
                    prev_parking.has_scooter.disconnect(scooter)
                    new_parking = random.choice(parkings)
                    new_parking.has_scooter.connect(scooter)
                    scooter.set_parking(new_parking.node_id)
                    scooters[index] = [new_parking, scooter]
                case "remove":
                    scooter_parking = scooters[random.randint(0, scooters_count - 1)]
                    prev_parking = scooter_parking[0]
                    scooter = scooter_parking[1]
                    prev_parking.has_scooter.disconnect(scooter)
                    scooter.delete()
                    scooters.remove(scooter_parking)
                    scooters_count -= 1
                case "add":
                    new_scooter = Scooter(
                        charge=random.randint(45, 100), name="Scooter"
                    ).save()
                    parking = random.choice(parkings)
                    parking.has_scooter.connect(new_scooter)
                    new_scooter.set_parking(parking.node_id)
                    scooters.append([parking, new_scooter])
                    scooters_count += 1

    @db.transaction
    def update_lockers(self, time_passed: int):
        """
        :param time_passed: сколько времени прошло между вызовами функции
        :return: None
        """
        lockers = Locker.nodes.filter(status="1")
        for locker in lockers:
            if locker.time_charge_remaining > time_passed:
                locker.time_charge_remaining -= time_passed
            else:
                locker.time_charge_remaining = 0
                locker.status = "0"
            locker.save()



if __name__ == "__main__":
    config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"
    updater = Updater()
    while True:
        print("Randomizing....")
        updater.random_change_scooters()
        updater.decrease_scooter_charge(0.4)
        sleep(5)
