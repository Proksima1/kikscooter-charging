import random

from neomodel import (
    StructuredNode,
    IntegerProperty,
    StringProperty,
    RelationshipTo,
    StructuredRel,
    ZeroOrMore,
    FloatProperty,
    OneOrMore,
    config,
)


class Base(StructuredNode):
    __abstract_node__ = True
    node_id = IntegerProperty(default=lambda: random.getrandbits(32), unique_index=True)
    name = StringProperty()


class PathRel(StructuredRel):
    time_to_travel = FloatProperty()


class ScooterRel(StructuredRel): ...


class Locker(Base):
    lat = IntegerProperty()
    lon = IntegerProperty()
    status = StringProperty(
        choices={"0": "ready", "1": "charging", "2": "empty"}, default="0"
    )
    time_charge_remaining = IntegerProperty(default=0)
    capacity = IntegerProperty(default=20)
    lockerPath = RelationshipTo("Locker", "PATH", cardinality=OneOrMore, model=PathRel)


class Parking(Base):
    lat = IntegerProperty()
    lon = IntegerProperty()
    capacity = IntegerProperty(default=lambda: random.choice([5, 10, 15, 20]))
    lockerPath = RelationshipTo("Locker", "PATH", cardinality=ZeroOrMore, model=PathRel)
    parkingPath = RelationshipTo(
        "Parking", "PATH", cardinality=ZeroOrMore, model=PathRel
    )
    has_scooter = RelationshipTo(
        "Scooter", "HAS_SCOOTER", cardinality=ZeroOrMore, model=ScooterRel
    )


class Scooter(Base):
    charge = FloatProperty()
    parking = IntegerProperty()

    def set_parking(self, parking: int):
        self.parking = parking
        self.save()
