from decimal import Decimal
import enum as py_enum  
from sqlalchemy import Boolean, Enum as SAEnum, Numeric, Text, text

from sqlalchemy import BigInteger, String, DateTime, UniqueConstraint, func, ForeignKey, Date, Time, exists
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import date, time





class BookingStatus(py_enum.Enum):
    active = "active"
    cancelled = "cancelled"


class Base(DeclarativeBase):
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class WorkingDays(Base):
    __tablename__ = "working_days"

    id : Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date_day: Mapped[date] = mapped_column(Date,unique=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    date_day: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(SAEnum(BookingStatus), default=BookingStatus.active)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)

    service: Mapped["Service"] = relationship(back_populates="bookings")

    __table_args__ = (
        UniqueConstraint("date_day", "start_time", "status", name="uq_slot_active"),
    )


class Admin(Base):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False, unique=True)


class Service(Base):
    __tablename__ = 'services'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=True, default=True)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")

