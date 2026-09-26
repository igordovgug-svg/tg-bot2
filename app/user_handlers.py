from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timedelta, date as date_cls

import app.keyboards as kb


from database.orm_queries import get_available_days, get_working_hours, create_booking, get_user_booking, cancel_booking, orm_get_services, orm_get_services_by_id, orm_is_admin


user = Router()

PAGE_SIZE = 5  

@user.message(CommandStart())
async def start(mesage: Message):
    await mesage.answer("Нажміть кнопку нижче👇", reply_markup=await kb.muplti_kb_inline(text="Меню", callback="start:menu"))


@user.callback_query(F.data == "start:menu")
async def start_menu(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    is_admin = orm_is_admin(session, user_id)

    await callback.message.edit_text('Це бот для запису/бронювання місця на послуги, нижче виберіть що вам потрібно👇', reply_markup=await kb.start_kb(is_admin))

""""
Початок блоку для резервування дати та часу на послугу
"""


# показує доступні послуги
@user.callback_query(F.data =='book:service')
async def service(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    services = await orm_get_services(session)

    await callback.message.edit_text('Виберіть послугу', reply_markup=await kb.build_services_keyboard(services=services))


# генерує інлайнову клавіатуру з доступними днями для запису
@user.callback_query(F.data.startswith('service:'))
async def show_days(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    service_id = int(callback.data.split(':')[1])

    service_name = await orm_get_services_by_id(session, service_id)

    await state.update_data(service_id=service_id, service_name=service_name)

    days = await get_available_days(session)
    

    await callback.message.edit_text(
        "Оберіть зручний день:",
        reply_markup=await kb.build_days_keyboard(days)
    )


# генерує інлайнову клавіатуру з доступним часом для запису
@user.callback_query(F.data.startswith('day:'))
async def show_time_slots(callback: CallbackQuery, session: AsyncSession):
    day_str = callback.data.split(":")[1]
    selected_day = date_cls.fromisoformat(day_str)

    hours = await get_working_hours(session, selected_day)
    if not hours:
        await callback.answer("Цей день недоступний", show_alert=True)
        return

    start, end = hours
    slots = []
    current = datetime.combine(selected_day, start)
    end_dt = datetime.combine(selected_day, end)

    while current < end_dt:
        slots.append(current.time())
        current += timedelta(minutes=30)

    await callback.message.edit_text(
        f"Оберіть час на {selected_day.strftime('%d.%m')}:",
        reply_markup=await kb.build_time_keyboard(slots, selected_day)
    )


# проміжне меню для підтвердженя сапису
@user.callback_query(F.data.startswith('time:'))
async def confirm_booking(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    _, day_str, time_str = callback.data.split(':', 2)  # split(':', 2) — фікс бага з часом

    await state.update_data(day_str=day_str, time_str=time_str)
        
    data = await state.get_data()
    
    selected_day = date_cls.fromisoformat(day_str)
    slot_time = datetime.strptime(time_str, '%H:%M').time() 
    service_name = data.get('service_name')
   

    await callback.message.edit_text(
        f"✅ Запис підтверджено!\n"
        f"Послуга: {service_name}\n"
        f"Дата: {selected_day.strftime('%d.%m')}\n"
        f"Час: {slot_time.strftime('%H:%M')}",
        reply_markup=kb.confirm_booking
    )


# ця частина перевіряє чи є вільне місце для запису на послугу якщо немає показує плашку на жадь зайнято і ви дальше вибиражте новий час
@user.callback_query(F.data == 'confirm:booking')
async def accept(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()

    service_id = data.get('service_id')
    day_str = data.get('day_str')
    time_str = data.get("time_str")

    selected_day = date_cls.fromisoformat(day_str)
    slot_time = datetime.strptime(time_str, '%H:%M').time() 

    
    booking = await create_booking(session, callback.from_user.id, service_id, selected_day, slot_time) #перевіряє чи на даний час і жату вже запис
    
    if booking is None:
        await callback.answer("На жаль, цей час вже зайнято 😔", show_alert=True)
        return

    await callback.message.edit_text("Запис успішно створений", reply_markup=await kb.muplti_kb_inline(text="Меню", callback="start:menu"))

""""
Кінець блоку резервування
"""


"""
Початок блоку для відміни своїх записів 
"""
@user.callback_query(F.data == 'my:services')
async def my_bookings(callback: CallbackQuery, session: AsyncSession):
    await render_bookings_page(callback, session, page=1)


@user.callback_query(F.data.startswith('mypage:'))
async def my_bookings_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(':')[1])
    await render_bookings_page(callback, session, page)


@user.callback_query(F.data.startswith('cancel:'))
async def cancel_booking_handler(callback: CallbackQuery, session: AsyncSession):
    booking_id = int(callback.data.split(':')[1])
    ok = await cancel_booking(session, booking_id, callback.from_user.id)
    await callback.answer("Запис скасовано ✅" if ok else "Не вдалося скасувати", show_alert=not ok)
    await render_bookings_page(callback, session, page=1)

"""
Кінець блоку для скасування своїх записів
"""


# будує клавіатуру в вашими доступними послугами з пагінацією 
async def render_bookings_page(callback: CallbackQuery, session: AsyncSession, page: int):
    bookings, total = await get_user_booking(session, callback.from_user.id, page, PAGE_SIZE)

    if not bookings:
        await callback.message.edit_text("У вас немає активних записів.")
        return

    await callback.message.edit_text(
        "Ваші записи:",
        reply_markup=await kb.build_bookings_keyboard(bookings, page, total, PAGE_SIZE)
    )


