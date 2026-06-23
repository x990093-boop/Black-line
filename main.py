import disnake
from disnake.ext import commands
import json, os
from datetime import datetime

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"

# 🛠️ الأقسام والرومات المعينة من قبلك
APPEAL_CHANNEL_ID = 1514971328124424222      # روم تقديم الاعتراض للعامة
ADMIN_LOG_CHANNEL_ID = 1515034021510381568   # روم الإدارة للتحكم بالاعتراضات

# 📊 رومات نظام بصمة الإدارة الجديد
DUTY_PANEL_CHANNEL_ID = 1508640601116250213  # روم بنل البصمة (إرسال تلقائي)
DUTY_LOG_CHANNEL_ID = 1519022162621632542    # روم سجل الأونر (استقبال تقارير الشغل)

# قاموس مؤقت لحفظ وقت بداية دخول الإداريين (يتحمل الرستارت لبيانات الجلسة الحالية)
active_duty = {}

# دالة مساعدة لتنسيق الأرقام بالفواصل مع رمز العملة ⃁
def format_num(val):
    try:
        return f"{int(val):,} ⃁"
    except:
        return str(val)

# دالة لتنظيف الرقم المدخل من الفواصل
def clean_num(val_str):
    try:
        return int(str(val_str).replace(",", ""))
    except:
        return 0

# ================= DATABASE =================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= USER =================
def get_user(gid, uid):
    db = load(BANK_FILE)
    gid, uid = str(gid), str(uid)

    db.setdefault(gid, {})
    if uid not in db[gid]:
        db[gid][uid] = {"cash": 1000, "bank": 0}
        save(BANK_FILE, db)

    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)

