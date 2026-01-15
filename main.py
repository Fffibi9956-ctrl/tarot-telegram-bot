import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, ConversationHandler,
    filters
)
from config import Config
from database import Database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ASKING_QUESTION = 1
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    if user.id == Config.ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("🎴 Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("🔮 Я таролог", callback_data="i_am_tarot")],
            [InlineKeyboardButton("⚡ Модерация", callback_data="moderation")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🎴 Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("🔮 Я таролог", callback_data="i_am_tarot")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ Добро пожаловать в бота для тарологов! ✨\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "ask_question":
        await query.edit_message_text(
            "🎴 *Задайте вопрос тарологу:*\n\nПросто напишите его в чат:",
            parse_mode="Markdown"
        )
        return ASKING_QUESTION
    
    elif query.data == "i_am_tarot":
        user_data = db.get_user_by_id(query.from_user.id)
        if user_data and user_data[4] == Config.ROLE_TAROT:
            await show_tarot_dashboard(query)
        else:
            await query.edit_message_text(
                "🔮 Чтобы стать тарологом, обратитесь к администратору (команда /promote)."
            )
    
    elif query.data == "moderation":
        if query.from_user.id == Config.ADMIN_ID:
            await show_moderation_panel(query)
        else:
            await query.edit_message_text("❌ Нет доступа.")
    
    elif query.data == "back_to_start":
        await start_callback(query)
    
    elif query.data.startswith("answer_"):
        question_id = int(query.data.split("_")[1])
        context.user_data["answering_question"] = question_id
        await query.edit_message_text(f"📝 Ответ на вопрос #{question_id}:\n\nНапишите ответ:")
        return ASKING_QUESTION
    
    elif query.data.startswith("moderate_"):
        parts = query.data.split("_")
        question_id, action = int(parts[1]), parts[2]
        approved = (action == "approve")
        
        result = db.moderate_question(question_id, approved, query.from_user.id)
        status = "одобрен" if approved else "отклонен"
        await query.edit_message_text(f"✅ Вопрос #{question_id} {status}!")
        
        if result:
            user_id = result[0]
            try:
                await context.bot.send_message(
                    user_id,
                    f"✅ Ваш вопрос #{question_id} прошел модерацию!" if approved 
                    else f"❌ Ваш вопрос #{question_id} отклонен модерацией."
                )
            except:
                logger.warning(f"Не удалось отправить уведомление {user_id}")

async def show_tarot_dashboard(query):
    questions = db.get_unanswered_questions()
    
    if not questions:
        await query.edit_message_text("📭 Нет новых вопросов.")
        return
    
    keyboard = []
    for q in questions:
        text = q[1][:50] + "..." if len(q[1]) > 50 else q[1]
        keyboard.append([InlineKeyboardButton(f"❓ {q[0]}: {text}", callback_data=f"answer_{q[0]}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])
    await query.edit_message_text(
        f"🔮 Доступно вопросов: {len(questions)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_moderation_panel(query):
    questions = db.get_questions_for_moderation()
    
    if not questions:
        await query.edit_message_text("✅ Нет вопросов на модерации.")
        return
    
    for q in questions:
        text = f"*Вопрос #{q[0]} от {q[3]}*:\n{q[1]}"
        if q[2]:
            text += f"\n\n*Ответ от {q[4]}*:\n{q[2]}"
        
        keyboard = [[
            InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_{q[0]}_approve"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_{q[0]}_reject")
        ]]
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    
    await query.edit_message_text(f"⚡ Вопросов на модерации: {len(questions)}")

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "answering_question" in context.user_data:
        question_id = context.user_data.pop("answering_question")
        answer_text = update.message.text
        db.add_answer(question_id, update.effective_user.id, answer_text)
        
        question_info = db.get_question_info(question_id)
        if question_info:
            try:
                await context.bot.send_message(
                    question_info[0],
                    f"✨ Вы получили ответ!\n\n*Ответ:* {answer_text}"
                )
            except:
                pass
        
        await update.message.reply_text("✅ Ответ отправлен!")
    else:
        user_id = update.effective_user.id
        question_text = update.message.text
        question_id = db.add_question(user_id, question_text)
        
        try:
            await context.bot.send_message(
                Config.ADMIN_ID,
                f"📨 Новый вопрос #{question_id} от @{update.effective_user.username}:\n{question_text}"
            )
        except:
            pass
        
        await update.message.reply_text("✅ Вопрос отправлен на модерацию!")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END

async def start_callback(query):
    await start(query.message, None)

async def admin_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_ID:
        await update.message.reply_text("❌ Только админ.")
        return
    
    if not context.args:
        await update.message.reply_text("Используйте: /promote @username")
        return
    
    username = context.args[0].replace("@", "")
    db.set_user_role(0, Config.ROLE_TAROT)  # Здесь нужен реальный поиск по username
    await update.message.reply_text(f"✅ @{username} теперь таролог!")

async def my_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = db.get_user_questions(update.effective_user.id)
    
    if not questions:
        await update.message.reply_text("📭 У вас нет вопросов.")
        return
    
    text = "📋 Ваши вопросы:\n\n"
    for q in questions:
        status = "✅" if q[2]=="answered" else "🕒" if q[2]=="new" else "❌"
        text += f"{status} #{q[0]}: {q[1]}\n"
        if q[3]:
            text += f"   Ответ: {q[3]}\n"
        text += "\n"
    
    await update.message.reply_text(text)

def main():
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^ask_question$")],
        states={ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promote", admin_promote))
    application.add_handler(CommandHandler("myquestions", my_questions))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
