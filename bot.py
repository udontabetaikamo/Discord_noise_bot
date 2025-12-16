import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import google.generativeai as genai
from duckduckgo_search import DDGS

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = 000000000000000000 # サーバーID（整数）を入れる
CATEGORY_NAME = "🧠 Members" # 個室を作るカテゴリー名
LOG_CHANNEL_NAME = "noise-log" # AIログを流すチャンネル名
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
CONNECTION_KEYWORDS = [
    # Social
    "地方創生", "地域活性化", "まちづくり", "コミュニティ", "移住", "教育", "福祉",
    # Business
    "起業", "経営", "マーケティング", "デザイン", "フリーランス", "副業",
    # Tech
    "AI", "プログラミング", "エンジニア", "Web3", "ブロックチェーン",
    # Lifestyle
    "サウナ", "筋トレ", "料理", "読書", "映画", "アート", "旅"
]

# 簡易データベース (今回はJSONファイルで代用)
DB_FILE = "noise_db.json"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# SETUP & UTILS
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# データベースの読み書き関数
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# CORE LOGIC FUNCTIONS
# ==========================================

async def complete_onboarding_tutorial(member, channel, msg_content):
    """
    オンボーディングチュートリアルの完了処理（思考接続の演出以降）
    """
    guild = member.guild
    
    # 思考接続の演出 & ロール付与
    # 川北大洋のID (環境変数から取得、なければプレースホルダー)
    target_id_str = os.getenv('TUTORIAL_TARGET_ID')
    target_member = None
    
    if target_id_str:
        try:
            target_member = guild.get_member(int(target_id_str))
        except ValueError:
            # IDじゃない場合は名前で検索してみる
            target_member = discord.utils.get(guild.members, name=target_id_str)
            if not target_member:
                print(f"Warning: Could not find user with ID or Name: {target_id_str}")

    # 演出
    async with channel.typing():
        await asyncio.sleep(2) # 処理してる感
    
    embed_connect = discord.Embed(title="🧩 思考が接続されました", color=0x00ff00)
    embed_connect.add_field(name=f"{member.name} の思考", value=msg_content, inline=False)
    
    if target_member:
        # ロール付与
        role_name = f"role-times-{target_member.name}"
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.add_roles(role)
            embed_connect.add_field(name=f"🔗 接続先: {target_member.name}", value="「思考の波長」が共鳴しました。\n相手の思考チャンネルへの**永久アクセス権**が付与されました。", inline=False)
        else:
            embed_connect.add_field(name="🔗 接続先: 不明", value="共鳴しましたが、アクセス権の取得に失敗しました。", inline=False)
    else:
        # ターゲットが見つからない場合のフォールバック
        embed_connect.add_field(name="🔗 接続先: ???", value="思考の波長が共鳴しましたが、対象は深淵にいます。（ターゲットID未設定）", inline=False)

    embed_connect.set_footer(text="これが「思考の接続」です。")
    await channel.send(embed=embed_connect)

    await asyncio.sleep(3)

    # 次のアクション案内
    embed_next = discord.Embed(
        title="📡 思考を広げる",
        description="あなたの思考も、誰かの思考と繋がるかもしれません。",
        color=0xcccccc
    )
    embed_next.add_field(
        name="1️⃣ 部屋の名前を変える",
        value="**コマンド:** `/rename [好きな名前]`\n例: `/rename 〇〇の実験室`",
        inline=False
    )
    embed_next.add_field(
        name="2️⃣ 観測者を招待する",
        value="特定の誰かに思考を見せたい場合。\n**コマンド:** `/expose_to @ユーザー名`",
        inline=False
    )
    embed_next.add_field(
        name="3️⃣ 興味の窓を開く",
        value="AIがあなたの思考に合わせて、面白い記事を定期的に探してきます。\n**コマンド:** `/auto_recommend [日数]`\n例: `/auto_recommend 3` (3日に1回推薦)",
        inline=False
    )
    embed_next.add_field(
        name="4️⃣ 自己紹介をする",
        value="最後に、コミュニティ全体に挨拶しましょう。\n<#1446725817244713051> チャンネルで自己紹介をお願いします！",
        inline=False
    )
    await channel.send(embed=embed_next)
    
    # DBの状態更新: 完了済みとする
    db = load_db()
    user_id = str(member.id)
    if user_id in db["users"]:
        db["users"][user_id]["onboarding_status"] = "completed"
        save_db(db)


