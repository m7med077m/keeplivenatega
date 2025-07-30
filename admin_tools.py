from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
import pandas as pd
from io import BytesIO

def setup_admin_tools(bot_instance):
    app = bot_instance.app
    admin_list = bot_instance.admin_list
    user_student_map = bot_instance.user_student_map
    student_usage = bot_instance.student_usage
    get_student_info_by_id = bot_instance.get_student_info_by_id

    # /broadcast
    @app.on_message(filters.command("broadcast"))
    async def broadcast_command(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("❗ استخدم الأمر كده:\n/broadcast رسالتك هنا")
            return

        msg = parts[1]
        sent = 0
        failed = 0
        for uid in user_student_map.keys():
            try:
                await app.send_message(int(uid), f"📢 رسالة من الإدارة:\n\n{msg}")
                sent += 1
            except:
                failed += 1

        await message.reply(f"✅ تم الإرسال لـ {sent} مستخدم.\n❌ فشل الإرسال لـ {failed}.")

    # /stats
    # /stats
    # /stats
    # /stats
    # /stats
    @app.on_message(filters.command("stats"))
    async def stats_command(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        total_users = len(user_student_map)
        total_lookups = sum([d.get("count", 0) for d in student_usage.values()])
        top_users = sorted(student_usage.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:5]

        text = f"📊 **إحصائيات النظام:**\n\n"
        text += f"👥 عدد المستخدمين المرتبطين: `{total_users}`\n"
        text += f"📥 عدد مرات الاستعلام الكلي: `{total_lookups}`\n"
        text += "\n🏆 **أكثر الطلاب تم البحث عنهم:**\n"

        for sid, info in top_users:
            count = info.get("count", 0)
            name = (await get_student_info_by_id(sid)).get("name", "—")
            text += f"🔹 {name} (ID: `{sid}`) ➤ {count} مره\n"

        # حساب محاولات غير مصرح بها (حتى لو تم منعهم من الوصول للنتائج)
        abuse_attempts = {}

        for student_id, info in student_usage.items():
            for uid_raw, count in info.get("by", {}).items():
                uid = str(uid_raw)
                student_id = str(student_id)
                linked_student_id = user_student_map.get(uid)

                # لو المستخدم مرتبط بطالب آخر أو مش مرتبط نهائيًا
                if linked_student_id != student_id:
                    abuse_attempts[uid] = abuse_attempts.get(uid, 0) + count

        # الترتيب حسب عدد المحاولات
        offenders = sorted(abuse_attempts.items(), key=lambda x: x[1], reverse=True)

        await message.reply(text)

        if offenders:
            offenders_to_show = []
            for uid, tries in offenders:
                if tries < 5:
                    continue  # تجاهل المحاولات القليلة
                try:
                    user = await client.get_users(int(uid))
                    username = f"@{user.username}" if user.username else f"{user.first_name} {user.last_name or ''}".strip()
                except:
                    username = "مستخدم غير معروف"
                offenders_to_show.append(f"🔸 {username} (`{uid}`) ➤ {tries} محاوله")

            if offenders_to_show:
                max_batch_size = 20
                total = len(offenders_to_show)
                for i in range(0, total, max_batch_size):
                    batch = offenders_to_show[i:i + max_batch_size]
                    batch_text = "\n".join(batch)
                    batch_text += f"\n\n📄 {i + 1} - {min(i + max_batch_size, total)} من {total}"
                    if i == 0:
                        batch_text = "🚨 مستخدمين حاولوا الوصول لنتائج طلاب آخرين:\n" + batch_text
                    await message.reply(batch_text)
                if total > max_batch_size:
                    from io import BytesIO
                    file = BytesIO("\n".join(offenders_to_show).encode("utf-8"))
                    file.name = "offenders_list.txt"
                    await message.reply_document(file, caption="📄 جميع محاولات التجاوز كاملة (ملف)")
        else:
            pass  # لا ترسل أي نص إضافي إذا لم يوجد مخالفون


    # /unlinktg <telegram_id>
    @app.on_message(filters.command("unlinktg"))
    async def unlink_by_telegram_id(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        parts = message.text.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.reply("❗ الاستخدام الصحيح:\n/unlinktg <telegram_user_id>")
            return

        target_id = parts[1]
        if target_id not in user_student_map:
            await message.reply("❌ لا يوجد حساب مرتبط بهذا ID.")
            return

        student_id = user_student_map.pop(target_id)
        bot_instance.save_state()

        await message.reply(
            f"✅ تم فك الربط بين:\n"
            f"👤 Telegram ID: `{target_id}`\n"
            f"🎓 Student ID: `{student_id}`"
        )

        try:
            await app.send_message(
                int(target_id),
                "⚠️ تم فك ربط حسابك برقم الطالب الخاص بك بواسطة الإدارة.\n"
                "إذا كنت تريد ربطه مرة أخرى، أرسل كود الطالب من جديد."
            )
        except:
            pass

    # /unlink <student_id>
    @app.on_message(filters.command("unlink"))
    async def unlink_by_student_id(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("❗ الاستخدام الصحيح:\n/unlink <student_id>")
            return

        target_student_id = parts[1]
        linked_user_id = None

        for uid, sid in user_student_map.items():
            if sid == target_student_id:
                linked_user_id = uid
                break

        if not linked_user_id:
            await message.reply("❌ لا يوجد مستخدم مرتبط بهذا رقم الطالب.")
            return

        user_student_map.pop(linked_user_id)
        bot_instance.save_state()

        await message.reply(
            f"✅ تم فك الربط بين:\n"
            f"🎓 Student ID: `{target_student_id}`\n"
            f"👤 Telegram ID: `{linked_user_id}`"
        )

        try:
            await app.send_message(
                int(linked_user_id),
                "⚠️ تم فك ربط رقم الطالب الخاص بك بواسطة الإدارة.\n"
                "إذا كنت تريد ربطه مرة أخرى، أرسل الكود من جديد."
            )
        except:
            pass

    # /find <part of name>
    @app.on_message(filters.command("find"))
    async def find_student_command(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        parts = message.text.strip().split(maxsplit=1)
        if len(parts) != 2:
            await message.reply("❗ الاستخدام الصحيح:\n/find <جزء من اسم الطالب أو الاسم كامل>")
            return

        search_terms = parts[1].lower().split()
        matches = []

        try:
            df = pd.read_excel("result.xlsx", sheet_name="Sheet1")
            df.columns = df.columns.str.strip()
            df.rename(columns={"ID": "id", "اسم الطالب": "Name"}, inplace=True)
            df["id"] = df["id"].astype(str).str.strip().str.replace(".0", "", regex=False)
            df["Name"] = df["Name"].astype(str)

            for _, row in df.iterrows():
                name = row["Name"].lower()
                if all(term in name for term in search_terms):
                    matches.append(f"👤 {row['Name']} — 🆔 `{row['id']}`")

            if not matches:
                await message.reply("❌ لا يوجد نتائج لهذا البحث.")
                return

            # تقسيم النتائج على دفعات
            max_batch_size = 20
            total = len(matches)
            for i in range(0, total, max_batch_size):
                batch = matches[i:i + max_batch_size]
                text = "🔍 **نتائج البحث:**\n\n" + "\n".join(batch)
                text += f"\n\n📄 {i + 1} - {min(i + max_batch_size, total)} من {total}"
                await message.reply(text)

            # لو أكتر من 50 نتيجة ➤ ابعت ملف
            if total > 50:
                file = BytesIO("\n".join(matches).encode("utf-8"))
                file.name = "search_results.txt"
                await message.reply_document(file, caption="📄 جميع نتائج البحث كاملة (ملف)")

        except Exception as e:
            await message.reply(f"❌ حصل خطأ أثناء البحث: {str(e)}")

    # /reset
    @app.on_message(filters.command("reset"))
    async def reset_command(client: Client, message: Message):
        if message.from_user.id not in admin_list:
            await message.reply("❌ الأمر ده مخصص للإدمن فقط.")
            return

        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("❗ الاستخدام الصحيح:\n/reset <password>")
            return

        password = parts[1]
        if password != "19312@Mo":
            await message.reply("❌ كلمة المرور غير صحيحة.")
            return

        # Clear the in-memory data
        user_student_map.clear()
        student_usage.clear()
        bot_instance.save_state()

        await message.reply("✅ تم إعادة ضبط قاعدة البيانات بنجاح. يمكنك الآن إضافة نتائج جديدة.")
