import os
import pandas as pd
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
from datetime import datetime
from admin_tools import setup_admin_tools
from dotenv import load_dotenv

load_dotenv()

# Bot credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# File paths
EXCEL_FILE = 'result.xlsx'
SHEET_NAME = 'Sheet1'
USER_STUDENT_MAP_FILE = 'user_student_map.json'
ADMIN_LIST_FILE = 'admin_list.json'
STUDENT_USAGE_FILE = 'student_usage.json'
INITIAL_ADMIN_ID = 933493534

# Helper functions
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

class StudentResultBot:
    def __init__(self):
        self.app = Client("student_result_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        self.user_student_map = load_json(USER_STUDENT_MAP_FILE, {})
        self.admin_list = load_json(ADMIN_LIST_FILE, [INITIAL_ADMIN_ID])
        self.student_usage = load_json(STUDENT_USAGE_FILE, {})
        self.setup_handlers()
        setup_admin_tools(self)

    def save_state(self):
        save_json(USER_STUDENT_MAP_FILE, self.user_student_map)
        save_json(ADMIN_LIST_FILE, self.admin_list)
        save_json(STUDENT_USAGE_FILE, self.student_usage)

    def setup_handlers(self):
        @self.app.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            await self.handle_start(message)

        @self.app.on_message(filters.command("adminlist"))
        async def admin_list_command(client: Client, message: Message):
            await self.handle_admin_list(message)

        @self.app.on_message(filters.command("result"))
        async def result_command(client: Client, message: Message):
            await self.handle_result(message)

        @self.app.on_message(filters.command("admin"))
        async def add_admin_command(client: Client, message: Message):
            await self.handle_add_admin(message)

        @self.app.on_message(filters.command("who"))
        async def whois_command(client: Client, message: Message):
            await self.handle_whois(message)

        @self.app.on_message(filters.command("remove"))
        async def remove_admin_command(client: Client, message: Message):
            await self.handle_remove_admin(message)

        @self.app.on_message(filters.text & ~filters.regex(r'^/'))
        async def id_only_message(client: Client, message: Message):
            await self.handle_result(message)

    async def handle_start(self, message: Message):
        await message.reply_text(
            "👋 <b>أهلاً وسهلاً في بوت النتيجة 📚</b>\n\n"
            "هنا تقدر تعرف نتيجتك بكل سهولة ✨\n\n"
            "🔹 <b>علشان تجيب نتيجتك:</b>\n"
            " ➤ ابعت <b> رقم الجلوس  مباشرة \n"
            " ➤ أو استخدم الأمر: <code>/result رقم الجلوس \n\n"
            "🔐 أول ما تبعت الكود، هنربطه بحسابك تلقائيًا."
       )
    async def get_student_info_by_id(self, student_id: str) -> dict:
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
            df.columns = df.columns.str.strip()  # clean up column headers
            df.rename(columns={'ID': 'id', 'اسم الطالب': 'Name'}, inplace=True)
            df['id'] = df['id'].astype(str).str.strip().str.replace('.0', '', regex=False)
            student_row = df[df['id'] == str(student_id)]
            if not student_row.empty:
                return {
                    "name": student_row['Name'].iloc[0]
                }
        except Exception as e:
            print(f"Error loading student info: {e}")
        return {}
    async def handle_admin_list(self, message: Message):
        if not self.admin_list:
            await message.reply_text("🚫 مفيش إدمنات مسجلين حالياً.")
            return

        text = "👮‍♂️ قائمة الإدمنات الحاليين:\n\n"
        for admin_id in self.admin_list:
            try:
                user = await self.app.get_users(admin_id)
                name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                username = f"@{user.username}" if user.username else "بدون يوزر"
                text += f"• {name} ({username}) - ID: `{admin_id}`\n"
            except:
                text += f"• ID: `{admin_id}` (ماقدرناش نجيب معلوماته)\n"

        await message.reply_text(text)

    async def handle_add_admin(self, message: Message):
        user_id = message.from_user.id
        if user_id not in self.admin_list:
            await message.reply_text("❌ Only admins can add new admins.")
            return

        command_parts = message.text.split()
        if len(command_parts) != 2 or not command_parts[1].isdigit():
            await message.reply_text("Usage: /addadmin <telegram_user_id>")
            return

        new_admin_id = int(command_parts[1])
        if new_admin_id in self.admin_list:
            await message.reply_text("ℹ️ This user is already an admin.")
            return

        self.admin_list.append(new_admin_id)
        self.save_state()
        await message.reply_text(f"✅ User `{new_admin_id}` has been added as an admin.")

        try:
            await self.app.send_message(
                new_admin_id,
                "**🎉 Congratulations! You've been promoted to admin.**\n\n"
                "As an admin, you can:\n"
                "🔹 Use `/admin <user_id>` to promote others\n"
                "🔹 Use `/who <user_id>` to know who got the result\n"
                "🔹 Use `/remove <user_id>` to remove others admin ""owner only ""\n"
                "🔹 Use `/unlink <student_id>` or `/unlinktg <telegram_id>` to unlink accounts\n"
                "🔹 Access any student's result using their ID\n"
                "🔹 some other hidden features dont ask about it 😉\n"
                "🔹 Help users in case of ID conflicts\n\n"
                "🛠 Contact @M7MED1573 if you need assistance."
            )
        except: pass

    async def handle_remove_admin(self, message: Message):
        user_id = message.from_user.id
        if user_id not in self.admin_list:
            await message.reply_text("❌ Only admins can remove other admins.")
            return

        parts = message.text.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.reply_text("Usage: /remove <telegram_user_id>")
            return

        target_id = int(parts[1])
        if target_id == user_id:
            await message.reply_text("⚠️ You cannot remove yourself.")
            return

        if target_id not in self.admin_list:
            await message.reply_text("❌ This user is not an admin.")
            return

        self.admin_list.remove(target_id)
        self.save_state()
        await message.reply_text(f"✅ User {target_id} has been removed from admin list.")

        try:
            await self.app.send_message(
                target_id,
                "**⚠️ You have been removed as an admin by another administrator.**\n"
                "If you believe this is a mistake, please contact support."
            )
        except: pass

    async def handle_result(self, message: Message):
        user_id = message.from_user.id
        student_id = self.extract_student_id(message)
        if not student_id:
            await message.reply_text("❌ please send me /result رقم الجلوس .\n or just send رقم الجلوس directly.")
            return

        if user_id in self.admin_list:
            result = await self.get_student_result(student_id)
            if result:
                self.track_usage(student_id)
            await message.reply_text(result or f"❌ No results found for ID: {student_id}")
            return

        registered_id = self.user_student_map.get(str(user_id))
        for uid, sid in self.user_student_map.items():
            if sid == student_id and uid != str(user_id):
                await message.reply_text(
                    "❌ **تم استخدام كود الطالب الخاص بك من قِبل شخص آخر.**\n"
                    "📞 تواصل مع:\n @youssra_fayed \n @Zahra_3laa \n @El_karadawy \n @Dr_M_ElBaz \n @ElHaWary_M \n @Karimaboraya \n"
                    "🛠️دعم التقنية : @M7MED1573 "
                )
                return

        result = await self.get_student_result(student_id)
        if not result:
            await message.reply_text("❌ عذرًا، نتيجتك مش متاحة دلوقتي.")
            return

        if registered_id is None:
            self.user_student_map[str(user_id)] = student_id
        elif registered_id != student_id:
            await message.reply_text("❌ You can only access your linked result.")
            return

        self.track_usage(student_id)
        self.save_state()
        await message.reply_text(result + "\n\n🔒 ID linked to your account.")

    async def handle_whois(self, message: Message):
        user_id = message.from_user.id
        if user_id not in self.admin_list:
            await message.reply_text("❌ الأمر ده للمشرفين بس.")
            return

        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.reply_text("الاستخدام الصحيح:\n/who <student_id> ")
            return

        target_id = parts[1]
        for uid, sid in self.user_student_map.items():
            if sid == target_id:
                try:
                    user = await self.app.get_users(int(uid))
                    student_info = await self.get_student_info_by_id(target_id)
                    student_name = student_info.get("name", "—")
                    usage = self.student_usage.get(target_id, {})
                    access_count = usage.get("count", 0)
                    last_time = usage.get("last_time")
                    if last_time:
                        last_time = datetime.fromisoformat(last_time).strftime("%Y-%m-%d %H:%M")

                    info = f"""
📌 **بيانات الطالب:**

🆔 **Student ID:** `{target_id}`
👤 **الاسم:** {student_name}
📚 **النتيجة متاحة:** {"✅" if student_name != "—" else "❌ غير متاحة"}

━━━━━━━━━━━━━━━━━━━━

👤 **المستخدم اللي حصل على النتيجة:**

📎 **الاسم على تيليجرام:** {user.first_name or ''} {user.last_name or ''}
🔗 **اليوزر:** {'@' + user.username if user.username else '— مفيش يوزر —'}
🆔 **Telegram ID:** `{uid}`
📥 **مرات الدخول:** {access_count} مره
🕒 **آخر مرة ظهر فيها:** {last_time or 'غير متوفر'}
"""

                    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("💬 كلمه على الخاص", url=f"https://t.me/{user.username}")]]) if user.username else None
                    await message.reply_text(info, reply_markup=keyboard)
                    return
                except Exception as e:
                    await message.reply_text(f"❌ حصل خطأ: {e}")
                    return
        await message.reply_text("❌ مفيش حد مربوط بالـ Student ID ده.")

    def extract_student_id(self, message: Message) -> Optional[str]:
        parts = message.text.split()
        if len(parts) == 1 and parts[0].isdigit():
            return parts[0]
        if len(parts) == 2 and parts[1].isdigit():
            return parts[1]
        return None

    async def get_student_result(self, student_id: str) -> Optional[str]:
        try:
            if not os.path.exists(EXCEL_FILE):
                raise FileNotFoundError(f"Excel file '{EXCEL_FILE}' not found")

            df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
            df.rename(columns={'ID': 'id', 'اسم الطالب': 'Name'}, inplace=True)
            df['id'] = df['id'].astype(str).str.strip().str.replace('.0', '', regex=False)
            student_id = str(student_id).strip()

            row = df[df['id'] == student_id]
            if row.empty:
                return None

            name = row['Name'].iloc[0]
            Dermatology = row['Dermatology'].iloc[0]
            ENT = row['ENT'].iloc[0]
            Family_medicine = row['Family medicine'].iloc[0]
            Radiology = row['Radiology'].iloc[0]
            total = row['Total'].iloc[0]
            percentage = row['percentage'].iloc[0]

            return f"""
🎓 **Student Result**
━━━━━━━━━━━━━━━━━━━━━━━
👤 **Full Name**     : {name}  
🆔 **Student ID**    : `{student_id}`
🗓️ **Semester**      :   **9**  

📚 **Subject Grades:**
━━━━━━━━━━━━━━━━━━━━━━━
🔹 Dermatology : {Dermatology}
🔹 ENT : {ENT}
🔹 Family Medicine : {Family_medicine}
🔹 Radiology : {Radiology}
🔹 **Total** : {total}
🔹 **Percentage** : {percentage:.2f}%
━━━━━━━━━━━━━━━━━━━━━━━
🔒 **Privacy Notice:** Your Student ID has been securely linked to your Telegram account to protect your academic data.

"""
        except Exception as e:
            return f"Error: {str(e)}"



    def track_usage(self, student_id: str):
        usage = self.student_usage.get(student_id, {"count": 0})
        usage["count"] += 1
        usage["last_time"] = datetime.now().isoformat()
        self.student_usage[student_id] = usage

    def run(self):
        print("🚀 Bot is running...")
        self.app.run()

if __name__ == "__main__":
    bot = StudentResultBot()
    bot.run()
