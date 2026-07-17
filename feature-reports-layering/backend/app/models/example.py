from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base


class ExampleRecord(Base):
    __tablename__ = "example_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)