async def run_onboarding_tutorial(member, channel):
    """
    新規参加者向けのインタラクティブ・チュートリアル
    """
    # 問いかけ
    embed_q1 = discord.Embed(
        title="🧠 思考の種まき",
        description=f"{member.mention}、ようこそ。\nまずは、**「今、あなたがしたいこと」** をここに書き込んでみてください。\n(例: 旅行に行きたい、美味しいラーメンが食べたい、など)",
        color=0x00ff00
    )
    await channel.send(embed=embed_q1)

    # 回答待機
    def check(m):
        return m.author == member and m.channel == channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=300.0) # 5分待機
        # 成功した場合
        await complete_onboarding_tutorial(member, channel, msg.content)
        
    except asyncio.TimeoutError:
        await channel.send("...思考の波が途絶えました。また気が向いた時に書き込んでください。")
        
        # タイムアウトした場合: DBにリトライ待ちステータスを記録
        db = load_db()
        user_id = str(member.id)
        if user_id in db["users"]:
            db["users"][user_id]["onboarding_status"] = "pending_retry"
            save_db(db)
        return


async def create_personal_channel(member):
    guild = member.guild
    
    # カテゴリーの取得または作成
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if not category:
        category = await guild.create_category(CATEGORY_NAME)

    # ロールの作成
    role_name = f"role-times-{member.name}"
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(name=role_name)
    
    # ロールをメンバーに付与
    if role not in member.roles:
        await member.add_roles(role)

    # チャンネル名の決定 (times-ユーザー名)
    channel_name = f"times-{member.name}".lower().replace(" ", "-")
    
    # 権限設定 (Botと専用ロールのみ閲覧可)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }

    # チャンネル作成
    existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
    channel = None
    
    if not existing_channel:
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        print(f"Created channel for {member.name}")
    else:
        channel = existing_channel
        await channel.set_permissions(role, read_messages=True, send_messages=True)
        print(f"Updated channel permissions for {member.name}")
    
    # DBに記録
    db = load_db()
    user_id = str(member.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "channel_id": channel.id,
            "points": 0,
            "history": [],
            "expose_count": 0,
            "onboarding_status": "started" # ステータス初期化
        }
    else:
        # 既存ユーザーの場合はチャンネルIDだけ更新しておく
        db["users"][user_id]["channel_id"] = channel.id
        if "expose_count" not in db["users"][user_id]:
             db["users"][user_id]["expose_count"] = 0
        if "expose_count" not in db["users"][user_id]:
             db["users"][user_id]["expose_count"] = 0
        db["users"][user_id]["onboarding_status"] = "started" # 再実行時もステータスリセット

    # 興味関心設定の初期化 (既存・新規問わず確認)
    if "recommendation" not in db["users"][user_id]:
        db["users"][user_id]["recommendation"] = {
            "enabled": False,
            "interval_days": 3,
            "last_run": None
        }
             
    save_db(db)

    # ウェルカムメッセージ
    await channel.send(f"ようこそ、{member.mention}。ここはあなたの脳内（外部脳）です。\n気になったこと、意味のないこと、なんでも書き込んでください。\nAIがあなたの思考を誰かと接続します。")

    # チュートリアル開始 (非同期で実行)
    asyncio.create_task(run_onboarding_tutorial(member, channel))


