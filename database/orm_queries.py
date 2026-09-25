import asyncio
import datetime

from datetime import date, timedelta, time
from decimal import Decimal

from aiogram import Bot
from database.models import WorkingDays, Booking, BookingStatus, Admin, Service

from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

days_ahead = 14
weekend_days = {5,6}

weekday_hours = (time(8,0), time(18,0))
weekend_hours = (time(9,0), time(15,0))


def hours_for(day: date) -> tuple[time, time]:
    return weekend_hours if day.weekday() in weekend_days else weekday_hours


async def sync_working_days(
    session: AsyncSession,
    days_ahead: int = days_ahead,
    ) -> None: 

    today = date.today()

    result = await session.execute(select(WorkingDays.date_day))
    existing = set(result.scalars())

    to_add = []
    for offset in range(days_ahead):
        day = today + timedelta(days=offset)
        if day not in existing:
            start, end = hours_for(day)
            to_add.append(WorkingDays(date_day=day, start_time=start, end_time=end))

    if to_add:
        session.add_all(to_add)

    await session.execute(delete(WorkingDays).where(WorkingDays.date_day < today))
    await session.commit()


async def get_available_days(session: AsyncSession, days_ahead: int = 7) -> list[WorkingDays]:
    today = date.today()
    result = await session.execute(
        select(WorkingDays)
        .where(WorkingDays.date_day >= today)
        .order_by(WorkingDays.date_day)
    )
    return list(result.scalars())


async def get_working_hours(session: AsyncSession, day: date) -> tuple[time, time] | None:
    result = await session.execute(
        select(WorkingDays.start_time, WorkingDays.end_time)
        .where(WorkingDays.date_day == day)
    )

    row = result.first()
    return (row.start_time, row.end_time) if row else None


async def create_booking(session: AsyncSession, user_id: int, service_id: int, day: date, slot_time: time): 
    booking = Booking(
        user_id=user_id,
        service_id=service_id,
        date_day=day,       
        start_time=slot_time,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return None
    return booking


async def get_user_booking(session: AsyncSession, user_id: int, page: int = 1, page_size: int = 5):
    offset = (page - 1) * page_size


    total_resuly = await session.execute(
        select(func.count()).select_from(Booking)
        .where(Booking.user_id == user_id, Booking.status == BookingStatus.active)
    )

    total = total_resuly.scalar_one()


    result = await session.execute(
        select(Booking)
        .where(Booking.user_id == user_id, Booking.status == BookingStatus.active)
        .options(selectinload(Booking.service))
        .order_by(Booking.date_day, Booking.start_time)
        .offset(offset)
        .limit(page_size)
    )

    bookings = list(result.scalars())

    return bookings, total


async def cancel_booking(session: AsyncSession, booking_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == user_id)
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.status == BookingStatus.cancelled:
        return False

    booking.status = BookingStatus.cancelled
    await session.commit()
    return True


async def orm_is_admin(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Admin.user_id)
        .where(Admin.user_id == user_id)
    )
    admin = result.scalar()
    
    return admin is not None


async def orm_show_stats_for_admin(session: AsyncSession):
    result = await session.execute(
        select(func.count(Booking.id))
        .where(Booking.status == "active")
        )
        
    count = result.scalar()
    return count


async def orm_sync_admins(session: AsyncSession, currend_admin_list: list[int]):
    result = await session.execute(
        select(Admin.user_id)
        )

    
    existing = set(result.scalars().all())

    remove_admin_list = [x for x in existing if x not in currend_admin_list]

    current_admins = [Admin(user_id=x) for x in currend_admin_list if x not in existing]


    if current_admins:
        session.add_all(current_admins)

    if remove_admin_list:
        await session.execute(delete(Admin).where(Admin.user_id.in_(remove_admin_list)))

    await session.commit()


async def orm_get_services(session: AsyncSession):
    result = await session.execute(
        select(Service)
        .where(Service.is_active)
    )

    services = result.scalars().all()

    return services


async def orm_add_service(session: AsyncSession, name: str, price: Decimal):
    service = Service(name=name, price=price)
    session.add(service)
    await session.commit()
    return service


async def orm_get_services_by_id(session: AsyncSession, service_id: int):
    result = await session.execute(select(Service.name).where(Service.id == service_id))

    name = result.scalar_one_or_none()

    return name

async def orm_get_avtive_booking(session: AsyncSession):
    result = await session.execute(
        select(Booking)
        .where(Booking.status == "active")
        .options(selectinload(Booking.service))
        .order_by(Booking.date_day, Booking.start_time)
    )

    bookings = result.scalars().all()

    return bookings


async def get_booking_for_admin(session: AsyncSession, user_id: int, booking_id: int):
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.service))
        .where(Booking.user_id == user_id, Booking.id == booking_id)
    )

    booking = result.scalar_one_or_none()

    return booking


async def get_bot_chat(bot: Bot, user_id: int):
    chat = await bot.get_chat(user_id)
    full_name = chat.full_name
    user_name = f"@{chat.username}" if chat.username else 'немає username'

    return full_name, user_name


async def get_service_obj(session: AsyncSession):
    names = await session.execute(
        select(Service)
        .where(Service.is_active)
    )
    result = names.scalars().all()

    return result


async def orm_delete_service(session: AsyncSession, service_id: int) -> bool:
    service = await session.get(Service, service_id)

    if service is None:
        return False

    await session.delete(service)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return False

    return True