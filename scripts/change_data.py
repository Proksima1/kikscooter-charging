from neomodel import config
from GraphDB.models import Locker, Parking

def main():
    print("--- Редактор данных ---")
    while True:
        t = input("Что вы хотите изменить? Шкаф(l), парковку(p): ")
        node_id = int(input("Введите node_id: "))
        match t:
            case "l":
                instance = Locker.nodes.get(node_id=node_id)
            case "p":
                instance = Locker.nodes.get(node_id=node_id)
        attr = input("Введите какой атрибут хотите поменять: ")

if __name__ == "__main__":
    config.DATABASE_URL = "bolt://neo4j:changeme@localhost:7687"

