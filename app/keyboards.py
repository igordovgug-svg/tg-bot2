from datetime import date, time

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, CallbackQuery
from  aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Service
from database.orm_queries import orm_get_services_by_id




async def start_kb(is_admin: bool):
    builder = InlineKeyboardBuilder()
    builder.button(text='Записатися на послугу', callback_data='book:service')
    builder.button(text='Мої записи', callback_data='my:services')

    if is_admin:
        builder.button(text='Адмін меню', callback_data="admin:menu")

    return builder.as_markup()

services = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Стрижка', callback_data='Hair:cut')], [InlineKeyboardButton(text='Фарбування волося', callback_data="Hair:coloring")]
])


confirm_booking = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Підтвердити', callback_data='confirm:booking')], [InlineKeyboardButton(text="Спочатку", callback_data="book:service")]
])

async def muplti_kb_inline(text, callback):
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=callback)
    return builder.as_markup()


async def build_services_keyboard(services: list[Service]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for serv in services:
        label = f"{serv.name} — {serv.price} грн"
        builder.button(text=label, callback_data=f"service:{serv.id}:{serv.name}")

    builder.adjust(2)
    return builder.as_markup()



async def build_days_keyboard(days: list[date]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for wd in days:
        label = f"{wd.date_day.strftime('%a, %d.%m')} ({wd.start_time.strftime('%H:%M')}-{wd.end_time.strftime('%H:%M')})"
        builder.button(text=label, callback_data=f"day:{wd.date_day.isoformat()}")

    builder.adjust(2)
    return builder.as_markup()


async def build_time_keyboard(slots: list[time], day: date) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=slot.strftime('%H:%M'),
            callback_data=f"time:{day.isoformat()}:{slot.strftime('%H:%M')}"
        )
    builder.adjust(3)
    return builder.as_markup()


async def build_bookings_keyboard(bookings: list, page: int, total: int, name: str, page_size: int = 5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    

    for b in bookings:
        label = f"{b.date_day.strftime('%d.%m')} {b.start_time.strftime('%H:%M')} — {b.service.name}"
        builder.row(InlineKeyboardButton(text=label, callback_data="noop"))
        builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel:{b.id}"))

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"mypage:{page-1}"))
    if page * page_size < total:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"mypage:{page+1}"))
    if nav_row:
        builder.row(*nav_row)
    builder.button(text="Меню", callback_data="start:menu")

    return builder.as_markup()



async def build_admin_bookings_keyboard(bookings: list):
    builder = InlineKeyboardBuilder()

    for b in bookings:
        label = f"{b.date_day.strftime('%d.%m')} {b.start_time.strftime('%H:%M')} — {b.service.name}"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin_booking:{b.id}:{b.user_id}"))

    builder.button(text="Назад", callback_data="admin:menu")
    builder.adjust(1)

    return builder.as_markup()


admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Загальна кільість записів", callback_data='stats')], [InlineKeyboardButton(text="Додати нову послугу", callback_data="add:service")],
    [InlineKeyboardButton(text="Існуючі записи клієнтів", callback_data="services")], [InlineKeyboardButton(text="Видалити послугу", callback_data="delete:sevrice")],
    [InlineKeyboardButton(text="Назад", callback_data="start:menu")]
])


async def delete_service(names: list):
    builder = InlineKeyboardBuilder()
    for n in names:
        label = f"{n.name}"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"{n.name}:{n.id}:delete"))

    builder.button(text="Назад", callback_data="admin:menu")
    builder.adjust(2)

    return builder.as_markup()


confirm_delete = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Підтвердити", callback_data='confirm:delete:sevrice')], [InlineKeyboardButton(text="Скасувати", callback_data='delete:sevrice')]
])


async def kyeboard_options(name: str, id: int):
    builder = InlineKeyboardBuilder()

    builder.button(text=f"Видалити категорію {name}", callback_data=f"confirm:delete:{id}")
    builder.button(text="Скасувати видалення", callback_data="delete:sevrice")

    return builder.as_markup()