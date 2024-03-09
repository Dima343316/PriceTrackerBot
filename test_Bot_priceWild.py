import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
import logging
import aiohttp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dataBase_class import *
from dotenv import load_dotenv
import os


load_dotenv()
# Инициализация бота и диспетчера
API_TOKEN = 'your token'  # Замените на свой токен
bot = Bot(os.getenv.('TOKEN'))
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())


# Получение информации о товаре с помощью API Wildberries
# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Это бот для получения информации о товарах и управления уведомлениями.",
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="Получить информацию по товару", callback_data="get_info")
                                ],
                                [
                                    InlineKeyboardButton(text="Остановить уведомления", callback_data="unsubscribe")
                                ],
                                [
                                    InlineKeyboardButton(text="Получить информацию из БД", callback_data="get_db_info")
                                ]
                            ]
                        ))


# Получение информации о товаре с помощью API Wildberries
async def get_product_info(product_article):
    async with aiohttp.ClientSession() as session:
        url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={product_article}"
        async with session.get(url) as response:
            result_data = await response.json()

    try:
        product = result_data['data']['products'][0]
        product_name = product['name']
        product_price = product['priceU']
        product_rating = product['rating']
        product_volume = product['volume']
        product_info = f"Название: {product_name}\nАртикул: {product_article}\nЦена: {product_price}\nРейтинг: {product_rating}\nКоличество товара на всех складах: {product_volume}"
    except (KeyError, IndexError):
        return "Информация о товаре не найдена."

    return product_info, product_name, product_price, product_rating, product_volume




# Обработчик нажатия на кнопку "Получить информацию по товару"
@dp.callback_query_handler(lambda callback_query: callback_query.data == "get_info")
async def get_info_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.reply("Введите артикул товара с Wildberries.")

# Обработчик ввода артикула товара
@dp.message_handler()
async def handle_product_article(message: types.Message):
    product_article = message.text

    # Получение информации о товаре

    product_info = await get_product_info(product_article)
    if product_info == "Информация о товаре не найдена.":
        await message.reply(product_info)
    else:
    # Преобразование кортежа в строку
        product_info_str = f"Название: {product_info[1]}\nАртикул: {product_article}\nЦена: {product_info[2]}\nРейтинг: {product_info[3]}\nКоличество товара на всех складах: {product_info[4]}"

    # Отправка информации о товаре с кнопкой "Подписаться"
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="Подписаться", callback_data=f"subscribe_{product_article}")
        )
        await message.reply(product_info_str, reply_markup=keyboard)

async def send_product_notification(user_id, product_article):
    product_info, _, _, _, _ = await get_product_info(product_article)
    await bot.send_message(user_id, product_info)


# Запуск цикла отправки уведомлений каждые 5 минут
async def send_notifications():
    while True:
        await asyncio.sleep(10)  # Ожидание 5 минут

        # Получение всех подписок из базы данных
        session = SessionLocal()
        subscriptions = session.query(Subscription).all()

        # Отправка уведомлений каждому подписчику
        for subscription in subscriptions:
            await send_product_notification(subscription.user_id, subscription.product_article)

        # Закрытие сеанса после обработки всех подписок
        session.close()

# Обработчик кнопки "Подписаться"
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('subscribe_'))
async def subscribe_to_product(callback_query: types.CallbackQuery):
    product_article = callback_query.data.split('_')[1]  # Получаем артикул товара из данных кнопки
    user_id = callback_query.from_user.id

    # Проверка, подписан ли пользователь уже на этот товар
    session = SessionLocal()
    existing_subscription = session.query(Subscription).filter(Subscription.user_id == user_id, Subscription.product_article == product_article).first()
    session.close()

    if existing_subscription:
        await callback_query.answer("Вы уже подписаны на рассылку", show_alert=True)
    else:
        # Получение информации о товаре
        product_info, product_name, product_price, product_rating, product_volume = await get_product_info(product_article)

        # Сохранение подписки в базе данных
        session = SessionLocal()
        subscription = Subscription(user_id=user_id, product_article=product_article, product_name=product_name, product_price=product_price, product_rating=product_rating, product_volume=product_volume)
        session.add(subscription)
        session.commit()

        # Запуск цикла отправки уведомлений для этой подписки
        asyncio.create_task(send_notifications())

        session.close()

        await callback_query.answer("Вы успешно подписались на уведомления!")


@dp.callback_query_handler(lambda callback_query: callback_query.data == "unsubscribe")
async def unsubscribe_from_product(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    session = SessionLocal()
    session.query(Subscription).filter(Subscription.user_id == user_id).delete()
    session.commit()

    # Отправка сообщения о успешной отписке
    await bot.send_message(user_id, "Вы успешно отписались от уведомлений!")

    session.close()
    await callback_query.answer("Вы успешно отписались от уведомлений!")

@dp.callback_query_handler(lambda callback_query: callback_query.data == "get_db_info")
async def get_db_info(callback_query: types.CallbackQuery):
    session = SessionLocal()
    subscriptions = session.query(Subscription).order_by(Subscription.id.desc()).limit(5).all()

    for subscription in subscriptions:
        user_id = subscription.user_id
        product_article = subscription.product_article

        # Получение информации о товаре
        product_info = await get_product_info(product_article)

        # Проверка наличия информации о товаре
        if product_info == "Информация о товаре не найдена.":
            message = f"Пользователь {user_id}, информация о товаре с артикулом {product_article} не найдена."
        else:
            # Преобразование кортежа в строку
            product_info_str = f"Название: {product_info[1]}\nАртикул: {product_article}\nЦена: {product_info[2]}\nРейтинг: {product_info[3]}\nКоличество товара на всех складах: {product_info[4]}"

            # Формирование сообщения о подписке и товаре
            message = f"Информация о подписке пользователя {user_id} на товар с артикулом {product_article}:\n{product_info_str}"

        # Отправка сообщения в личный чат пользователя
        await bot.send_message(user_id, message)

    session.close()
    await callback_query.answer("Информация о подписках отправлена в личные чаты пользователей.")
# Запуск бота
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