async def simulate_ai_connection(guild, author, content, forced_keyword=None):
    """
    AIによるマッチングと「第三の文脈」生成 (Gemini版)
    forced_keyword: これが指定されている場合、過去ログからもこのキーワードを含むものを優先する
    """
    # DBからユーザーのチャンネルIDを取得
    db = load_db()
    user_data = db["users"].get(str(author.id))
    
    if not user_data or "channel_id" not in user_data:
        return

    channel_id = user_data["channel_id"]
    log_channel = guild.get_channel(channel_id)

    if not log_channel:
        return

    # 1. 現在の投稿をベクトル化
    try:
        # Gemini Embedding
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=content,
            task_type="semantic_similarity"
        )
        current_vector = result['embedding']
    except Exception as e:
        print(f"Gemini Embedding Error: {e}")
        return

    # 2. 過去ログから類似度60%前後のものを検索 (Designed Serendipity)
    best_match = None
    
    candidates = []

    for uid, udata in db["users"].items():
        # 自分自身の直近の発言は除外したいが、今回は簡易的に全探索
        for history in udata.get("history", []):
            if "vector" not in history:
                continue
            
            # コサイン類似度計算
            vec_a = np.array(current_vector)
            vec_b = np.array(history["vector"])
            
            # ベクトルが空またはサイズ違いのチェック
            if vec_a.size == 0 or vec_b.size == 0 or vec_a.shape != vec_b.shape:
                continue

            # キーワード強制マッチングロジック
            if forced_keyword:
                partner_stats = udata.get("keyword_stats", {})
                partner_count = partner_stats.get(forced_keyword, 0)
                
                # そのキーワードを含む発言か？ または そのキーワードの熟練者が発した言葉か？
                # 今回は「そのキーワードを含む発言」を対象としつつ、熟練度が高い人を優遇する
                if forced_keyword in history["content"]:
                    # 類似度を1.0固定ではなく、熟練度に応じて重み付けする
                    # base_score 1.0 + (count * 0.1) -> 最大 2.0くらいまで伸びる
                    score = 1.0 + min(partner_count * 0.1, 1.0)
                    
                    candidates.append({
                        "content": history["content"], 
                        "user_id": uid, 
                        "similarity": score, 
                        "is_keyword_match": True
                    })
                    continue
            
            similarity = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
            
            # 類似度が0.5 ~ 0.7の範囲にあるものを候補にする
            if 0.5 <= similarity <= 0.7:
                candidates.append({"content": history["content"], "user_id": uid, "similarity": similarity, "is_keyword_match": False})

    # 候補の選定
    keyword_matches = [c for c in candidates if c.get("is_keyword_match")]
    
    if keyword_matches:
        # スコア（熟練度込み）で重み付け抽選
        weights = [c["similarity"] for c in keyword_matches]
        best_match = random.choices(keyword_matches, weights=weights, k=1)[0]
    elif candidates:
        # なければ類似度マッチから選ぶ
        best_match = random.choice(candidates)
    else:
        # 候補がなければ、ランダムに過去ログから選ぶ（Asynchronous Synapsesの強制発動）
        # 全履歴からランダム取得
        all_history = []
        for uid, udata in db["users"].items():
            for h in udata.get("history", []):
                if h["content"] != content: # 完全一致は避ける
                    all_history.append({"content": h["content"], "user_id": uid})
        
        if all_history:
            best_match = random.choice(all_history)
            best_match["similarity"] = 0.0 # 擬似

    if not best_match:
        return

    partner_id = best_match["user_id"]
    partner_content = best_match["content"]
    partner_member = guild.get_member(int(partner_id))
    # partner_name = partner_member.name if partner_member else "Unknown User"

    # 3. Geminiで「第三の文脈」を生成 (The Third Context)
    prompt = f"""
    あなたは「思考の接続者」です。以下の2つの発言を接続し、新しい視座を提供してください。
    
    発言A (現在): "{content}"
    発言B (過去): "{partner_content}"
    
    【行動指針】
    状況に応じて以下のモードで振る舞ってください。
    - Mode A (Mirror): 孤独や不安を感じる場合 -> 共感し、過去の痛みと接続する。
    - Mode B (Prism): 議論やアイデアの場合 -> 全く異なる分野（建築、生物、料理など）の概念を用いて構造的類似性を指摘する。
    - Mode C (Ghost): 特定のキーワードの場合 -> 「過去にはこんな結論が出ていました」と歴史を提示する。

    【制約】
    - 決して「正解」を教えないでください。
    - 「お役に立てれば幸いです」などの定型句は禁止です。
    - 140文字以内で、詩的かつ哲学的に答えてください。
    - 出力は「接続コメント」のみにしてください。
    """

    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        ai_comment = response.text
    except Exception as e:
        print(f"Gemini Chat Error: {e}")
        ai_comment = "思考の回線が混線しています...しかし、偶然のノイズもまた一興です。"
    
    # ログチャンネル（またはユーザーのチャンネル）に投稿
    # ここではユーザーのチャンネルに投稿する
    embed = discord.Embed(title="⚡ 思考の接続", color=0x9900ff)
    embed.add_field(name="あなたの思考", value=content, inline=False)
    embed.add_field(name="過去の残響", value=partner_content, inline=False)
    embed.add_field(name="AIの視座", value=ai_comment, inline=False)
    
    await log_channel.send(embed=embed)


