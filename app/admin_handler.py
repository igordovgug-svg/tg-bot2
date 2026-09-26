from decimal import Decimal

from aiogram import F, Bot, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

import app.keyboards as kb

from database.models import Service
from database.orm_queries import get_booking_for_admin, get_bot_chat, get_service_obj, orm_add_service, orm_delete_service, orm_get_avtive_booking, orm_show_stats_for_admin
from .filters import IsAdmin

from aiogram.utils.keyboard import InlineKeyboardBuilder

admin = Router()


@admin.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery):
    await callback.message.edit_text("Ваша Адмін панель", reply_markup=kb.admin_keyboard)



@admin.callback_query(F.data == "stats", IsAdmin())
async def show_stats(callback: CallbackQuery, session: AsyncSession):
    stats = await orm_show_stats_for_admin(session)
    await callback.message.edit_text(f"всі існюючі записи, {stats}", reply_markup=await kb.muplti_kb_inline(text="Назад", callback='admin:menu'))

"""
Початок регістрації нової послуги
"""


class AddServices(StatesGroup):
    name = State()
    price = State()
    

@admin.callback_query(F.data == 'add:service', IsAdmin(), StateFilter(None))
async def add_service(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть назву послуги")
    await state.set_state(AddServices.name)


@admin.message(IsAdmin(), StateFilter(AddServices.name))
async def name_service(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Тепер введіть ціну:")
    await state.set_state(AddServices.price)


@admin.message(IsAdmin(), StateFilter(AddServices.price))
async def price_service(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    name = data["name"]
    price = Decimal(message.text)

    service = await orm_add_service(session, name, price)

    await message.answer(f"Послугу '{service.name}' додано, ціна {service.price}")
    await state.clear()


"""
Кінець регістрації нової послуги
"""


# показує всі існуючі записи клієнтів нажаль без пагінації 
@admin.callback_query(IsAdmin(), F.data == "services")
async def get_service(callback: CallbackQuery, session: AsyncSession):
    bookings = await orm_get_avtive_booking(session)

    await callback.message.edit_text("Виберіть послугу", reply_markup=await kb.build_admin_bookings_keyboard(bookings))
    

# детальніше показує інформацію про запис клієнта на яку дату та час також доступну інформації usera в телеграм
@admin.callback_query(F.data.startswith("admin_booking"), IsAdmin())
async def show_booking_details(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    booking_id = int(callback.data.split(':')[1])
    user_id = int(callback.data.split(":")[2])

    b = await get_booking_for_admin(session, user_id, booking_id)

    if b is None:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    full_name, user_name = await get_bot_chat(bot, user_id)

    text = (
        f"Запис на ім'я -> {full_name}\n"
        f"Записався на -> {b.date_day} {b.start_time}\n"
        f"Послуга -> {b.service.name}\n"
        f"Контактні дані -> {user_name}\n"
    )

    await callback.message.edit_text(text, reply_markup=await kb.muplti_kb_inline(text='Назад', callback="services"))


"""
Початок блоку для видалення непотрібних послуг
"""

@admin.callback_query(F.data == 'delete:sevrice')
async def delete_service(callback: CallbackQuery, session: AsyncSession):
    names = await get_service_obj(session)
    await callback.message.edit_text("Вибеіть послугу яку хочете видалити", reply_markup=await kb.delete_service(names))


@admin.callback_query(F.data.endswith("delete"))
async def chose_delete_options(callback: CallbackQuery, session: AsyncSession):
    service_name = callback.data.split(":")[0]
    id = int(callback.data.split(":")[1])
    await callback.message.edit_text("Виберіть",reply_markup=await kb.kyeboard_options(service_name, id))
    

@admin.callback_query(F.data.startswith("confirm:delete"))
async def confirm_delete(callback: CallbackQuery, session: AsyncSession):
    id = int(callback.data.split(":")[2])
    bool = await orm_delete_service(session, id)
    if bool:
        await callback.message.edit_text('Ви видалили категорію', reply_markup=await kb.muplti_kb_inline(text="Меню", callback="admin:menu"))
    else:
        await callback.message.edit_text("Не вийшло видалити категорію", reply_markup=await kb.muplti_kb_inline(text="Меню", callback="admin:menu"))


"""
Кінець блоку для видалення непотрібних послуг
"""