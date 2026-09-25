import asyncio
import os
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.orm_queries import sync_working_days, orm_sync_admins

from aiogram import Bot, Dispatcher, F

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


from database.engine import session_maker 
from app.user_handlers import user
from app.admin_handler import admin
from database.engine import create_db, drop_db, session_maker
from middleware.db import DataBaseSession


async def sync_admins_on_startup():
    async with session_maker() as session:
        chat_admins = await bot.get_chat_administrators(chat_id=int(os.getenv("CHAT_ADMIN")))
        admin_ids = [
            member.user.id for member in chat_admins if not member.user.is_bot
        ]
        await orm_sync_admins(session, admin_ids)



async def refresh_working_days():
    async with session_maker() as session:
        await sync_working_days(session)


bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher()


dp.include_router(user)
dp.include_router(admin)


async def on_startup(bot):
    await sync_admins_on_startup()
    await refresh_working_days()

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(refresh_working_days, "cron", hour=0, minute=5)
    scheduler.start()
    
    run_param = False
    if run_param:
        await drop_db()

    await create_db()


async def on_shutdown(bot):
    print('Bot droped')


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await create_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot stoped')