# ================= حساب =================
@bot.command(name="حسابي")
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)

    embed = disnake.Embed(title=f"🏦 حساب {ctx.author.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command(name="حساب")
async def account(ctx, member: disnake.Member = None):
    if not member:
        member = ctx.author

    user = get_user(ctx.guild.id, member.id)

    embed = disnake.Embed(title=f"🏦 حساب {member.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ================= تحويل =================
@bot.command(name="تحويل")
async def transfer(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    sender = get_user(ctx.guild.id, ctx.author.id)
    receiver = get_user(ctx.guild.id, member.id)

    if sender["cash"] < parsed_amount:
        return await ctx.send("❌ ما عندك كاش كافي")

    if receiver["bank"] + parsed_amount > 1000000:
        return await ctx.send(f"❌ لا يمكنك التحويل، بنك {member.mention} سيتعدى الحد الأقصى ({format_num(1000000)})")

    sender["cash"] -= parsed_amount
    receiver["bank"] += parsed_amount 

    update_user(ctx.guild.id, ctx.author.id, sender)
    update_user(ctx.guild.id, member.id, receiver)

    await ctx.send(f"💸 تم تحويل {format_num(parsed_amount)} إلى بنك {member.mention}")

# ================= ايداع / سحب =================
@bot.command(name="ايداع")
async def deposit(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    user = get_user(ctx.guild.id, ctx.author.id)

    if user["cash"] < parsed_amount:
        return await ctx.send("❌ ما عندك كاش")

    if user["bank"] >= 1000000:
        return await ctx.send(f"❌ بنكك ممتلئ بالفعل! الحد الأقصى هو {format_num(1000000)}")

    if user["bank"] + parsed_amount > 1000000:
        allowed_amount = 1000000 - user["bank"]
        user["cash"] -= allowed_amount
        user["bank"] = 1000000
        update_user(ctx.guild.id, ctx.author.id, user)
        return await ctx.send(f"🏦 تم إيداع {format_num(allowed_amount)} فقط لأن البنك وصل للحد الأقصى ({format_num(1000000)})")

    user["cash"] -= parsed_amount
    user["bank"] += parsed_amount

    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"🏦 تم إيداع {format_num(parsed_amount)}")

@bot.command(name="سحب")
async def withdraw(ctx, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ المبلغ يجب ان يكون أكبر من صفر")

    user = get_user(ctx.guild.id, ctx.author.id)

    if user["bank"] < parsed_amount:
        return await ctx.send("❌ ما عندك بالبنك")

    user["bank"] -= parsed_amount
    user["cash"] += parsed_amount

    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"💵 تم سحب {format_num(parsed_amount)}")

# ================= أوامر الإدارة العليا =================
@bot.command(name="اعطاء")
@commands.has_permissions(administrator=True)
async def give(ctx, member: disnake.Member, amount: str):
    parsed_amount = clean_num(amount)
    if parsed_amount <= 0:
        return await ctx.send("❌ الرجاء تحديد مبلغ صحيح أكبر من صفر")

    user = get_user(ctx.guild.id, member.id)
    user["cash"] += parsed_amount
    update_user(ctx.guild.id, member.id, user)

    await ctx.send(f"👑 **[أمر إداري]** تم إعطاء {format_num(parsed_amount)} كاش لـ {member.mention}")

@bot.command(name="حساب-السيرفر")
@commands.has_permissions(administrator=True)
async def server_accounts(ctx):
    db = load(BANK_FILE)
    gid = str(ctx.guild.id)

    if gid not in db or not db[gid]:
        return await ctx.send("❌ لا يوجد بيانات أعضاء في هذا السيرفر")

    embed = disnake.Embed(title="📊 حسابات السيرفر (إدارة عليا)", color=0x2b2d31)

    for uid, data in db[gid].items():
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"عضو غادر ({uid})"

        embed.add_field(
            name=f"👤 {name}",
            value=f"💵 كاش: {format_num(data['cash'])} | 🏦 بنك: {format_num(data['bank'])}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name="الغاء-مخالفة")
@commands.has_permissions(administrator=True)
async def clear_violation_by_reply(ctx):
    if not ctx.message.reference:
        return await ctx.send("❌ يرجى الرد (Reply) على رسالة المخالفة المراد إلغاؤها!")

    try:
        replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("❌ لم أتمكن من العثور على رسالة المخالفة الأصلية.")

    if not replied_msg.embeds:
        return await ctx.send("❌ الرسالة التي رددت عليها لا تحتوي على بيانات مخالفة (Embed)!")

    embed = replied_msg.embeds[0]
    citizen_mention = None
    violation_type = None

    for field in embed.fields:
        if "المواطن" in field.name:
            citizen_mention = field.value
        elif "المخالفة" in field.name:
            violation_type = field.value

    if not citizen_mention or not violation_type:
        return await ctx.send("❌ فشل استخراج بيانات المخالفة من الرسالة. تأكد أنها رسالة مخالفة صحيحة.")

    citizen_id = str(citizen_mention.replace("<@", "").replace(">", "").replace("!", ""))

    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)

    if gid in db and citizen_id in db[gid]:
        found = False
        for v in db[gid][citizen_id]:
            if v["type"] == violation_type:
                db[gid][citizen_id].remove(v)
                found = True
                break
        
        if found:
            save(VIOLATION_FILE, db)
            embed.color = 0x36393f
            embed.title = "🗑️ [تم إلغاء المخالفة بواسطة الإدارة]"
            try: await replied_msg.edit(embed=embed, view=None)
            except: pass

            return await ctx.send(f"✅ **[أمر إداري]** تم إسقاط وإلغاء مخالفة **({violation_type})** المسجلة ضد {citizen_mention} بنجاح!")

    await ctx.send("❌ لم يتم العثور على هذه المخالفة مسجلة in ملف المواطن.")


# ================= ⚖️ نظام لوحة التحكم في روم الاعتراض المخصص والأزرار والـ Modals =================

class AdminAppealButtons(disnake.ui.View):
    def __init__(self, user_id, violation_data):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.violation_data = violation_data

    @disnake.ui.button(label="✅ قبول الاعتراض", style=disnake.ButtonStyle.green, custom_id="admin_approve")
    async def approve(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ هذا الزر مخصص للإدارة العليا فقط!", ephemeral=True)

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(self.user_id)

        if gid in db and uid in db[gid]:
            for v in db[gid][uid]:
                if v["type"] == self.violation_data["type"]:
                    db[gid][uid].remove(v)
                    break
            save(VIOLATION_FILE, db)

        embed = inter.message.embeds[0]
        embed.color = 0x00ff00
        embed.title = "✅ تم قبول الاعتراض وحذف المخالفة بنجاح"
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=False)
        
        await inter.message.edit(embed=embed, view=None)
        
        try:
            member = inter.guild.get_member(self.user_id)
            if member: await member.send(f"🎉 تم قبول اعتراضك على مخالفة **({self.violation_data['type']})** وتم إسقاطها عنك!")
        except: pass

    @disnake.ui.button(label="❌ رفض الاعتراض", style=disnake.ButtonStyle.red, custom_id="admin_deny")
    async def deny(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ هذا الزر مخصص للإدارة العليا فقط!", ephemeral=True)

        embed = inter.message.embeds[0]
        embed.color = 0xff0000
        embed.title = "❌ تم رفض الاعتراض وبقاء المخالفة سارية"
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=False)
        
        await inter.message.edit(embed=embed, view=None)
        
        try:
            member = inter.guild.get_member(self.user_id)
            if member: await member.send(f"👎 تم رفض اعتراضك على مخالفة **({self.violation_data['type']})** من قبل الإدارة.")
        except: pass


class AppealReasonModal(disnake.ui.Modal):
    def __init__(self, violation_data, citizen_id):
        components = [
            disnake.ui.TextInput(
                label="سبب الاعتراض",
                placeholder="اكتب هنا سبب اعتراضك بالتفصيل وبشكل واضح...",
                custom_id="reason_input",
                style=disnake.TextInputStyle.paragraph,
                min_length=5,
                max_length=300
            )
        ]
        super().__init__(title="تقديم طلب اعتراض", components=components)
        self.violation_data = violation_data
        self.citizen_id = citizen_id

    async def callback(self, inter: disnake.ModalInteraction):
        reason = inter.text_values["reason_input"]
        appeal_channel = inter.guild.get_channel(ADMIN_LOG_CHANNEL_ID)

        if not appeal_channel:
            return await inter.response.send_message("❌ خطأ: لم يتم العثور على روم الاعتراضات المخصص للإدارة.", ephemeral=True)

        embed = disnake.Embed(title="⚖️ طلب اعتراض جديد على مخالفة", color=0xf1c40f)
        embed.add_field(name="👤 المواطن المعترض", value=f"<@{self.citizen_id}>", inline=True)
        embed.add_field(name="📄 نوع المخالفة", value=self.violation_data["type"], inline=True)
        embed.add_field(name="💰 الغرامة / العقوبة", value=format_num(self.violation_data["fine"]), inline=True)
        embed.add_field(name="👮 العسكري المسجل", value=self.violation_data["officer"], inline=True)
        embed.add_field(name="📝 سبب الاعتراض المقدم", value=reason, inline=False)
        
        if self.violation_data.get("image"):
            embed.set_image(url=self.violation_data["image"])

        await appeal_channel.send(embed=embed, view=AdminAppealButtons(self.citizen_id, self.violation_data))
        await inter.response.send_message("✅ تم إرسال طلب اعتراضك بنجاح إلى روم الإدارة وجاري النظر فيه.", ephemeral=True)


class DirectAppealSelect(disnake.ui.Select):
    def __init__(self, violations, citizen_id):
        options = []
        for i, v in enumerate(violations):
            officer_name = v['officer'].split('#')[0] if '@' not in v['officer'] else "عسكري"
            options.append(disnake.SelectOption(
                label=f"{v['type']} | {format_num(v['fine'])}",
                description=f"👮 العسكري: {officer_name}",
                value=str(i)
            ))
        super().__init__(placeholder="اختر المخالفة التي ترغب بالاعتراض عليها من القائمة", options=options)
        self.violations = violations
        self.citizen_id = citizen_id

    async def callback(self, inter: disnake.MessageInteraction):
        idx = int(self.values[0])
        chosen_violation = self.violations[idx]
        await inter.response.send_modal(modal=AppealReasonModal(chosen_violation, self.citizen_id))


class DirectAppealSelectView(disnake.ui.View):
    def __init__(self, violations, citizen_id):
        super().__init__(timeout=60)
        self.add_item(DirectAppealSelect(violations, citizen_id))


class RoomAppealBaseButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="⚖️ تقديم طلب اعتراض", style=disnake.ButtonStyle.blurple, custom_id="base_appeal_btn")
    async def open_menu(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(inter.author.id)

        if gid not in db or uid not in db[gid] or len(db[gid][uid]) == 0:
            return await inter.response.send_message("❌ ملفك نظيف تماماً! ليس لديك أي مخالفات لتسجيل اعتراض عليها.", ephemeral=True)

        await inter.response.send_message(
            content="📋 ظهرت لك قائمة بمخالفاتك المسجلة حالياً، يرجى اختيار واحدة لتحديدها:",
            view=DirectAppealSelectView(db[gid][uid], inter.author.id),
            ephemeral=True
        )


# ================= 🚓 قائمة المخالفات الكاملة =================
VIOLATIONS = [
    ("زره", "500"),
    ("قطع اشاره", "3000"),
    ("عكس سير متعمد", "منع من اللعب يومين"),
    ("سحب جلنط متقصد", "1000"),
    ("سرعه 75 الى 80", "منع من اللعب يومين"),
    ("سرعه 81 الى 90 ميل", "منع من اللعب ثلاث ايام"),
    ("سرعه 90 و فوق", "منع من اللعب خمس ايام"),
    ("تجاوز سيارات", "1000"),
    ("هروب من عسكري", "تتبلك"),
    ("تطلع الرصيف", "500"),
    ("عدم وجود لوحه و ماعندك تصريح", "3000"),
    ("التفحيط", "4500"),
    ("مركبه سبورت و ماشريت تصريح", "3000 و تغير السيارة قدام العسكري"),
    ("تديور على خط اصفر", "1000"),
    ("عدم تشغيل اضواء", "500"),
    ("لوحه مميزه و ما معك تصريح", "3000")
]

class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, officer, image):
        options = [disnake.SelectOption(label=f"{v[0]} | {format_num(v[1])}") for v in VIOLATIONS]
        super().__init__(placeholder="اختر المخالفة المراد تسجيلها", options=options)

        self.member = member
        self.officer = officer
        self.image = image

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]
        fine = next(v[1] for v in VIOLATIONS if v[0] == selected)

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(self.member.id)

        violation_entry = {
            "type": selected,
            "fine": fine,
            "officer": str(self.officer),
            "image": self.image
        }

        db.setdefault(gid, {}).setdefault(uid, [])
        db[gid][uid].append(violation_entry)
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="🚨 تم تسجيل مخالفة مرورية", color=0xff0000)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="👮 العسكري", value=self.officer.mention)
        embed.add_field(name="📄 المخالفة", value=selected)
        embed.add_field(name="💰 الغرامة / العقوبة", value=format_num(fine))

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class ViolationView(disnake.ui.View):
    def __init__(self, member, officer, image):
        super().__init__()
        self.add_item(ViolationSelect(member, officer, image))

