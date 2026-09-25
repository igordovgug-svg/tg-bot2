from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_queries import orm_is_admin


class IsAdmin(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery], session: AsyncSession) -> bool:
        return await orm_is_admin(session, event.from_user.id)