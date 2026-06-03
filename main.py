import disnake
from disnake.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, time
import random

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

# ==== ملفات قواعد البيانات ====
BANK_FILE = "bank.json"
CONFIG_FILE = "config.json"
JAIL_FILE = "jail.json"

# ==== إعدادات الرومات الثابتة ====
APPEAL_CHANNEL_ID = 1498633999579615242  
ADMIN_LOG_CHANNEL_ID = 1509623362991821011  

IDENTITY_SETUP_CHANNEL = 1484406368524828672   # روم بنل تقديم الهوية
IDENTITY_ADMIN_CHANNEL = 1484405475805233202   # روم قبول ورفض الهوية للإدارة

# ==== إعدادات الرتب المطلوبة عند القبول ====
AUTO_ROLES = [1491881927005835407, 1492523810937897132, 1491881746151510158]

# النص الأصلي والكامل للحلف
OATH_TEXT_ORIGINAL = "اقـسـم بـالله الـعـظـيـم انـا ( اسـمك ) انـي لـن اخـرب بـ رولات بـلاك لايـن و لـن اسـرب اي رابـط مـن روابـط الـسـيـرفـر وانـي لـن اهـكـر الـسـيـرفـر والله عـلـى مـا اقـولـه شـهـيـد"


# ================= 🛡️ دالة التحقق الشاملة (تشمل الإدارة الصغرى والعليا) =================
def check_admin_permission(member):
    # يسمح لمالكي السيرفر والإداريين الأساسيين تلقائياً
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild or member.guild_permissions.kick_members:
        return True
    
    # فحص الرتب الذكي ليشمل الإدارة الصغرى والوسطى والعليا وطاقم العمل
    admin_keywords = ["اداره", "إدارة", "طاقم", "مسؤول", "مسئول", "اداري", "إداري", "امن", "أمن"]
    for role in member.roles:
        role_name_lower = role.name.lower()
        if any(keyword in role_name_lower for keyword in admin_keywords):
            return True
            
    return False


# ================= ⚙️ دوال المساعدة وقواعد البيانات الأصلية =================
def format_num(val):
    try: return f"{int(val):,} ⃁"
    except: return str(val)

def load(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(gid, uid):
    db = load(BANK_FILE)
    gid, uid = str(gid), str(uid)
    db.setdefault(gid, {})
    if uid not in db[gid]:
        db[gid][uid] = {"cash": 1000, "bank": 0, "work_cooldown": 0, "crime_cooldown": 0, "rob_cooldown": 0}
        save(BANK_FILE, db)
    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)


# ================= 🪪 نظام تقديم الهوية والتحقق للإدارة =================

