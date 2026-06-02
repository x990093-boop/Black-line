import disnake
from disnake.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta, time

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

# ==== ملفات قواعد البيانات ====
BANK_FILE = "bank.json"
CONFIG_FILE = "config.json"

# ==== إعدادات الرومات الثابتة ====
APPEAL_CHANNEL_ID = 1498633999579615242  
ADMIN_LOG_CHANNEL_ID = 1509623362991821011  

IDENTITY_SETUP_CHANNEL = 1484406368524828672   # روم بنل تقديم الهوية
IDENTITY_ADMIN_CHANNEL = 1484405475805233202   # روم قبول ورفض الهوية للإدارة

# ==== إعدادات الرتب المطلوبة عند القبول ====
AUTO_ROLES = [1491881927005835407, 1492523810937897132, 1491881746151510158]

# النص الأصلي والكامل للحلف للرجوع إليه ومقارنته
OATH_TEXT_ORIGINAL = "اقـسـم بـالله الـعـظـيـم انـا ( اسـمك ) انـي لـن اخـرب بـ رولات بـلاك لايـن و لـن اسـرب اي رابـط مـن روابـط الـسـيـرفـر وانـي لـن اهـكـر الـسـيـرفـر والله عـلـى مـا اقـولـه شـهـيـد"

# ================= دوان الـ Helper والـ Format =================
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
        db[gid][uid] = {"cash": 1000, "bank": 0}
        save(BANK_FILE, db)
    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)

def get_next_identity_id():
    config = load(CONFIG_FILE)
    if "next_id" not in config:
        config["next_id"] = 1123
    current_id = config["next_id"]
    config["next_id"] += 1
    save(CONFIG_FILE, config)
    return current_id

# ================= 🪪 نظام تقديم الهوية المتكامل =================

