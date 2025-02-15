from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from database import init_db, save_user_id, get_all_users
from deep_translator import GoogleTranslator
from config import ADMINS, TOKEN
import requests
import telebot
import random
import time

bot = telebot.TeleBot(TOKEN)

GENRES = {
    "🔍 جنایی": "crime",
    "💘 عاشقانه": "romance",
    "🐉 فانتزی": "fantasy",
    "🚀 علمی‌تخیلی": "science fiction",
    "🏰 تاریخی": "history",
    "🎭 درام": "drama",
    "😂 کمدی": "comedy",
    "🕵️ معمایی": "mystery",
    "👻 وحشت": "horror",
    "⚔️ حماسی": "epic",
    "📖 زندگی‌نامه": "biography",
    "🔬 علمی": "science",
    "🎵 موسیقی": "music",
    "🎨 هنر": "art",
    "🧠 فلسفه": "philosophy",
    "🧠 روانشناسی": "psychology",
    "📚 رمان فلسفی": "philosophical novel"


}


@bot.message_handler(commands=['start', 'start start'])
def start(message):
    user_id = message.chat.id
    save_user_id(user_id)
    welcome_text = (
        "👋 سلام! به ربات پیشنهاد کتاب خوش آمدید.\n\n"
        "📚 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("🔎 جستجوی نویسنده"),
        KeyboardButton("📚 جستجو بر اساس ژانر"),
        KeyboardButton("🛠️ ارتباط با پشتیبانی")
    ]

    markup.add(*buttons)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

def translate_text(text, dest_lang="fa"):
    try:
        return GoogleTranslator(source="auto", target=dest_lang).translate(text)
    except Exception as e:
        print(f"⚠️ خطا در ترجمه: {e}")
        return text