async def perform_recommendation(user_id, user_data, guild):
    """
    ユーザーの興味関心に基づいた記事を推薦する
    """
    channel_id = user_data["channel_id"]
    channel = guild.get_channel(channel_id)
    if not channel:
        return

    print(f"Running recommendation for user {user_id}...")

    # 1. 最近の履歴取得 (直近20件)
    history_content = []
    # historyがリストとして保存されているので後ろから取得
    recent_history = user_data.get("history", [])[-20:]
    for h in recent_history:
        history_content.append(h["content"])
    
    if not history_content:
        return

    joined_history = "\n".join(history_content)

    # 2. Geminiで検索クエリ生成
    # 2. Geminiで検索クエリ生成
    prompt = f"""
    以下のユーザーの発言履歴から、現在このユーザーが最も興味を持っている具体的なトピックを分析し、
    Web検索用の検索クエリを3つ生成してください。また、なぜそのクエリを選んだのか、ユーザーの発言に基づいた理由も添えてください。
    
    発言履歴:
    {joined_history}
    
    条件:
    - 具体的でニッチなキーワードを含めること
    - JSON形式のリスト [{{ "query": "検索クエリ", "reason": "選定理由" }}, ...] で返すこと
    - "reason" は「あなたは〜と言っていたので」「最近〜に興味があるようなので」のように、ユーザーへの語りかけ口調で短く記述すること
    - 余計な説明は省くこと
    """
    
    search_queries = []
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        text = response.text.strip()
        # JSON部分だけ抽出（マークダウン対策）
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        search_queries = json.loads(text)
    except Exception as e:
        print(f"Gemini Query Gen Error: {e}")
        return

    if not search_queries:
        return

    # 3. DuckDuckGoで検索
    results = []
    try:
        with DDGS() as ddgs:
            for item in search_queries:
                query = item.get("query")
                reason = item.get("reason", "")
                
                # 各クエリで1件だけ取得してバリエーションを出す
                r = list(ddgs.text(query, max_results=1))
                if r:
                    # 検索結果に理由を付与して保存
                    r[0]["reason"] = reason
                    results.extend(r)
    except Exception as e:
        print(f"DDGS Error: {e}")
        return

    if not results:
        return

    # 重複排除
    unique_results = []
    seen_urls = set()
    for res in results:
        if res['href'] not in seen_urls:
            unique_results.append(res)
            seen_urls.add(res['href'])
    
    # 4. 投稿
    embed = discord.Embed(title="🌐 興味の窓", description="あなたの発言から、興味がありそうな世界を覗いてみました。", color=0x00aaff)
    for res in unique_results[:3]:
        reason_text = f"\n💡 **選定理由**: {res.get('reason')}" if res.get('reason') else ""
        embed.add_field(name=res['title'], value=f"{res['body'][:100]}...{reason_text}\n[リンク]({res['href']})", inline=False)
    
    keywords = [q.get("query") for q in search_queries]
    embed.set_footer(text=f"Keywords: {', '.join(keywords)}")
    await channel.send(embed=embed)
    
    # 5. 最終実行日時の更新
    db = load_db()
    if "recommendation" not in db["users"][user_id]:
         db["users"][user_id]["recommendation"] = {}
    
    db["users"][user_id]["recommendation"]["last_run"] = datetime.now().isoformat()
    save_db(db)


@tasks.loop(hours=1)
async def recommendation_loop():
    """
    定期的にユーザーの最終実行日時を確認し、設定された日数が経過していれば推薦を実行する
    """
    # 準備完了まで待つ
    await bot.wait_until_ready()
    
    db = load_db()
    now = datetime.now()
    
    # GUILD_IDからguildオブジェクトを取得（複数サーバー対応の場合はループが必要だが今回は単一前提）
    guild = bot.get_guild(GUILD_ID)
    if not guild:
         # 環境変数等でGUILD_IDが正しく設定されていない場合のフォールバック
         # 接続しているギルドの最初を取得
         if bot.guilds:
             guild = bot.guilds[0]
         else:
             return

    try:
        updated = False
        for user_id, data in db["users"].items():
            config = data.get("recommendation", {})
            
            # 設定が無効ならスキップ
            if not config.get("enabled", False):
                continue
            
            interval_days = config.get("interval_days", 3)
            last_run_str = config.get("last_run")
            
            should_run = False
            if not last_run_str:
                should_run = True
            else:
                last_run = datetime.fromisoformat(last_run_str)
                delta = now - last_run
                if delta.days >= interval_days:
                    should_run = True
            
            if should_run:
                # 実行処理 (非同期で個別に走らせる)
                asyncio.create_task(perform_recommendation(user_id, data, guild))
    except Exception as e:
        print(f"Recommendation Loop Error: {e}")


