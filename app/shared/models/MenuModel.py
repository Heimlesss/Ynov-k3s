import uuid
from pydantic import BaseModel

class MenuModel(BaseModel):
    menu_id: uuid.UUID
    name: str
    price: float

    def __init__(self, menu_id, name, price):
        super().__init__(menu_id=menu_id, name=name, price=price)

    def to_dict(self):
        return {
            "menu_id": str(self.menu_id),
            "name": self.name,
            "price": self.price
        }

    def from_dict(self, data):
        self.menu_id = data["menu_id"]
        self.name = data["name"]
        self.price = data["price"]
        return self