def get_book_suggestions(query):
    try:
        print(f"🔍 جستجوی کتاب در ژانر: {query}")

        url = f"https://openlibrary.org/search.json?q={query}&limit=10"
        response = requests.get(url, timeout=10)

        print(f"📡 API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            books_list = data.get("docs", [])

            if not books_list:
                return "📚 کتابی یافت نشد!"

            random.shuffle(books_list)
            book = random.choice(books_list)

            title = book.get("title", "عنوان نامشخص")
            authors = ", ".join(book.get("author_name", ["نویسنده نامشخص"]))
            book_key = book.get("key", "")
            summary = get_book_summary(book_key) if book_key else "📌 خلاصه‌ای موجود نیست!"

            title_fa = translate_text(title)
            authors_fa = translate_text(authors)
            summary_fa = translate_text(summary)

            return f"📖 *{title_fa}*\n✍ نویسنده: {authors_fa}\n📌 خلاصه: {summary_fa}"
        else:
            return f"⚠️ خطای API: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"⚠️ خطا در ارتباط با سرور: {str(e)}"


def get_book_summary(book_key):
    try:
        url = f"https://openlibrary.org{book_key}.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            summary = data.get("description", "📌 خلاصه‌ای موجود نیست!")
            if isinstance(summary, dict):
                summary = summary.get("value", "📌 خلاصه‌ای موجود نیست!")
            return summary[:300] + "..." if len(summary) > 300 else summary
        return "📌 خلاصه‌ای موجود نیست!"

    except requests.exceptions.RequestException:
        return "⚠️ خطا در دریافت خلاصه!"

@bot.message_handler(commands=['show_users'])
def show_users(message):
    if message.chat.id in ADMINS:
        users = get_all_users()

        if users:
            user_count = len(users)
            bot.send_message(message.chat.id, f"تعداد کاربران ثبت شده: {user_count}")
        else:
            bot.send_message(message.chat.id, "هیچ کاربری ثبت نشده است.")

init_db()

@bot.message_handler(func=lambda message: message.text.strip() in GENRES.keys())
def genre_selected(message):
    print(f"Received message: {message.text}")

    genre_farsi = message.text.strip()
    genre_key = GENRES.get(genre_farsi, None)

    if genre_key:
        book_suggestion = get_book_suggestions(genre_key)
        bot.send_message(message.chat.id, f"📚 ژانر انتخابی: *{genre_farsi}*\n\n{book_suggestion}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ ژانر نامعتبر است. لطفاً از دکمه‌های کیبورد استفاده کنید.")

@bot.message_handler(func=lambda message: message.text == "📚 جستجو بر اساس ژانر")
def show_genres_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [KeyboardButton(text=genre) for genre in GENRES.keys()]
    buttons.append(KeyboardButton("🔙 بازگشت به منوی اصلی"))

    markup.add(*buttons)
    bot.send_message(
        message.chat.id,
        "📖 لطفاً ژانر مورد نظر خود را انتخاب کنید:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def back_to_main_menu(message):
    start(message)

author_search_sessions = {}
@bot.message_handler(func=lambda message: message.text == "🔎 جستجوی نویسنده")
def ask_author_name(message):
    # if message.text == "🛠️ ارتباط با پشتیبانی":
    #     return support_contact(message)
    #
    # elif message.text == "📚 جستجو بر اساس ژانر":
    #     return show_genres_menu(message)

    bot.send_message(
        message.chat.id,
        "✍ لطفاً نام نویسنده را به **انگلیسی** وارد کنید.\n\nمثال:\n📌 *J.K. Rowling*\n📌 *George Orwell*\n📌 *Agatha Christie*"
        , parse_mode="Markdown"
    )

    author_search_sessions[message.chat.id] = True

@bot.message_handler(func=lambda message: message.chat.id in author_search_sessions)
def search_books_by_author(message):

    if message.text == "🛠️ ارتباط با پشتیبانی":
        return support_contact(message)

    elif message.text == "📚 جستجو بر اساس ژانر":
        return show_genres_menu(message)

    author_name = message.text.strip()
    del author_search_sessions[message.chat.id]

    books = get_books_by_author(author_name)
    bot.send_message(message.chat.id, books, parse_mode="Markdown")

shown_books = set()

def get_books_by_author(author_name):
    global shown_books

    try:
        url = f"https://openlibrary.org/search.json?author={author_name}&limit=20"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            books_list = data.get("docs", [])

            if not books_list:
                return "❌ هیچ کتابی از این نویسنده یافت نشد."

            random.shuffle(books_list)

            result = "📚 **کتاب‌های پیشنهادی:**\n\n"
            count = 0

            for book in books_list:
                title = book.get("title", "عنوان نامشخص")

                if title in shown_books:
                    continue

                publish_year = book.get("first_publish_year", "نامشخص")
                book_key = book.get("key", "")
                summary = get_book_summary(book_key) if book_key else "📌 خلاصه‌ای موجود نیست!"

                title_fa = translate_text(title)
                summary_fa = translate_text(summary)

                result += f"📖 *{title_fa}*\n"
                result += f"📅 سال انتشار: {publish_year}\n"
                result += f"📌 خلاصه: {summary_fa}\n"
                result += "-----------------\n"

                shown_books.add(title)
                count += 1

                if count >= 3:
                    break

            if count == 0:
                return "✅ همه‌ی کتاب‌های این نویسنده قبلاً نمایش داده شده‌اند!"

            return result

        elif response.status_code == 500:
            return "⚠️ سرور Open Library دچار مشکل شده است. لطفاً بعداً دوباره تلاش کنید."

        else:
            return f"⚠️ خطای API: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"⚠️ خطا در ارتباط با سرور: {str(e)}"

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ شما اجازه‌ی ارسال پیام همگانی را ندارید!")
        return

    try:
        command_parts = message.text.split(" ", 1)
        if len(command_parts) < 2:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه! استفاده صحیح:\n`/broadcast پیام شما`")
            return

        broadcast_text = command_parts[1]
        users = get_all_users()

        if not users:
            bot.send_message(message.chat.id, "❌ هیچ کاربری در دیتابیس یافت نشد!")
            return

        sent_count = 0
        failed_count = 0

        for user in users:
            try:
                user_id = int(user[0])
                bot.send_message(user_id, f"📢 پیام جدید از ادمین:\n\n{broadcast_text}")
                sent_count += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ خطا در ارسال پیام به {user_id}: {str(e)}")
                failed_count += 1

        bot.send_message(message.chat.id, f"✅ پیام به {sent_count} کاربر ارسال شد!\n❌ ارسال به {failed_count} کاربر ناموفق بود.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطای ارسال پیام همگانی: {str(e)}")


@bot.message_handler(commands=['test_users'])
def test_users(message):
    users = get_all_users()
    bot.send_message(message.chat.id, f"📌 تعداد کاربران در دیتابیس: {len(users)}\n\n{users}")


user_support_sessions = {}
@bot.message_handler(func=lambda message: message.text == "🛠️ ارتباط با پشتیبانی")
def support_contact(message):
    btn = KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(btn)
    bot.send_message(
        message.chat.id,
        "📩 لطفاً پیام خود را ارسال کنید. پیام شما مستقیماً برای پشتیبانی فرستاده خواهد شد.",
        reply_markup=markup
    )
    user_support_sessions[message.chat.id] = True

@bot.message_handler(func=lambda message: message.chat.id in user_support_sessions)
def handle_support_message(message):
    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد! پشتیبانی به زودی پاسخ خواهد داد.")

    forward_to_admin(message)

    del user_support_sessions[message.chat.id]

def forward_to_admin(message):
    user_id = message.chat.id
    user_info = f"👤 **کاربر:** {message.from_user.first_name} (@{message.from_user.username})\n🆔 **آیدی:** {message.from_user.id}"

    for admin in ADMINS:
        try:
            bot.send_message(admin, user_info)
            bot.forward_message(admin, message.chat.id, message.message_id)
            bot.send_message(admin,
                f"✉️ برای پاسخ به این کاربر از دستور زیر استفاده کنید:\n"
                f"`/reply {message.chat.id} پیام شما`",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ خطا در ارسال پیام به ادمین {admin}: {str(e)}")

    # bot.send_message(message.chat.id, "✅ پیام شما ارسال شد! پشتیبانی به زودی پاسخ خواهد داد.")

    if user_id in user_support_sessions:
        del user_support_sessions[user_id]

@bot.message_handler(commands=['reply'])
def reply_to_user(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ شما مجاز به استفاده از این دستور نیستید.")
        return

    try:
        command_parts = message.text.split(" ", 2)

        if len(command_parts) < 3:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه! استفاده صحیح:\n`/reply USER_ID پیام شما`",
                             parse_mode="Markdown")
            return

        user_id = command_parts[1]
        if not user_id.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر باید عدد باشد!")
            return

        user_id = int(user_id)
        reply_message = command_parts[2]

        bot.send_message(user_id, f"📩 **پاسخ پشتیبانی:**\n{reply_message}")
        bot.send_message(message.chat.id, "✅ پیام شما به کاربر ارسال شد.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ خطا در ارسال پاسخ: {str(e)}")



while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=20)
    except Exception as e:
        print(f"Polling Error: {e}")
        time.sleep(5)