@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(title="🚓 نظام المخالفات", color=0x2b2d31)
    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=ViolationView(member, ctx.author, image))

# ================= تسديد =================
class PaySelect(disnake.ui.Select):
    def __init__(self, violations):
        options = [disnake.SelectOption(label=f"{v['type']} | {format_num(v['fine'])}") for v in violations]
        super().__init__(placeholder="اختر للدفع", options=options)
        self.violations = violations

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(inter.author.id)

        chosen = None
        for v in self.violations:
            if v["type"] == selected:
                chosen = v
                break

        if not chosen:
            return await inter.response.send_message("❌ حدث خطأ في العثور على المخالفة", ephemeral=True)

        if not str(chosen["fine"]).isdigit():
            return await inter.response.send_message("❌ هذه مخالفة إدارية وعقوبة سلوكية وليست غرامة مالية ليتم دفعها!", ephemeral=True)

        user = get_user(inter.guild.id, inter.author.id)

        if user["bank"] < int(chosen["fine"]):
            return await inter.response.send_message("❌ حسابك في البنك لا يكفي لتسديد الغرامة", ephemeral=True)

        user["bank"] -= int(chosen["fine"])
        update_user(inter.guild.id, inter.author.id, user)

        db[gid][uid].remove(chosen)
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="✅ تم التسديد بنجاح", color=0x00ff00)
        embed.add_field(name="👤 المواطن", value=inter.author.mention)
        embed.add_field(name="👮 العسكري", value=chosen["officer"])
        embed.add_field(name="📄 المخالفة", value=chosen["type"])
        embed.add_field(name="💰 الغرامة المسددة", value=format_num(chosen["fine"]))

        if chosen["image"]:
            embed.set_image(url=chosen["image"])

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class PayView(disnake.ui.View):
    def __init__(self, violations):
        super().__init__()
        self.add_item(PaySelect(violations))

