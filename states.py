from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    MessageEntity,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from asgiref.sync import sync_to_async
from db.models import Feedback

MENU, FIRST_NAME, LAST_NAME, PHONE, FEEDBACK = range(5)


def menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Yangi fikr")],
            [KeyboardButton("Mening fikrlarim")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Telefon raqam yuborish", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom!", reply_markup=menu_keyboard())
    return MENU


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Quyidagi menyuni tanlang!", reply_markup=menu_keyboard()
    )
    return MENU


async def new_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ismingizni kiriting!")
    return FIRST_NAME


async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.update(
        {
            "first_name": update.message.text,
        }
    )
    print(context.chat_data)
    await update.message.reply_text("Ajoyib! Ana endi familiyanginzi kiriting!")
    return LAST_NAME


async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.update(
        {
            "last_name": update.message.text,
        }
    )
    print(context.chat_data)
    await update.message.reply_text(
        "Telefon raqamingizni kiriting, yoki pastdagi knopkani bosing!",
        reply_markup=phone_keyboard(),
    )
    return PHONE


async def last_name_resend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Familiyangizni kiriting!")


async def phone_entity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_number_entity = pne = list(
        filter(lambda e: e.type == "phone_number", update.message.entities)
    )[0]
    phone_number = update.message.text[pne.offset : pne.offset + pne.length]
    context.chat_data.update(
        {
            "phone_number": phone_number,
        }
    )
    await update.message.reply_text("Endi fikringizni qoldiring")
    return FEEDBACK


async def phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    context.chat_data.update(
        {
            "phone_number": "+" + contact.phone_number,
        }
    )
    await update.message.reply_text("Endi fikringizni qoldiring!")
    return FEEDBACK


async def phone_resend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Telefon raqamingizni kiriting, yoki pastdagi knopkani bosing",
        reply_markup=phone_keyboard(),
    )


def save_feedback(feedback_data):
    feedback = Feedback.objects.create(**feedback_data)
    return feedback


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.update(
        {
            "feedback": update.message.text,
        }
    )
    await update.message.reply_text("Fikringiz uchun raxmat!")
    cd = context.chat_data

    feedback = {
        "first_name": cd["first_name"][0:255],
        "last_name": cd["last_name"][0:255],
        "phone_number": cd["phone_number"][0:63],
        "feedback": cd["feedback"],
        "user_id": update.effective_user.id,
    }
    saved_feedback = await sync_to_async(save_feedback)(feedback)
    print(saved_feedback.first_name)
    return await menu(update, context)


async def feedback_resend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fikringizni matn orqali qoldiring")


def get_user_feedback(user_id):
    feedbacks = Feedback.objects.order_by("-id").filter(user_id=user_id)[:5]
    return feedbacks


async def all_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Mening ohirgi 5ta fikrim")

    feedbacks = await sync_to_async(get_user_feedback)(update.effective_user.id)

    feedbacks = await sync_to_async(list)(feedbacks)
    if len(feedbacks) == 0:
        await update.message.reply_text("Siz hech qanday fikr qoldirmagansiz!")
    else:
        for feedback in feedbacks:
            await update.message.reply_text(
                f"{feedback.feedback}\n\n{feedback.first_name} {feedback.last_name}"
            )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hayr!", reply_markup=ReplyKeyboardRemove())


conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.ALL, start)],
    states={
        MENU: [
            MessageHandler(filters.Regex(r"^Yangi fikr$"), new_feedback),
            MessageHandler(filters.Regex(r"^Mening fikrlarim$"), all_feedback),
            MessageHandler(filters.ALL, menu),
        ],
        FIRST_NAME: [
            MessageHandler(filters.TEXT, first_name),
            MessageHandler(filters.ALL, new_feedback),
        ],
        LAST_NAME: [
            MessageHandler(filters.TEXT, last_name),
            MessageHandler(filters.ALL, last_name_resend),
        ],
        PHONE: [
            MessageHandler(
                filters.TEXT & filters.Entity(MessageEntity.PHONE_NUMBER), phone_entity
            ),
            MessageHandler(filters.CONTACT, phone_contact),
            MessageHandler(filters.ALL, phone_resend),
        ],
        FEEDBACK: [
            MessageHandler(filters.TEXT, feedback),
            MessageHandler(filters.ALL, feedback_resend),
        ],
    },
    fallbacks=[CommandHandler("stop", stop)],
)