class IdentityAdminButtons(disnake.ui.View):
    def __init__(self, applicant_id=None, roblox_name=""):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.roblox_name = roblox_name

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green, custom_id="id_approve_global")
    async def id_approve(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # السماح للإدارة الصغرى والعليا بالضغط
        if not check_admin_permission(inter.author):
            return await inter.response.send_message("❌ الصلاحية لطاقم الإدارة فقط بمختلف رتبهم!", ephemeral=True)
        
        await inter.response.defer()
        member = inter.guild.get_member(self.applicant_id)
        if not member:
            return await inter.followup.send("❌ تعذر العثور على العضو داخل السيرفر.")
        
        config = load(CONFIG_FILE)
        if "next_id" not in config:
            config["next_id"] = 1123
        identity_id = config["next_id"]
        config["next_id"] += 1
        save(CONFIG_FILE, config)
        
        new_nick = f"{self.roblox_name} | {identity_id}"
        
        try: await member.edit(nick=new_nick)
        except Exception as e: print(f"⚠️ تعذر تغيير الاسم: {e}")

        for role_id in AUTO_ROLES:
            role = inter.guild.get_role(role_id)
            if role:
                try: await member.add_roles(role)
                except Exception as e: print(f"⚠️ تعذر إعطاء رتبة {role_id}: {e}")

        embed = inter.message.embeds[0]
        embed.title = "✅ تم قبول طلب الهوية وتفعيل الحساب"
        embed.color = 0x00ff00
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=True)
        embed.add_field(name="🪪 الهوية الممنوحة", value=f"`{identity_id}`", inline=True)
        await inter.message.edit(embed=embed, view=None)
        
        try:
            reply_embed = disnake.Embed(
                title="🎉 تهانينا تفعيل هويتك!",
                description=f"تم قبول طلب الهوية الخاص بك بنجاح!\n\n**🪪 رقم الهوية:** {identity_id}\n**👤 الاسم الجديد:** {new_nick}\n\nنتمنى لك وقتاً ممتعاً باللعب.",
                color=0x00ff00
            )
            await member.send(embed=reply_embed)
        except: pass

    @disnake.ui.button(label="رفض", style=disnake.ButtonStyle.red, custom_id="id_deny_global")
    async def id_deny(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # السماح للإدارة الصغرى والعليا بالضغط
        if not check_admin_permission(inter.author):
            return await inter.response.send_message("❌ الصلاحية لطاقم الإدارة فقط بمختلف رتبهم!", ephemeral=True)
            
        embed = inter.message.embeds[0]
        embed.title = "❌ تم رفض طلب الهوية"
        embed.color = 0xff0000
        embed.add_field(name="⚖️ المسؤول", value=inter.author.mention, inline=False)
        await inter.message.edit(embed=embed, view=None)
        
        try:
            member = inter.guild.get_member(self.applicant_id)
            if member:
                reply_embed = disnake.Embed(title="👎 تعذر قبول الهوية", description="للأسف، تم رفض طلب الهوية الخاص بك بعد مراجعته من قبل الإدارة.", color=0xff0000)
                await member.send(embed=reply_embed)
        except: pass


class IdentityConfirmView(disnake.ui.View):
    def __init__(self, answers, bot_instance, guild_id):
        super().__init__(timeout=120)
        self.answers = answers
        self.bot = bot_instance
        self.guild_id = guild_id

    @disnake.ui.button(label="قبول التقديم وإرساله", style=disnake.ButtonStyle.green)
    async def confirm_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        guild = self.bot.get_guild(self.guild_id)
        if not guild: return await inter.followup.send("❌ حدث خطأ في تحديد السيرفر الرئيسي.")
            
        admin_channel = guild.get_channel(IDENTITY_ADMIN_CHANNEL)
        if not admin_channel: return await inter.followup.send("❌ حدث خطأ: روم الإدارة مفقود.")

        embed = disnake.Embed(title="🪪 طلب هوية جديد للتحقق ومراجعته", color=0x3498db)
        embed.add_field(name="👤 صاحب الطلب", value=f"<@{inter.author.id}>", inline=False)
        embed.add_field(name="📝 اسمك:", value=self.answers["name"], inline=True)
        embed.add_field(name="📝 عمرك:", value=self.answers["age"], inline=True)
        embed.add_field(name="📝 حسابك روبلوكس:", value=self.answers["roblox"], inline=True)
        embed.add_field(name="📝 قانون السيرفر:", value=self.answers["rule1"], inline=False)
        embed.add_field(name="📝 قانون الرول:", value=self.answers["rule2"], inline=False)
        
        # تم إصلاح تهيئة النص هنا لتجنب خطأ SyntaxError
        embed.add_field(name="📜 الـحـلـف المـطـلـوب (الأصـلـي):", value=f"```\n{OATH_TEXT_ORIGINAL}\n```", inline=False)
        embed.add_field(name="✍️ كـتـابـة الـعـضـو الـحـالـيـة:", value=f"```\n{self.answers['oath']}\n```", inline=False)
        
        if self.answers["image_url"]:
            embed.set_image(url=self.answers["image_url"])

        await admin_channel.send(embed=embed, view=IdentityAdminButtons(inter.author.id, self.answers["roblox"]))
        await inter.followup.send(embed=disnake.Embed(title="✅ تم التقديم", description="تم إرسال طلب هويتك بنجاح.", color=0x00ff00))
        self.stop()

    @disnake.ui.button(label="إلغاء التقديم", style=disnake.ButtonStyle.red)
    async def cancel_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message(embed=disnake.Embed(description="❌ تم إلغاء تقديم الطلب.", color=0xff0000), ephemeral=True)
        self.stop()


class IdentityStartConfirmation(disnake.ui.View):
    def __init__(self, bot_instance, guild_id):
        super().__init__(timeout=60)
        self.bot = bot_instance
        self.guild_id = guild_id

    @disnake.ui.button(label="موافق وبدء الأسئلة", style=disnake.ButtonStyle.green)
    async def accept_start(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(view=None)
        try:
            dm = inter.author
            questions = [
                {"title": "1/7 طلب هوية", "desc": "اسمك الكامل الثنائي:"},
                {"title": "2/7 طلب هوية", "desc": "عمرك الحقيقي:"},
                {"title": "3/7 طلب هوية", "desc": "اسم حسابك في روبلوكس (Roblox Username):"},
                {"title": "4/7 طلب هوية", "desc": "اذكر قانوناً أساسياً واحداً من قوانين السيرفر:"},
                {"title": "5/7 طلب هوية", "desc": "اذكر قانوناً واحداً خاصاً بنظام الرولبلاي:"},
                {"title": "6/7 طلب هوية", "desc": f"اكتب الحلف التالي نصاً بيدك وممنوع النسخ واللصق 👈 : ( {OATH_TEXT_ORIGINAL} )"},
                {"title": "📸 إثبات الصورة الشخصية", "desc": "قم برفع لقطة شاشة لحسابك في روبلوكس الآن أو أرسل رابط الصورة الشخصية المباشر:"}
            ]
            
            answers = {}
            keys = ["name", "age", "roblox", "rule1", "rule2", "oath", "image_url"]
            
            def check(m): return m.author.id == inter.author.id and isinstance(m.channel, disnake.DMChannel)

            for i, q in enumerate(questions):
                await dm.send(embed=disnake.Embed(title=q["title"], description=q["desc"], color=0x2b2d31))
                msg = await self.bot.wait_for("message", check=check, timeout=180)
                if i == 6:  
                    answers[keys[i]] = msg.attachments[0].url if msg.attachments else msg.content
                else:
                    answers[keys[i]] = msg.content

            await dm.send(embed=disnake.Embed(title="❓ تأكيد التقديم النهائي", description="هل أنت متأكد من مراجعة إجاباتك وإرسالها للإدارة؟", color=0xe74c3c), view=IdentityConfirmView(answers, self.bot, self.guild_id))
        except Exception as e:
            try: await inter.author.send(embed=disnake.Embed(title="❌ إلغاء التقديم تلقائياً", description="انتهى الوقت المتاح للإجابة أو تم إغلاق الخاص لديك.", color=0xff0000))
            except: pass
        self.stop()

    @disnake.ui.button(label="إلغاء التقديم", style=disnake.ButtonStyle.red)
    async def deny_start(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(embed=disnake.Embed(description="❌ تم إلغاء التقديم بنجاح.", color=0xff0000), view=None)
        self.stop()


class IdentityPanelButton(disnake.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @disnake.ui.button(label="🪪 ابدأ تقديم الهوية الآن", style=disnake.ButtonStyle.blurple, custom_id="start_identity_btn_global")
    async def start_app(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message("📥 تم بدء العملية بنجاح! تفقد رسائلك الخاصة الآن لتعبئة الهوية الخاصة بك.", ephemeral=True)
        try:
            await inter.author.send(embed=disnake.Embed(title="❓ تأكيد الرغبة في التقديم", description="هل أنت متأكد من رغبتك بالبدء بتقديم طلب هوية جديد في السيرفر؟", color=0x2b2d31), view=IdentityStartConfirmation(self.bot, inter.guild.id))
        except:
            await inter.followup.send("❌ تعذر إرسال الأسئلة إليك، يرجى فتح رسائل الخاص بالسيرفر أولاً (Allow DMs).", ephemeral=True)


# ================= 💵 نظام الرواتب والموارد البشرية الأصلي الخاص بك =================

SALARY_ROLES = {
    "دعم فني مبتدئ": 4500, "دعم الفني مترقي": 5500, "دعم فني محترف": 6500, "مسؤول الدعم فني": 8500,
    "منظم اقماع مبتدئ": 4500, "منظم اقماع متقدم": 5500, "مسؤول المنظمين": 8500,
    "جندي": 5000, "جندي اول": 6000, "عريف": 7000, "وكيل رقيب": 8000, "رقيب": 9000,
    "رقيب اول": 10000, "رئيس رقباء": 11000, "ملازم": 12000, "ملازم اول": 13000,
    "نقيب": 14000, "رائد": 15000, "مقدم": 16000, "عقيد": 17000, "عميد": 18000,
    "فريق": 19000, "فريق اول": 20000,
    "طاقم الاداره": 12000, "الادارة العليا": 25000
}

def get_next_friday_one_pm():
    now = datetime.now()
    days_ahead = 4 - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.time() >= time(13, 0)): days_ahead += 7
    next_friday = now + timedelta(days=days_ahead)
    return datetime.combine(next_friday.date(), time(13, 0))

@bot.command(name="الرواتب")
async def salary_status(ctx):
    if not check_admin_permission(ctx.author): 
        return await ctx.send("❌ هذا الأمر مخصص لطاقم الإدارة والمسؤولين فقط!")

    next_payout = get_next_friday_one_pm()
    remaining = next_payout - datetime.now()
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    embed = disnake.Embed(title="🕒 حالة نظام الرواتب الأسبوعي لوزارة العمل", color=0x2b2d31)
    embed.add_field(name="📅 موعد الصرف الثابت الدوري:", value="كل يوم جمعة الساعة 1:00 مساءً بالتوقيت المحلي", inline=False)
    embed.add_field(name="⌛ الوقت المتبقي للإيداع القادم:", value=f"{days} يوم و {hours} ساعة و {minutes} دقيقة", inline=False)
    await ctx.send(embed=embed)

@tasks.loop(seconds=60)
async def auto_salary_check():
    now = datetime.now()
    if now.weekday() == 4 and now.hour == 13 and now.minute == 0:
        for guild in bot.guilds:
            log_channel = guild.get_channel(ADMIN_LOG_CHANNEL_ID)
            total_distributed, count = 0, 0
            for member in guild.members:
                if member.bot: continue
                highest_salary = 0
                for role in member.roles:
                    clean_role_name = role.name.replace("|", "").replace("•", "").strip()
                    if clean_role_name in SALARY_ROLES and SALARY_ROLES[clean_role_name] > highest_salary:
                        highest_salary = SALARY_ROLES[clean_role_name]
                
                if highest_salary > 0:
                    user = get_user(guild.id, member.id)
                    if user["bank"] + highest_salary > 1000000:
                        allowed = 1000000 - user["bank"]
                        user["bank"] = 1000000
                        user["cash"] += (highest_salary - allowed)
                    else:
                        user["bank"] += highest_salary
                    update_user(guild.id, member.id, user)
                    total_distributed += highest_salary
                    count += 1
                    try: await member.send(embed=disnake.Embed(description=f"💵 تم صرف وإيداع راتبك الأسبوعي بمبلغ {format_num(highest_salary)} بنجاح في حسابك البنكي!", color=0x00ff00))
                    except: pass
            
            if log_channel and count > 0:
                embed = disnake.Embed(title="🏦 تقرير وزارة المالية وصرف الرواتب", color=0x00ff00)
                embed.add_field(name="📊 إجمالي الموظفين المستلمين:", value=f"{count} موظف وعامل", inline=True)
                embed.add_field(name="💰 إجمالي الميزانية المستهلكة:", value=format_num(total_distributed), inline=True)
                await log_channel.send(embed=embed)


# ================= 🏦 الأوامر الاقتصادية المتكاملة والتحويلات الأصلي الخاص بك =================

@bot.command(name="حسابي", aliases=["فلوسي", "بنك"])
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)
    embed = disnake.Embed(title=f"🏦 الحساب المالي لـ {ctx.author.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 النقود بالكاش (Cash):", value=format_num(user["cash"]), inline=True)
    embed.add_field(name="💳 الرصيد في البنك (Bank):", value=format_num(user["bank"]), inline=True)
    embed.add_field(name="📊 المجموع الإجمالي للثروة:", value=format_num(user["cash"] + user["bank"]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="حساب")
async def account(ctx, member: disnake.Member = None):
    if not member: member = ctx.author
    user = get_user(ctx.guild.id, member.id)
    embed = disnake.Embed(title=f"🏦 الحساب المالي لـ {member.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 النقود بالكاش (Cash):", value=format_num(user["cash"]), inline=True)
    embed.add_field(name="💳 الرصيد في البنك (Bank):", value=format_num(user["bank"]), inline=True)
    embed.add_field(name="📊 المجموع الإجمالي للثروة:", value=format_num(user["cash"] + user["bank"]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="إيداع", aliases=["يدع"])
async def deposit(ctx, amount: str):
    user = get_user(ctx.guild.id, ctx.author.id)
    if amount.lower() == "كلها" or amount.lower() == "all": amount = user["cash"]
    try: amount = int(amount)
    except: return await ctx.send("❌ يرجى إدخال مبلغ صحيح وصالح للإيداع.")
    
    if amount <= 0: return await ctx.send("❌ لا يمكنك إيداع مبلغ صفر أو أقل من الصفر!")
    if user["cash"] < amount: return await ctx.send("❌ أنت لا تملك هذا المبلغ الكافي في كاشك الحالي لتودعه.")
    
    user["cash"] -= amount
    user["bank"] += amount
    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"✅ تم إيداع {format_num(amount)} بنجاح من محفظتك إلى حسابك بالبنك.")

@bot.command(name="سحب", aliases=["يسحب"])
async def withdraw(ctx, amount: str):
    user = get_user(ctx.guild.id, ctx.author.id)
    if amount.lower() == "كلها" or amount.lower() == "all": amount = user["bank"]
    try: amount = int(amount)
    except: return await ctx.send("❌ يرجى إدخال مبلغ صحيح وصالح للسحب.")
    
    if amount <= 0: return await ctx.send("❌ لا يمكنك سحب مبلغ صفر أو أقل!")
    if user["bank"] < amount: return await ctx.send("❌ حسابك البنكي لا يحتوي على الرصيد الكافي لسحب هذا المبلغ.")
    
    user["bank"] -= amount
    user["cash"] += amount
    update_user(ctx.guild.id, ctx.author.id, user)
    await ctx.send(f"✅ تم سحب {format_num(amount)} بنجاح من حسابك البنكي إلى محفظتك الكاش.")

@bot.command(name="تحويل", aliases=["يحول"])
async def transfer(ctx, member: disnake.Member, amount: int):
    if member.id == ctx.author.id: return await ctx.send("❌ لا يمكنك تحويل الأموال إلى نفسك!")
    if amount <= 0: return await ctx.send("❌ يرجى تحديد قيمة تحويل أكبر من الصفر.")
    
    sender = get_user(ctx.guild.id, ctx.author.id)
    if sender["bank"] < amount: return await ctx.send("❌ رصيدك البنكي الحالي لا يكفي لإتمام هذه الحوالة.")
    
    receiver = get_user(ctx.guild.id, member.id)
    sender["bank"] -= amount
    receiver["bank"] += amount
    
    update_user(ctx.guild.id, ctx.author.id, sender)
    update_user(ctx.guild.id, member.id, receiver)
    await ctx.send(f"💸 تم تحويل مبلغ {format_num(amount)} من حسابك بنجاح إلى حساب {member.mention}.")


# ================= 🎮 الألعاب والعمل وكسب المال الأصلي الخاص بك =================

@bot.command(name="عمل", aliases=["اشتغل"])
async def work(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)
    now = datetime.now().timestamp()
    if now < user.get("work_cooldown", 0):
        remaining = int(user["work_cooldown"] - now)
        return await ctx.send(f"⏳ أنت متعب من العمل الحالي! يرجى الانتظار {remaining} ثانية لتستطيع العمل مجدداً.")
    
    earned = random.randint(500, 1500)
    user["cash"] += earned
    user["work_cooldown"] = now + 300 
    update_user(ctx.guild.id, ctx.author.id, user)
    
    jobs = ["مهندساً في شركة بلاك لاين", "مستشاراً قانونياً للإدارة", "ميكانيكياً في رول بلاي السيرفر", "عسكرياً في خفر السواحل"]
    await ctx.send(f"⚒️ لقد عملت {random.choice(jobs)} وكسبت مبلغ {format_num(earned)} كاش!")

@bot.command(name="جريمة", aliases=["سرقة"])
async def crime(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)
    now = datetime.now().timestamp()
    if now < user.get("crime_cooldown", 0):
        remaining = int(user["crime_cooldown"] - now)
        return await ctx.send(f"🚨 عيون الشرطة عليك حالياً! انتظر {remaining} ثانية قبل التخطيط لجريمة أخرى.")
    
    user["crime_cooldown"] = now + 600 
    success = random.choice([True, False, True])
    if success:
        earned = random.randint(1500, 4000)
        user["cash"] += earned
        await ctx.send(f"🥷 نجحت الجريمة! قمت بسطو مسلح على متجر محلي وهربت بمبلغ {format_num(earned)} كاش.")
    else:
        fine = random.randint(800, 2000)
        user["cash"] = max(0, user["cash"] - fine)
        await ctx.send(f"👮 فشلت الجريمة وألقت مكافحة الشغب القبض عليك! وتم تغريمك بمبلغ {format_num(fine)} من أموالك.")
    update_user(ctx.guild.id, ctx.author.id, user)


# ================= 👮 نظام العقوبات والسجن الأصلي الخاص بك =================

@bot.command(name="سجن")
async def jail_member(ctx, member: disnake.Member, minutes: int, *, reason: str = "غير محدد"):
    if not check_admin_permission(ctx.author): 
        return await ctx.send("❌ هذا الأمر الإداري مخصص لأعضاء الأمن الداخلي والإدارة!")
    
    jail_db = load(JAIL_FILE)
    unid = str(member.id)
    release_time = datetime.now() + timedelta(minutes=minutes)
    jail_db[unid] = {"release_at": release_time.timestamp(), "reason": reason, "author": ctx.author.name}
    save(JAIL_FILE, jail_db)
    
    try:
        jail_role = disnake.utils.get(ctx.guild.roles, name="مسجون")
        if jail_role: await member.add_roles(jail_role)
    except: pass
    
    await ctx.send(f"🔒 تم إيداع المتهم {member.mention} السجن المركزي لمدة {minutes} دقيقة بسبب: {reason}.")

@bot.command(name="إفراج")
async def unjail_member(ctx, member: disnake.Member):
    if not check_admin_permission(ctx.author): 
        return await ctx.send("❌ لا تملك صلاحية الإفراج.")
    
    jail_db = load(JAIL_FILE)
    unid = str(member.id)
    if unid in jail_db:
        del jail_db[unid]
        save(JAIL_FILE, jail_db)
    
    try:
        jail_role = disnake.utils.get(ctx.guild.roles, name="مسجون")
        if jail_role: await member.remove_roles(jail_role)
    except: pass
    await ctx.send(f"🔓 تم الإفراج والعفو عن العضو {member.mention} وإزالة قيود السجن عنه بنجاح.")


# ================= 👑 الأوامر الإدارية والتحكم بالسيرفر =================

@bot.command(name="تصفير-رتب")
async def reset_roles(ctx, member: disnake.Member):
    if not check_admin_permission(ctx.author): 
        return await ctx.send("❌ هذا الأمر مخصص لطاقم الإدارة والمسؤولين فقط!")

    if member.id == ctx.guild.owner_id: return await ctx.send("❌ لا يمكنك تصفير رتب مالك السيرفر ومؤسسه!")
    try:
        await member.edit(roles=[])
        await ctx.send(f"👑 **[أمر إداري]** تم تصفير وسحب جميع الرتب والامتيازات من {member.mention} بنجاح!")
    except:
        await ctx.send("❌ البوت لا يملك الصلاحيات الإدارية العليا لتعديل رتب هذا الشخص.")

@bot.command(name="تصفير-مال")
async def reset_money(ctx, member: disnake.Member):
    if not ctx.author.guild_permissions.administrator: return await ctx.send("❌ الصلاحية للإدارة العليا فقط.")
    user = get_user(ctx.guild.id, member.id)
    user["cash"] = 1000
    user["bank"] = 0
    update_user(ctx.guild.id, member.id, user)
    await ctx.send(f"💰 تم تصفير حساب {member.mention} المالي وإعادته للرصيد الافتراضي الافتتاحي.")


# ================= ⚡ تشغيل البوت والـ Views الحية =================

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم البوت: {bot.user}")
    
    try:
        bot.add_view(IdentityPanelButton(bot))
        bot.add_view(IdentityAdminButtons(None, ""))
    except Exception as e:
        print(f"⚠️ خطأ في تحميل الأزرار الدائمة: {e}")
    
    try:
        if not auto_salary_check.is_running(): 
            auto_salary_check.start()
    except Exception as e:
        print(f"⚠️ خطأ في تشغيل لوب الرواتب التلقائي: {e}")
        
    await bot.wait_until_ready()
    
    channel_id_setup = bot.get_channel(IDENTITY_SETUP_CHANNEL)
    if channel_id_setup:
        try:
            embed_id = disnake.Embed(
                title="🪪 نظام الهويات والتصاريح الرسمي لسيرفر Black Line",
                description="مرحباً بك في مركز استخراج الهويات والتصاريح الموحد.\nتقديم الهوية إلزامي لتستطيع بدء اللعب والحصول على الرتب والتفاعل داخل السيرفر ورول بلاي المدينة.",
                color=0x2b2d31
            )
            embed_id.set_footer(text="الأحوال المدنية | BlackLine Roleplay")
            await channel_id_setup.send(embed=embed_id, view=IdentityPanelButton(bot))
            print("📬 تم تحديث بنل تقديم الهويات التلقائي بنجاح!")
        except Exception as e:
            print(f"❌ تعذر إرسال بنل البوت: {e}")

@bot.event
async def on_message(message):
    if message.author.bot: return
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