# ==========================================
# EVENTS
# ==========================================

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    if not recommendation_loop.is_running():
        recommendation_loop.start()

@bot.event
async def on_member_join(member):
    """
    【機能1：自動オンボーディング】
    メンバー参加時に、その人専用のプライベートチャンネルを作成する
    """
    await create_personal_channel(member)

@bot.event
async def on_message(message):
    """
    【機能2：ポイントシステム & AIフック】
    投稿を検知してポイント加算 + AI処理への送信
    """
    if message.author.bot:
        return

    # DB読み込み
    db = load_db()
    user_id = str(message.author.id)

    # ユーザー登録がまだなら作成（既存メンバー用）
    if user_id not in db["users"]:
        db["users"][user_id] = {"channel_id": message.channel.id, "points": 0, "history": [], "expose_count": 0}

    # キーワード統計データの初期化
    if "keyword_stats" not in db["users"][user_id]:
        db["users"][user_id]["keyword_stats"] = {}

    # ==================================================
    # チュートリアルのリトライチェック
    # ==================================================
    if db["users"][user_id].get("onboarding_status") == "pending_retry":
        # リトライ待ち状態なら、この発言をチュートリアルの回答として処理
        # ステータスを進行中に変更（多重実行防止）
        db["users"][user_id]["onboarding_status"] = "processing"
        save_db(db)
        
        await complete_onboarding_tutorial(message.author, message.channel, message.content)
        # complete_onboarding_tutorial内で完了ステータスに更新される
        
        # 通常のポイント加算等はスキップするか、並行するかはお好みだが、
        # ここではチュートリアル回答もポイント対象にするため後続処理へ
    
    # ポイント加算 (+1pt)
    db["users"][user_id]["points"] += 1
    
    # ベクトル化して保存
    vector = []
    try:
        if GEMINI_API_KEY:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=message.content,
                task_type="semantic_similarity"
            )
            vector = result['embedding']
    except Exception as e:
        print(f"Embedding Error: {e}")

    # 投稿履歴の保存（AI解析用データとして）
    db["users"][user_id]["history"].append({
        "content": message.content,
        "timestamp": str(datetime.now()),
        "vector": vector
    })
    save_db(db)

    # ---------------------------------------------------------
    # 【機能3：AI思考接続 (Simulation)】
    # ---------------------------------------------------------
    
    # トリガー判定
    should_trigger = False
    forced_keyword = None
    trigger_prob = 0.1 # デフォルト確率
    
    # 1. キーワード判定 (優先)
    for kw in CONNECTION_KEYWORDS:
        if kw in message.content:
            # カウントアップ
            current_count = db["users"][user_id]["keyword_stats"].get(kw, 0)
            db["users"][user_id]["keyword_stats"][kw] = current_count + 1
            save_db(db) # 更新
            
            # 確率計算: 0.1 スタート、1回につき +0.09 -> 10回で1.0 (100%)
            # min(1.0, 0.1 + count * 0.09)
            # countが加算された最新の値を使う
            prob = min(1.0, 0.1 + (db["users"][user_id]["keyword_stats"][kw] * 0.09))
            
            # 確率が一番高いキーワードを優先する（複数ヒットした場合）
            if prob > trigger_prob:
                trigger_prob = prob
                forced_keyword = kw

    # 2. 確率判定
    # forced_keywordがある場合、trigger_probは上昇している
    if random.random() < trigger_prob:
        should_trigger = True

    if should_trigger:
        if GEMINI_API_KEY:
            # forced_keywordがあった場合はそれを渡す、なければNone
            await simulate_ai_connection(message.guild, message.author, message.content, forced_keyword)
        else:
            pass

    await bot.process_commands(message)