class IdentityAdminButtons(disnake.ui.View):
    def __init__(self, applicant_id=None, roblox_name=""):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.roblox_name = roblox_name

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green, custom_id="id_approve_global")
    async def id_approve(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ الصلاحية للإدارة العليا فقط!", ephemeral=True)
        
        await inter.response.defer()
        
        member = inter.guild.get_member(self.applicant_id)
        if not member:
            return await inter.followup.send("❌ تعذر العثور على العضو داخل السيرفر.")
        
        identity_id = get_next_identity_id()
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
        if not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ الصلاحية للإدارة العليا فقط!", ephemeral=True)
            
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

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green)
    async def confirm_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return await inter.followup.send("❌ حدث خطأ في تحديد السيرفر الرئيسي.")
            
        admin_channel = guild.get_channel(IDENTITY_ADMIN_CHANNEL)
        if not admin_channel:
            return await inter.followup.send("❌ حدث خطأ: لا يمكن العثور على روم الإدارة الخاص بالهويات.")

        embed = disnake.Embed(title="🪪 طلب هوية جديد للتحقق ومراجعة الحلف", color=0x3498db)
        embed.add_field(name="👤 صاحب الطلب", value=f"<@{inter.author.id}>", inline=False)
        embed.add_field(name="📝 اسمك:", value=self.answers["name"], inline=True)
        embed.add_field(name="📝 عمرك:", value=self.answers["age"], inline=True)
        embed.add_field(name="📝 حسابك روبلوكس:", value=self.answers["roblox"], inline=True)
        embed.add_field(name="📝 قانون السيرفر:", value=self.answers["rule1"], inline=False)
        embed.add_field(name="📝 قانون الرول:", value=self.answers["rule2"], inline=False)
        
        # التحديث الجديد: عرض الحلف المطلوب مقارنة بكتابة العضو لسهولة كشف الأخطاء أو النسخ
        embed.add_field(name="📜 الـحـلـف المـطـلـوب (الأصـلـي):", value=f"```\n({OATH_TEXT_ORIGINAL})\n
```", inline=False)
        embed.add_field(name="✍️ كـتـابـة الـعـضـو الـحـالـيـة:", value=f"```\n{self.answers['oath']}\n```", inline=False)
        
        if self.answers["image_url"]:
            embed.set_image(url=self.answers["image_url"])

        await admin_channel.send(embed=embed, view=IdentityAdminButtons(inter.author.id, self.answers["roblox"]))
        
        success_embed = disnake.Embed(title="✅ تم التقديم", description="تم إرسال طلب هويتك إلى الإدارة بنجاح وجاري مراجعته.", color=0x00ff00)
        await inter.followup.send(embed=success_embed)
        self.stop()

    @disnake.ui.button(label="رفض", style=disnake.ButtonStyle.red)
    async def cancel_send(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        cancel_embed = disnake.Embed(description="❌ تم إلغاء تقديم الطلب بنجاح.", color=0xff0000)
        await inter.response.send_message(embed=cancel_embed, ephemeral=True)
        self.stop()


class IdentityStartConfirmation(disnake.ui.View):
    def __init__(self, bot_instance, guild_id):
        super().__init__(timeout=60)
        self.bot = bot_instance
        self.guild_id = guild_id

    @disnake.ui.button(label="قبول", style=disnake.ButtonStyle.green)
    async def accept_start(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(view=None)
        
        try:
            dm = inter.author
            
            questions = [
                {"title": "1/6 طلب هوية", "desc": "اسمك:"},
                {"title": "2/6 طلب هوية", "desc": "عمرك:"},
                {"title": "3/6 طلب هوية", "desc": "حسابك روبلوكس:"},
                {"title": "4/6 طلب هوية", "desc": "اذكر قانون من السيرفر:"},
                {"title": "5/6 طلب هوية", "desc": "اذكر قانون من الرول:"},
                {"title": "6/6 طلب هوية", "desc": f"احلف هذا الـحـلـف 👈 : ( {OATH_TEXT_ORIGINAL} ) مـمـنـوع الـنـسـخ !"},
                {"title": "📸 أرسل صورة حسابك الآن", "desc": "قم برفع لقطة شاشة لحسابك أو ضع الرابط المباشر هنا:"}
            ]
            
            answers = {}
            keys = ["name", "age", "roblox", "rule1", "rule2", "oath", "image_url"]
            
            def check(m):
                return m.author.id == inter.author.id and isinstance(m.channel, disnake.DMChannel)

            for i, q in enumerate(questions):
                q_embed = disnake.Embed(title=q["title"], description=q["desc"], color=0x2b2d31)
                await dm.send(embed=q_embed)
                
                msg = await self.bot.wait_for("message", check=check, timeout=180)
                
                if i == 6:  
                    if msg.attachments: answers[keys[i]] = msg.attachments[0].url
                    else: answers[keys[i]] = msg.content
                else:
                    answers[keys[i]] = msg.content

            confirm_main_embed = disnake.Embed(title="❓ تأكيد التقديم", description="هل أنت متأكد من رغبتك في إرسال التقديم النهائي للإدارة؟", color=0xe74c3c)
            await dm.send(embed=confirm_main_embed, view=IdentityConfirmView(answers, self.bot, self.guild_id))
            
        except Exception as e:
            try:
                err_embed = disnake.Embed(title="❌ إلغاء التقديم", description="انتهى الوقت المتاح للإجابة على الأسئلة أو تم إغلاق الخاص.", color=0xff0000)
                await inter.author.send(embed=err_embed)
            except: pass
        self.stop()

    @disnake.ui.button(label="رفض", style=disnake.ButtonStyle.red)
    async def deny_start(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        cancel_embed = disnake.Embed(description="❌ تم إلغاء بدء التقديم بنجاح.", color=0xff0000)
        await inter.response.edit_message(embed=cancel_embed, view=None)
        self.stop()


class IdentityPanelButton(disnake.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @disnake.ui.button(label="ابدأ التقديم", style=disnake.ButtonStyle.blurple, custom_id="start_identity_btn_global")
    async def start_app(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_message("📥 تم بدء التقديم، يرجى التوجه لرسائلك الخاصة للإجابة على الأسئلة فوراً.", ephemeral=True)
        
        try:
            start_confirm_embed = disnake.Embed(
                title="❓ تأكيد التقديم",
                description="هل متأكد بدء التقديم？",
                color=0x2b2d31
            )
            await inter.author.send(embed=start_confirm_embed, view=IdentityStartConfirmation(self.bot, inter.guild.id))
        except:
            await inter.followup.send("❌ تأكد من فتح إعدادات الرسائل الخاصة أولاً.", ephemeral=True)


# ================= 💵 نظام الرواتب الأسبوعي المخصص للإدارة =================

SALARY_ROLES = {
    "دعم فني مبتدئ": 4500, "دعم الفني مترقي": 5500, "دعم فني محترف": 6500, "مسؤول الدعم فني": 8500,
    "منظم اقماع مبتدئ": 4500, "منظم اقماع متقدم": 5500, "مسؤول المنظمين": 8500,
    "جندي": 5000, "جندي اول": 6000, "عريف": 7000, "وكيل رقيب": 8000, "رقيب": 9000,
    "رقيب اول": 10000, "رئيس رقباء": 11000, "ملازم": 12000, "ملازم اول": 13000,
    "نقيب": 14000, "رائد": 15000, "مقدم": 16000, "عقيد": 17000, "عميد": 18000,
    "فريق": 19000, "فريق اول": 20000,
    "طاقم الادارف": 12000, "الادارة العليا": 25000
}

def get_next_friday_one_pm():
    now = datetime.now()
    days_ahead = 4 - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.time() >= time(13, 0)):
        days_ahead += 7
    next_friday = now + timedelta(days=days_ahead)
    return datetime.combine(next_friday.date(), time(13, 0))

@bot.command(name="الرواتب")
@commands.has_permissions(administrator=True)
async def salary_status(ctx):
    next_payout = get_next_friday_one_pm()
    remaining = next_payout - datetime.now()
    
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    time_str = f"{days} يوم و {hours} ساعة و {minutes} دقيقة"

    embed = disnake.Embed(title="🕒 حالة نظام الرواتب الأسبوعي", color=0x2b2d31)
    embed.add_field(name="📅 موعد الصرف الثابت:", value="كل يوم جمعة الساعة 1:00 مساءً", inline=False)
    embed.add_field(name="⌛ الموعد القادم خلال:", value=time_str, inline=False)
    embed.set_footer(text=f"وزارة الموارد البشرية | {datetime.now().strftime('%I:%M,%d/%m/%Y')}")
    await ctx.send(embed=embed)

@salary_status.error
async def salary_status_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ هذا الأمر مخصص لطاقم الإدارة العليا فقط!")


@tasks.loop(seconds=60)
async def auto_salary_check():
    now = datetime.now()
    if now.weekday() == 4 and now.hour == 13 and now.minute == 0:
        for guild in bot.guilds:
            log_channel = guild.get_channel(ADMIN_LOG_CHANNEL_ID)
            total_distributed = 0
            count = 0
            
            for member in guild.members:
                if member.bot: continue
                
                highest_salary = 0
                for role in member.roles:
                    clean_role_name = role.name.replace("|", "").replace("•", "").strip()
                    if clean_role_name in SALARY_ROLES:
                        if SALARY_ROLES[clean_role_name] > highest_salary:
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
                    try: 
                        dm_sal_embed = disnake.Embed(description=f"💵 تم إيداع راتبك الأسبوعي بمبلغ {format_num(highest_salary)} في حسابك بنجاح!", color=0x00ff00)
                        await member.send(embed=dm_sal_embed)
                    except: pass
            
            if log_channel and count > 0:
                embed = disnake.Embed(title="🏦 تقرير صرف الرواتب التلقائي", color=0x00ff00)
                embed.add_field(name="📊 إجمالي الأعضاء المستلمين", value=f"{count} عضو", inline=True)
                embed.add_field(name="💰 إجمالي المبالغ المصروفة", value=format_num(total_distributed), inline=True)
                await log_channel.send(embed=embed)


# ================= الأنظمة الأساسية المتبقية لحسابات البنك =================

@bot.command(name="حسابي")
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)
    embed = disnake.Embed(title=f"🏦 حساب {ctx.author.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    await ctx.send(embed=embed)

@bot.command(name="حساب")
async def account(ctx, member: disnake.Member = None):
    if not member: member = ctx.author
    user = get_user(ctx.guild.id, member.id)
    embed = disnake.Embed(title=f"🏦 حساب {member.display_name}", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=format_num(user["cash"]))
    embed.add_field(name="🏦 البنك", value=format_num(user["bank"]))
    embed.add_field(name="📊 المجموع", value=format_num(user["cash"] + user["bank"]))
    await ctx.send(embed=embed)

@bot.command(name="تصفير-رتب")
@commands.has_permissions(administrator=True)
async def reset_roles(ctx, member: disnake.Member):
    if member.id == ctx.guild.owner_id: return await ctx.send("❌ لا يمكنك تصفير رتب مالك السيرفر!")
    try:
        await member.edit(roles=[])
        await ctx.send(f"👑 **[أمر إداري]** تم تصفير وسحب جميع الرتب من {member.mention} بنجاح!")
    except:
        await ctx.send("❌ البوت لا يملك صلاحية لتعديل رتب هذا الشخص.")

# ================= ⚡ تشغيل البوت والتهيئة التلقائية =================

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user}")
    
    bot.add_view(IdentityPanelButton(bot))
    bot.add_view(IdentityAdminButtons(None, ""))
    
    if not auto_salary_check.is_running():
        auto_salary_check.start()
        
    await bot.wait_until_ready()
    
    channel_id_setup = bot.get_channel(IDENTITY_SETUP_CHANNEL)
    if channel_id_setup:
        try:
            await channel_id_setup.purge(limit=5)
            embed_id = disnake.Embed(
                title="🪪 طلب هوية",
                description="طلب هوية مهم عشان تقدر تلعب",
                color=0x2b2d31
            )
            await channel_id_setup.send(embed=embed_id, view=IdentityPanelButton(bot))
            print("📬 تم إرسال بنل تقديم الهوية بنجاح!")
        except Exception as e:
            print(f"❌ تعذر تحديث البنل: {e}")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