@bot.command(name="تسديد")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid] or len(db[gid][uid]) == 0:
        return await ctx.send("❌ ليس لديك أي مخالفات لتسديدها")

    embed = disnake.Embed(title="💳 اختر مخالفة مالية للتسديد", color=0x2b2d31)
    await ctx.send(embed=embed, view=PayView(db[gid][uid]))


# ================= 💼 نظام بصمة الإدارة (تسجيل الدخول / الخروج) =================

class AdminDutyButtons(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="🟢 تسجيل دخول", style=disnake.ButtonStyle.green, custom_id="duty_sign_in")
    async def sign_in(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        user_id = inter.author.id
        
        if user_id in active_duty:
            return await inter.response.send_message("⚠️ أنت مسجل دخولك بالفعل ومناوبتك تعمل حالياً!", ephemeral=True)
        
        # حفظ وقت الدخول الفعلي
        active_duty[user_id] = datetime.now()
        
        embed = disnake.Embed(
            title="🟢 تم تسجيل دخولك بنجاح",
            description="💼 بالتوفيق في عملك الإداري اليوم! البوت بدأ الآن حساب وقت مناوبتك تلقائياً.",
            color=0x2ecc71
        )
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="🔴 تسجيل خروج", style=disnake.ButtonStyle.red, custom_id="duty_sign_out")
    async def sign_out(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        user_id = inter.author.id
        
        if user_id not in active_duty:
            return await inter.response.send_message("❌ لم تقم بتسجيل الدخول أولاً لكي تسجل خروجك!", ephemeral=True)
        
        start_time = active_duty.pop(user_id)
        end_time = datetime.now()
        
        # حساب فارق الوقت بدقة
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_string = f"{hours} ساعة و {minutes} دقيقة و {seconds} ثانية" if hours > 0 else f"{minutes} دقيقة و {seconds} ثانية"

        # 1. إرسال رد فوري للمسؤول المستلم لإعلامه بنجاح البصمة
        embed_user = disnake.Embed(
            title="🔴 تم تسجيل خروجك بنجاح",
            description=f"⏱️ **الوقت المشتغل:** {time_string}\n📦 تم إرسال تقرير عملك بنجاح إلى الإدارة العليا (الأونر). شكراً لجهودك!",
            color=0xe74c3c
        )
        await inter.response.send_message(embed=embed_user, ephemeral=True)

        # 2. إرسال التقرير التفصيلي لروم سجل الأونر المخصص
        log_channel = bot.get_channel(DUTY_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = disnake.Embed(title="📊 تقرير بصمة إدارية جديدة", color=0x2b2d31)
            embed_log.add_field(name="👤 الإداري:", value=inter.author.mention, inline=True)
            embed_log.add_field(name="🆔 المعرف:", value=f"`{inter.author.id}`", inline=True)
            embed_log.add_field(name="⏱️ المدة المستغرقة:", value=f"**{time_string}**", inline=False)
            embed_log.add_field(name="📅 تاريخ ووقت الدخول:", value=start_time.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
            embed_log.add_field(name="📅 تاريخ ووقت الخروج:", value=end_time.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
            embed_log.set_thumbnail(url=inter.author.display_avatar.url)
            
            await log_channel.send(embed=embed_log)


# ================= ⚡ تشغيل البوت وإرسال الإمبيدات التلقائية =================

@bot.event
async def on_ready():
    print(f"✅ تم تشغيل البوت بنجاح باسم: {bot.user}")
    
    # ربط الأزرار الثابتة لكي لا تعطل عند ريستارت البوت (الاعتراضات + البصمة)
    bot.add_view(RoomAppealBaseButton())
    bot.add_view(AdminAppealButtons(None, None))
    bot.add_view(AdminDutyButtons())
    
    # 1. تحديث روم الاعتراضات تلقائياً
    channel_appeal = bot.get_channel(APPEAL_CHANNEL_ID)
    if channel_appeal:
        try:
            await channel_appeal.purge(limit=10)
            embed_appeal = disnake.Embed(
                title="⚖️ المحكمة الإدارية | تقديم طلبات الاعتراض",
                description=(
                    "إذا كنت ترى أن هناك مخالفة مرورية سجلت ضدك بشكل خاطئ أو تعسفي، "
                    "يمكنك تقديم طلب اعتراض رسمي مباشرة للإدارة العليا.\n\n"
                    "**اضغط على الزر أدناه لبدء تقديم الطلب وتحديد المخالفة:**"
                ),
                color=0x2b2d31
            )
            embed_appeal.set_footer(text="نظام الاعتراضات الآلي والمنظم للسيرفر")
            await channel_appeal.send(embed=embed_appeal, view=RoomAppealBaseButton())
            print("📬 تم تحديث وإرسال إمبيد الاعتراض في الروم المخصص بنجاح.")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء محاولة تحديث روم الاعتراضات: {e}")

    # 2. إرسال وتحديث إمبيد بصمة الإدارة تلقائياً في الروم المحدد
    channel_duty = bot.get_channel(DUTY_PANEL_CHANNEL_ID)
    if channel_duty:
        try:
            await channel_duty.purge(limit=10)
            
            # الإمبيد المطلوب: العنوان فوق، والنص التوجيهي بالأسفل
            embed_duty = disnake.Embed(
                title="💼 بصمة ادارهـ",
                description="يرجى تسجيل دخول عند بدء الشغل وتسجيل الخروج عند إنهاء الشغل",
                color=0x2b2d31
            )
            embed_duty.set_footer(text="نظام مراقبة وضبط ساعات العمل للإدارة")
            
            await channel_duty.send(embed=embed_duty, view=AdminDutyButtons())
            print("📬 تم تحديث وإرسال إمبيد بصمة الإدارة تلقائياً بنجاح.")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء إرسال إمبيد البصمة: {e}")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