# ==========================================
# COMMANDS
# ==========================================

@bot.command()
async def init_channel(ctx, member: discord.Member):
    """
    指定したユーザーのチャンネルとロールを作成する（管理者専用）
    """
    if ctx.author.name != "udonpalta":
        await ctx.send("このコマンドを実行する権限がありません。")
        return

    await create_personal_channel(member)
    await ctx.send(f"{member.name} さんのチャンネルとロールのセットアップが完了しました。")

@bot.command()
async def status(ctx):
    """自分のポイントを確認するコマンド"""
    db = load_db()
    user_id = str(ctx.author.id)
    points = db["users"].get(user_id, {}).get("points", 0)
    expose_count = db["users"].get(user_id, {}).get("expose_count", 0)
    
    # 次回のコスト計算
    if expose_count == 0:
        next_cost = 1
    elif expose_count == 1:
        next_cost = 5
    elif expose_count == 2:
        next_cost = 10
    else:
        next_cost = 15

    await ctx.send(f"現在の保有ポイント: **{points} pt** 🪙\n露出回数: {expose_count}回 (次回コスト: {next_cost} pt)")

@bot.command()
async def expose(ctx):
    """
    【機能4：露出権の購入】
    ポイントを消費して、ランダムな3人に自分の部屋を24時間公開する
    """
    db = load_db()
    user_id = str(ctx.author.id)
    user_data = db["users"].get(user_id)

    if not user_data:
        await ctx.send("ユーザーデータがありません。まずは何か発言してください。")
        return

    # コスト計算
    expose_count = user_data.get("expose_count", 0)
    if expose_count == 0:
        cost = 1
    elif expose_count == 1:
        cost = 5
    elif expose_count == 2:
        cost = 10
    else:
        cost = 15

    if user_data["points"] < cost:
        await ctx.send(f"ポイントが足りません！ (必要: {cost} pt / 現在: {user_data.get('points', 0)} pt)")
        return

    # ポイント消費 & カウントアップ
    user_data["points"] -= cost
    user_data["expose_count"] = expose_count + 1
    save_db(db)

    # ターゲット選定（自分以外のメンバーからランダムに3人）
    members = [m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
    if len(members) < 1:
        await ctx.send("他にメンバーがいません...")
        return
    
    targets = random.sample(members, min(3, len(members)))
    
    # 権限変更（ロールを付与する）
    role_name = f"role-times-{ctx.author.name}"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        await ctx.send("あなたのチャンネルロールが見つかりません。")
        return

    exposed_names = []
    
    for target in targets:
        # ロール付与
        if role not in target.roles:
            await target.add_roles(role)
            exposed_names.append(target.name)
            # 通知を送る
            try:
                await target.send(f"⚡ **思考の介入** ⚡\n{ctx.author.name} さんがポイントを消費して、あなたに思考を公開しました。\nチャンネル: {ctx.channel.mention}")
            except:
                pass

    await ctx.send(f"✅ **露出成功** (回数: {expose_count+1}, 消費: {cost}pt)\n以下のメンバーにこの部屋を公開しました（ロール付与）。\n対象: {', '.join(exposed_names)}")

    # 24時間後に権限を戻す処理（非同期で待機）
    # ※ 本番環境ではBot再起動対策のため、DBで期限管理をする必要がある
    await asyncio.sleep(86400) # 24時間待機
    for target in targets:
        if target in ctx.guild.members: # メンバーがまだいるか確認
             await target.remove_roles(role) # ロール剥奪

@bot.command()
async def expose_to(ctx, member: discord.Member):
    """
    指定したユーザーに自分の部屋を永久公開する
    コスト: 通常のexpose + 1pt
    """
    db = load_db()
    user_id = str(ctx.author.id)
    user_data = db["users"].get(user_id)

    if not user_data:
        await ctx.send("ユーザーデータがありません。")
        return

    # コスト計算
    expose_count = user_data.get("expose_count", 0)
    if expose_count == 0:
        base_cost = 1
    elif expose_count == 1:
        base_cost = 5
    elif expose_count == 2:
        base_cost = 10
    else:
        base_cost = 15
    
    cost = base_cost + 1

    if user_data["points"] < cost:
        await ctx.send(f"ポイントが足りません！ (必要: {cost} pt / 現在: {user_data.get('points', 0)} pt)")
        return

    # ロール取得
    role_name = f"role-times-{ctx.author.name}"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("あなたのチャンネルロールが見つかりません。")
        return

    # ポイント消費 & カウントアップ
    user_data["points"] -= cost
    user_data["expose_count"] = expose_count + 1
    save_db(db)

    # ロール付与
    if role not in member.roles:
        await member.add_roles(role)
        try:
            await member.send(f"⚡ **思考の介入 (永続)** ⚡\n{ctx.author.name} さんがポイントを消費して、あなたに思考を永久公開しました。\nチャンネル: {ctx.channel.mention}")
        except:
            pass
        await ctx.send(f"✅ **永久露出成功** (回数: {expose_count+1}, 消費: {cost}pt)\n{member.name} にこの部屋を永久公開しました。")
    else:
        await ctx.send(f"{member.name} は既にこの部屋の閲覧権限を持っています。（ポイントは消費されました）")

@bot.command()
async def rename(ctx, new_name: str):
    """
    自分のチャンネル名を変更する
    """
    db = load_db()
    user_id = str(ctx.author.id)
    user_data = db["users"].get(user_id)

    if not user_data:
        await ctx.send("ユーザーデータがありません。")
        return

    # 実行場所が自分のチャンネルか確認
    if ctx.channel.id != user_data["channel_id"]:
        await ctx.send("自分のチャンネルでのみ実行できます。")
        return

    try:
        await ctx.channel.edit(name=new_name)
        await ctx.send(f"チャンネル名を `{new_name}` に変更しました。")
    except Exception as e:
        await ctx.send(f"変更に失敗しました: {e}")

@bot.command()
async def grant_access(ctx, receiver: discord.Member, target: discord.Member):
    """
    指定したユーザー(receiver)に、指定したユーザー(target)のチャンネル閲覧ロールを永久に付与する（管理者専用）
    """
    if ctx.author.name != "udonpalta":
        await ctx.send("このコマンドを実行する権限がありません。")
        return

    # targetのロールを取得
    role_name = f"role-times-{target.name}"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        await ctx.send(f"{target.name} さんのチャンネルロールが見つかりません。")
        return

    # receiverにロール付与
    if role not in receiver.roles:
        await receiver.add_roles(role)
        try:
            await receiver.send(f"⚡ **思考の介入 (管理者権限)** ⚡\n管理者によって、{target.name} さんの思考へのアクセス権が付与されました。")
        except:
            pass
        await ctx.send(f"✅ {receiver.name} さんに {target.name} さんのチャンネル閲覧権限を付与しました。")
    else:
        await ctx.send(f"{receiver.name} さんは既に {target.name} さんのチャンネル閲覧権限を持っています。")

@bot.command()
async def auto_recommend(ctx, days: int = 0):
    """
    AIによる興味関心サイトの定期共有設定
    引数: 日数 (例: /auto_recommend 3 で3日に1回)
    引数が0の場合、機能をオフにする
    """
    db = load_db()
    user_id = str(ctx.author.id)
    
    if user_id not in db["users"]:
         await ctx.send("ユーザーデータがありません。")
         return

    if "recommendation" not in db["users"][user_id]:
        db["users"][user_id]["recommendation"] = {}

    if days > 0:
        db["users"][user_id]["recommendation"]["enabled"] = True
        db["users"][user_id]["recommendation"]["interval_days"] = days
        # 初回実行を即座に行うか、次回ループで行うか。
        # ここでは「設定した」だけにして、ループに任せるが、Last Runがない場合はループが即拾うはず。
        # すでにLast Runがある場合、リセットしたいかどうか...とりあえずそのまま。
        
        save_db(db)
        await ctx.send(f"✅ 設定が完了しました。\n{days}日に1回のペースで、あなたの興味関心に基づいた記事を推薦しますﾖ。\n(これより、初回の推薦を即座に実行します...)")
        
        # 即時実行
        try:
            await perform_recommendation(user_id, db["users"][user_id], ctx.guild)
        except Exception as e:
            await ctx.send(f"⚠️ 初回実行中にエラーが発生しました: {e}")
    else:
        db["users"][user_id]["recommendation"]["enabled"] = False
        save_db(db)
        await ctx.send("🛑 定期推薦をオフにしました。")

# 実行
bot.run(TOKEN)
