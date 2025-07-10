from http.client import responses

import telebot
import requests
import datetime
import os
import locale
from dotenv import  load_dotenv

from telebot import types

load_dotenv()

weekdays = {
    0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг',
    4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
}
months = {
    1: 'января', 2: 'фев', 3: 'мар', 4: 'апр', 5: 'мая', 6: 'июн',
    7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, 'Russian')

BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')
WEATHER_API_TOKEN = os.getenv('WEATHER_API_TOKEN')


bot = telebot.TeleBot(BOT_API_TOKEN)

def get_weather(city_name):
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={WEATHER_API_TOKEN}&units=metric&lang=ru'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        temp = data['main']['temp']
        description = data['weather'][0]['description']
        city = data['name']
        feels_like = data['main']['feels_like']
        wind = data['wind']['speed']
        pressure = data['main']['pressure']
        humidity = data['main']['humidity']

        now = datetime.datetime.now()

        actual_time = now.strftime("%H:%M")

        weather_report = (f"Погода в городе {city} на {actual_time}:\n"
                          f"🌡️ Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                          f"☁️ На небе: {description.capitalize()}\n"
                          f"💨 Ветер: {wind} м/с\n"
                          f"💧 Влажность: {humidity} %\n"
                          f"⏲️Давление: {pressure} мм рт.ст.")
        print(weather_report)
        return weather_report, None
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
             return None, f"Город '{city_name}' не найден. Проверьте название."
        else:
             return None, f"Произошла ошибка с сервисом погоды. Код: {err.response.status_code}"


def get_forecast(city_name):
    url = f'https://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={WEATHER_API_TOKEN}&units=metric&lang=ru'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        forecast_report = f"Прогноз погоды для города {data['city']['name']}:\n"

        forecast_by_day = {}

        forecast_times = ['09:00:00', '12:00:00', '21:00:00']

        for forecast in data['list']:
            date_str = forecast['dt_txt'].split()[0]
            time_str = forecast['dt_txt'].split()[1]

            if time_str in forecast_times:
                if date_str not in forecast_by_day:
                    forecast_by_day[date_str] = []

                temp = round(forecast['main']['temp'])
                description = forecast['weather'][0]['description']

                time_of_day = ""
                if time_str == '09:00:00':
                    time_of_day = "Утро☀️"
                elif time_str == '12:00:00':
                    time_of_day = "День 🏙️ "
                elif time_str == '21:00:00':
                    time_of_day = "Вечер 🌙"
                if time_of_day:
                    forecast_by_day[date_str].append(f"  - {time_of_day}: {temp}°C, {description.capitalize()}")

        for date, daily_reports in sorted(forecast_by_day.items()):
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            day_of_week_num = date_obj.weekday()
            day_num = date_obj.day
            month_num = date_obj.month
            formatted_date = f"{weekdays[day_of_week_num]}, {day_num} {months[month_num]}"
            forecast_report += f"\n *{formatted_date}* \n"
            forecast_report += "\n".join(daily_reports)
        return forecast_report , None

    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
             return None, f"Город '{city_name}' не найден. Проверьте название."
        else:
             return None, f"Произошла ошибка с сервисом погоды. Код: {err.response.status_code}"

@bot.message_handler(commands = ['start','help'])
def send_welcome(message):
    reply_text = "Привет, я погодный бот!\nОтправь мне название /weather [название города] и я отправлю тебе актуальную погоду!"
    bot.reply_to(message,reply_text)

@bot.message_handler(commands=['weather'])
def send_weather(message):
    try:
        city_name = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Пожалуйста, укажите город после команды.\n(Например /weather Лондон)")
        return

    weather_report, error_message = get_weather(city_name)
    if error_message:
        bot.reply_to(message,error_message)
        return
    markup = types.InlineKeyboardMarkup()
    button_1 = types.InlineKeyboardButton("Обновить 🔄", callback_data=f"refresh_{city_name}")
    button_2 = types.InlineKeyboardButton("Прогноз на 5 дней 🌤️",callback_data=f"forecast_{city_name}")
    markup.add(button_1)
    markup.add(button_2)

    bot.send_message(message.chat.id,weather_report, reply_markup = markup,parse_mode='Markdown')

@bot.callback_query_handler(func = lambda call: call.data.startswith('refresh_'))
def handle_refresh(call):
    bot.answer_callback_query(call.id)
    city_name = call.data.split('_')[1]
    new_weather_report, error_message = get_weather(city_name)

    bot.edit_message_text(
        text = new_weather_report,
        chat_id = call.message.chat.id,
        message_id= call.message.message_id,
        reply_markup = call.message.reply_markup,
        parse_mode='Markdown'
    )


@bot.callback_query_handler(func= lambda call: call.data.startswith('forecast_'))
def handle_forecast(call):
    bot.answer_callback_query(call.id)
    city_name = call.data.split('_')[1]
    forecast_report, error_message = get_forecast(city_name)
    if error_message:
        bot.answer_callback_query(call.id, text=error_message, show_alert=True)
        return

    markup = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{city_name}")
    markup.add(back_button)

    bot.edit_message_text(
        text=forecast_report,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func= lambda call:call.data.startswith('back_'))
def handle_back(call):
    bot.answer_callback_query(call.id)
    city_name = call.data.split('_')[1]
    new_weather_report, error_message = get_weather(city_name)

    markup = types.InlineKeyboardMarkup()
    button_1 = types.InlineKeyboardButton("Обновить 🔄", callback_data=f"refresh_{city_name}")
    button_2 = types.InlineKeyboardButton("Прогноз на 5 дней 🌤️",callback_data=f"forecast_{city_name}")
    markup.add(button_1)
    markup.add(button_2)

    bot.edit_message_text(
        text=new_weather_report,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.message_handler(content_types=['text'])
def handle_unknown_text(message):
    reply_text =  (
        "Я не понимаю эту команду 🤷‍♂️\n"
        "Чтобы узнать погоду, используйте команду в формате:\n"
        "`/weather <название города>`"
    )
    bot.reply_to(message, reply_text,parse_mode='Markdown')

bot.infinity_polling()