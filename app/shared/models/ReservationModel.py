from pydantic import BaseModel
from typing import Optional, List
import uuid
from shared.models.MenuModel import MenuModel

class ReservationModel(BaseModel):
    name: str
    email: str
    phone: str
    date: str
    time: str
    guests: int
    status: str
    reservation_id: uuid.UUID
    menus: Optional[List[MenuModel]]

    def __init__(self, name, email, phone, date, time, guests, status, reservation_id, menus=None):
        super().__init__(
            name=name,
            email=email,
            phone=phone,
            date=date,
            time=time,
            guests=guests,
            status=status,
            reservation_id=reservation_id,
            menus=menus
        )

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "date": self.date,
            "time": self.time,
            "guests": self.guests,
            "status": self.status,
            "reservation_id": str(self.reservation_id),
            "menus": [menu.to_dict() if hasattr(menu, 'to_dict') else menu for menu in self.menus] if self.menus else None
        }

    @classmethod
    def from_dict(cls, data):
        name = data["name"]
        email = data["email"]
        phone = data["phone"]
        date = data["date"]
        time = data["time"]
        guests = data["guests"]
        status = data["status"]
        reservation_id = data["reservation_id"]
        menus = data["menus"] if data["menus"] else None
        return ReservationModel(name, email, phone, date, time, guests, status, reservation_id, menus)

    def get_price(self):
        return sum(menu["price"] for menu in self.menus)