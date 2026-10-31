import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات شما
TOKEN = "9159091337:AAHDJXhzY5z5BwXe8g9-bhQGc2gXmwyROjI"

# ساختار داده‌ها در حافظه
couriers_queue = []
registered_couriers = {}
active_orders = {}
order_counter = 1

# دستور شروع (Start) - دو زبانه (Türkçe / English)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("🛵 Kurye Kayıt / Register as Courier", callback_data="register_courier")
        ],
        [
            InlineKeyboardButton("📋 Sırayı Gör / View Queue", callback_data="show_queue")
        ],
        [
            InlineKeyboardButton("🍔 Sipariş Ver (Restoran) / New Order (Restaurant)", callback_data="new_order_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Merhaba {user.first_name}! Otomatik Kurye ve Restoran Yönetim Sistemine hoş geldiniz.\n"
        f"Welcome to the Automated Courier & Restaurant Management System.\n\n"
        f"Lütfen bir seçenek belirleyin / Please choose an option:",
        reply_markup=reply_markup
    )

# مدیریت دکمه‌ها (دو زبانه)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if query.data == "register_courier":
        if user_id not in couriers_queue:
            couriers_queue.append(user_id)
            registered_couriers[user_id] = user_name
            position = len(couriers_queue)
            await query.edit_message_text(
                text=f"✅ Başarıyla kurye olarak kaydoldunuz! / Successfully registered as a courier!\n\n"
                     f"📍 Sıradaki yeriniz / Your position in queue: #{position}"
            )
        else:
            position = couriers_queue.index(user_id) + 1
            await query.edit_message_text(
                text=f"⚠️ Zaten sıradasınız. / You are already in the queue.\n\n"
                     f"📍 Sıradaki yeriniz / Your position in queue: #{position}"
            )

    elif query.data == "show_queue":
        if not couriers_queue:
            await query.edit_message_text(text="📭 Şu anda sırada kurye yok. / No couriers in the queue right now.")
        else:
            queue_text = "📋 **Kurye Sırası / Courier Queue:**\n\n"
            for index, cid in enumerate(couriers_queue, start=1):
                c_name = registered_couriers.get(cid, "Bilinmeyen / Unknown")
                icon = "👑 (Şu anki nöbetçi / Current)" if index == 1 else ""
                queue_text += f"{index}. {c_name} {icon}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Ana Menü / Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(text=queue_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "new_order_menu":
        await query.edit_message_text(
            text="🍔 **Restoran İçin Sipariş Kaydı / Restaurant Order Registration:**\n\n"
                 "Sipariş göndermek için şu formatı kullanın / Use this format to send an order:\n"
                 "`/order RestoranAdi | TeslimatAdresi`\n\n"
                 "Örnek / Example:\n"
                 "`/order BurgerKing | Taksim Meydanı No:12`",
            parse_mode="Markdown"
        )

    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🛵 Kurye Kayıt / Register as Courier", callback_data="register_courier")],
            [InlineKeyboardButton("📋 Sırayı Gör / View Queue", callback_data="show_queue")],
            [InlineKeyboardButton("🍔 Sipariş Ver (Restoran) / New Order", callback_data="new_order_menu")]
        ]
        await query.edit_message_text(text="Ana Menü / Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("deliver_"):
        order_id = int(query.data.split("_")[1])
        if order_id in active_orders:
            order_info = active_orders.pop(order_id)
            delivered_courier_id = order_info['courier_id']
            
            # انتقال پیک به انتهای صف
            if delivered_courier_id in couriers_queue:
                couriers_queue.remove(delivered_courier_id)
                couriers_queue.append(delivered_courier_id)
            
            await query.edit_message_text(
                text="✅ Sipariş başarıyla teslim edildi ve sıranın sonuna taşındınız. Eline sağlık!\n"
                     "✅ Order delivered successfully and you moved to the end of the queue. Good job!"
            )
            
            # اطلاع به نفر بعدی صف
            if couriers_queue:
                next_courier = couriers_queue[0]
                try:
                    await context.bot.send_message(
                        chat_id=next_courier, 
                        text="🔔 Sıra size geldi! Yeni sipariş bekleniyor.\n"
                             "🔔 It's your turn! Waiting for a new order."
                    )
                except Exception:
                    pass
        else:
            await query.edit_message_text(text="⚠️ Bu sipariş zaten kapatıldı. / This order is already closed.")

# دستور ثبت سفارش (دو زبانه)
async def make_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global order_counter
    text = update.message.text.replace("/order", "").strip()
    
    if not text or "|" not in text:
        await update.message.reply_text(
            "❌ Format hatalı! Lütfen şu şekilde gönderin:\n"
            "❌ Wrong format! Please send like this:\n"
            "`/order RestoranAdi | TeslimatAdresi`",
            parse_mode="Markdown"
        )
        return

    parts = text.split("|")
    restaurant_name = parts[0].strip()
    address = parts[1].strip()

    if not couriers_queue:
        await update.message.reply_text(
            "❌ Şu anda sırada aktif kurye bulunmuyor.\n"
            "❌ There are no active couriers in the queue."
        )
        return

    # ارسال به نفر اول صف
    target_courier = couriers_queue[0]
    current_order_id = order_counter
    order_counter += 1

    active_orders[current_order_id] = {
        "restaurant": restaurant_name,
        "address": address,
        "courier_id": target_courier
    }

    keyboard = [[InlineKeyboardButton("✅ Siparişi Teslim Ettim / Delivered", callback_data=f"deliver_{current_order_id}")]]
    
    try:
        await context.bot.send_message(
            chat_id=target_courier,
            text=f"🚨 **Yeni Sipariş Var! / New Order!**\n\n"
                 f"🏪 Restoran / Restaurant: {restaurant_name}\n"
                 f"📍 Adres / Address: {address}\n\n"
                 f"Teslimattan sonra aşağıdaki butona tıklayın:\n"
                 f"Click the button below after delivery:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ #${current_order_id} nolu sipariş başarıyla ilk kuryeye iletildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata / Error: {e}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("order", make_order))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot çalışıyor ve Türkçe/İngilizce destekliyor...")
    application.run_polling()

if __name__ == '__main__':
    main()
    import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
