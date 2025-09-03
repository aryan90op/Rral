import os
import time
import extract_msg
import vobject
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, PicklePersistence, CallbackContext, ContextTypes
import logging
import json
from datetime import datetime

# Configure logging for file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_activity.log', encoding='utf-8'),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)
logger = logging.getLogger(__name__)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Define states for conversation
CHOOSING = 0

ALLOWED_USERS_FILE = 'allowed_users.json'

# Load allowed users from JSON file
def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            return json.load(f)
    return {"users": []} # Ensure "users" key exists, even if the file is empty or malformed

# Save allowed users to JSON file
def save_allowed_users(allowed_users_data):
    with open(ALLOWED_USERS_FILE, 'w') as f:
        json.dump(allowed_users_data, f, indent=4)

# Initialize allowed users
ALLOWED_USERS_DATA = load_allowed_users()
ADMIN_IDS = [6497509361]  # List of allowed admin IDs

# Function to log activity
def log_activity(user_id, username, action, details=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] User ID: {user_id} (@{username}) - Action: {action}"
    if details:
        log_message += f" - Details: {details}"
    logger.info(log_message)

def convert_msg_to_txt(file_path):
    try:
        msg = extract_msg.Message(file_path)
        txt_file_path = file_path.replace('.msg', '.txt')
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Subject: {msg.subject}\n")
            f.write(f"From: {msg.sender}\n")
            f.write(f"To: {msg.to}\n")
            f.write(f"Date: {msg.date}\n")
            f.write("\nBody:\n")
            f.write(msg.body)
        return txt_file_path
    except Exception as e:
        print(f"Error converting MSG to TXT: {str(e)}")
        return None

def convert_txt_to_vcf(file_path, vcf_filename, contact_name, partition_size=None):
    """Function to convert a TXT file to VCF with a specified partition limit (default unlimited)"""
    try:
        logger.info(f"Converting TXT to VCF: {file_path} -> {vcf_filename}")
        # Read numbers from TXT file
        with open(file_path, 'r', encoding='utf-8') as f:
            numbers = [line.strip() for line in f if line.strip()]
        
        # Create VCF file(s)
        vcf_files = []  # List to store paths of created VCF files
        os.makedirs('downloads', exist_ok=True)
        
        # If partition_size is not specified, use the length of the numbers list
        if partition_size is None or partition_size > len(numbers):
            partition_size = len(numbers)
        
        for i in range(0, len(numbers), partition_size):  # Divide numbers into groups according to partition_size
            vcf_file_path = f"downloads/{vcf_filename}_{i//partition_size + 1}.vcf"  # VCF file name
            with open(vcf_file_path, 'w', encoding='utf-8') as f:
                for j in range(i, min(i + partition_size, len(numbers))):  # Take according to partition_size
                    f.write("BEGIN:VCARD\n")
                    f.write("VERSION:3.0\n")
                    f.write(f"FN:{contact_name} {j + 1}\n")  # Add sequential number
                    f.write(f"TEL;TYPE=CELL:{numbers[j]}\n")
                    f.write("END:VCARD\n")
            vcf_files.append(vcf_file_path)  # Store path of created VCF file
        
        return vcf_files  # Return list of created VCF files
    except Exception as e:
        logger.error(f"Error converting TXT to VCF: {str(e)}")
        return None

def convert_msg_to_vcf(file_path, adm_number, navy_number):
    try:
        logger.info(f"Converting MSG to VCF: {file_path}")
        msg = extract_msg.Message(file_path)
        vcf_file_path = file_path.replace('.msg', '.vcf')
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # ADM Format
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{msg.sender}\n")
            f.write(f"TEL:{adm_number}\n")  # ADM number without TYPE
            f.write(f"NOTE:SUBJECT: {msg.subject}\n")
            f.write(f"NOTE:DATE: {msg.date}\n")
            f.write(f"NOTE:BODY:\n{msg.body}\n")
            f.write("END:VCARD\n")
            
            # NAVY Format
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{msg.sender}\n")
            f.write(f"TEL:{navy_number}\n")  # NAVY number without TYPE
            f.write(f"NOTE:SUBJECT: {msg.subject}\n")
            f.write(f"NOTE:DATE: {msg.date}\n")
            f.write(f"NOTE:BODY:\n{msg.body}\n")
            f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error converting MSG to VCF: {str(e)}")
        return None

def convert_msg_to_adm_navy(file_path, adm_number, navy_number):
    try:
        msg = extract_msg.Message(file_path)
        adm_file_path = file_path.replace('.msg', '_ADM.txt')
        navy_file_path = file_path.replace('.msg', '_NAVY.txt')
        with open(adm_file_path, 'w', encoding='utf-8') as f:
            f.write("=== ADM FORMAT ===\n")
            f.write(f"FROM: {msg.sender}\n")
            f.write(f"TO: {adm_number}\n")  # Using the received ADM number
            f.write(f"DATE: {msg.date}\n")
            f.write(f"SUBJECT: {msg.subject}\n")
            f.write("\nBODY:\n")
            f.write(msg.body)
        with open(navy_file_path, 'w', encoding='utf-8') as f:
            f.write("=== NAVY FORMAT ===\n")
            f.write(f"FROM: {msg.sender}\n")
            f.write(f"TO: {navy_number}\n")  # Using the received NAVY number
            f.write(f"DATE: {msg.date}\n")
            f.write(f"SUBJECT: {msg.subject}\n")
            f.write("\nCONTENT:\n")
            f.write(msg.body)
        return (adm_file_path, navy_file_path)
    except Exception as e:
        print(f"Error converting MSG to ADM/NAVY: {str(e)}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Function to start the conversation and display the initial menu."""
    user = update.effective_user
    log_activity(user.id, user.username, "Started bot")
    reply_markup = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Start 🔄")],
            [KeyboardButton("1️⃣ MSG to TXT 📝"), KeyboardButton("2️⃣ TXT to VCF 📱")],
            [KeyboardButton("3️⃣ MSG to ADM & NAVY 📋"), KeyboardButton("4️⃣ MSG to VCF 📱")],
            [KeyboardButton("Developer 👨‍💻")]
        ],
        resize_keyboard=True
    )
    
    # Get username and escape special characters
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    # Escape special characters in username
    username = username.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]').replace('(', r'\(').replace(')', r'\)').replace('~', r'\~').replace('`', r'\`').replace('>', r'\>').replace('#', r'\#').replace('+', r'\+').replace('-', r'\-').replace('=', r'\=').replace('|', r'\|').replace('{', r'\{').replace('}', r'\}').replace('.', r'\.').replace('!', r'\!')

    # Welcome message with escaped username
    welcome_message = (
        f"*🤖 Hello {username}\\!*\n"
        "*Welcome to NagaHitam Bot\\!*\n"
        "Please select from the available menu 🚀:\n\n"
        "*1️⃣ Convert MSG to TXT*\n"
        "*2️⃣ Convert TXT to VCF*\n"
        "*3️⃣ Convert MSG to ADM & NAVY*\n"
        "*4️⃣ Convert MSG to VCF*"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='MarkdownV2')
    return CHOOSING

async def handle_text(update: Update, context: CallbackContext):
    """Function to handle text input from keyboard buttons"""
    user = update.effective_user
    text = update.message.text
    log_activity(user.id, user.username, "Text command", text)
    
    if text in ["Start 🔄", "Cancel"]:
        context.user_data.clear()
        return await start(update, context)
    elif text == "Developer 👨‍💻":
        dev_message = (
            "*👨‍💻 Developer Information\\:*\n\n"
            "*Name\\:* Naga Hitam\n"
            "*GitHub\\:* github\\.com/maryourbae\n"
            "*Telegram\\:* @toyng"
        )
        await update.message.reply_text(dev_message, parse_mode='MarkdownV2')
        return CHOOSING
    
    # Initialize if not already present
    if 'contact_name' not in context.user_data:
        context.user_data['contact_name'] = None
    if 'waiting_for_message_vcf' not in context.user_data:
        context.user_data['waiting_for_message_vcf'] = False
    if 'adm_numbers' not in context.user_data:
        context.user_data['adm_numbers'] = []
    if 'navy_numbers' not in context.user_data:
        context.user_data['navy_numbers'] = []

    # Handle menu option 1
    if text == "1️⃣ MSG to TXT 📝":
        context.user_data['waiting_for_number'] = True
        await update.message.reply_text(
            "Please enter the number to be saved.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_number'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Process canceled.")
            return await start(update, context)
            
        context.user_data['number'] = text
        context.user_data['waiting_for_number'] = False
        context.user_data['waiting_for_filename'] = True
        await update.message.reply_text("Please enter the filename (without extension):")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_filename'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Process canceled.")
            return await start(update, context)
            
        context.user_data['filename'] = text
        # Directly process and send the file
        try:
            number = context.user_data['number']
            filename = f"downloads/{text}.txt"
            
            # Ensure downloads directory exists
            os.makedirs('downloads', exist_ok=True)
            
            # Write number to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{number}\n")
            
            # Send file to user
            with open(filename, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=f"{text}.txt"
                )
            
            await update.message.reply_text("TXT file created successfully! ✅")
            
            # Clean up file
            if os.path.exists(filename):
                os.remove(filename)
            
            # Reset state and return to main menu
            context.user_data.clear()
            return await start(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ An error occurred: {str(e)}")
            context.user_data.clear()
            return await start(update, context)
    elif text == "2️⃣ TXT to VCF 📱":
        context.user_data['waiting_for_vcf_filename'] = True
        await update.message.reply_text(
            "Please enter a name for the VCF file.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_vcf_filename'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Process canceled.")
            return await start(update, context)
            
        context.user_data['vcf_filename'] = text
        context.user_data['waiting_for_vcf_filename'] = False
        context.user_data['waiting_for_partition_size'] = True
        await update.message.reply_text(
            "Please enter partition size (enter a number to limit, or press 'Enter' to not limit):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Enter")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_partition_size'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Process canceled.")
            return await start(update, context)
        
        partition_size = int(text) if text.isdigit() else None  # Use None if input is not valid
        context.user_data['partition_size'] = partition_size
        context.user_data['waiting_for_partition_size'] = False
        context.user_data['waiting_for_contact_name'] = True
        await update.message.reply_text("Please enter the contact name:")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_contact_name'):
        if text.lower() == 'cancel':
            context.user_data.clear()
            await update.message.reply_text("❌ Process canceled.")
            return await start(update, context)
            
        context.user_data['contact_name'] = text
        context.user_data['waiting_for_contact_name'] = False
        context.user_data['waiting_for_txt_file'] = True
        await update.message.reply_text("Please send the TXT file to be converted.")
        return CHOOSING
    
    elif text == "3️⃣ MSG to ADM & NAVY 📋":
        context.user_data['waiting_for_adm_number'] = True
        await update.message.reply_text(
            "Enter Admin numbers (one per line):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Cancel")]], resize_keyboard=True)
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_adm_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Process canceled. Returning to main menu.")
            context.user_data['waiting_for_adm_number'] = False
            return await start(update, context)
        
        # Separate input by newlines and add to list
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                context.user_data['adm_numbers'].append(number.strip())
        
        # Directly proceed to Navy input
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = True
        await update.message.reply_text("Enter Navy numbers (one per line):")
        return CHOOSING
    
    elif context.user_data.get('waiting_for_navy_number'):
        if text.lower() == 'cancel':
            await update.message.reply_text("❌ Process canceled. Returning to main menu.")
            context.user_data['waiting_for_navy_number'] = False
            return await start(update, context)
        
        # Separate input by newlines and add to list
        numbers = text.strip().split('\n')
        for number in numbers:
            if number.strip():
                context.user_data['navy_numbers'].append(number.strip())
        
        # Directly process VCF creation
        adm_numbers = context.user_data['adm_numbers']
        navy_numbers = context.user_data['navy_numbers']
        
        # Create VCF file with the given numbers
        vcf_file_path = create_vcf_from_multiple_numbers(adm_numbers, navy_numbers)
        
        if vcf_file_path:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(vcf_file_path, 'rb'),
                filename="AdminNavy.vcf"
            )
            await update.message.reply_text("Admin & Navy file created successfully! ✅")
        else:
            await update.message.reply_text('An error occurred: VCF file could not be created.')
        
        # Reset state
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False
        
        # Return to main menu
        return await start(update, context)
    elif text == "4️⃣ MSG to VCF 📱":
        context.user_data['waiting_for_message_vcf'] = True
        context.user_data['contact_name'] = None
        context.user_data['contact_numbers'] = []  # Reset number list
        context.user_data['waiting_for_numbers'] = False
        await update.message.reply_text(
            "Please enter the contact name for the VCF."
        )
        return CHOOSING
    
    elif context.user_data.get('waiting_for_message_vcf'):
        if text.lower() == 'cancel':
            # Reset all states
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_numbers'] = False
            await update.message.reply_text("❌ Process canceled. Returning to main menu.")
            return await start(update, context)
            
        if context.user_data['contact_name'] is None:
            # Save contact name
            context.user_data['contact_name'] = text
            context.user_data['waiting_for_numbers'] = True
            await update.message.reply_text(
                f"Contact name '{text}' has been saved.\n"
                "Please send contact numbers (can be more than one, separate with newlines)."
            )
            return CHOOSING
        
        elif context.user_data.get('waiting_for_numbers'):
            # Process contact numbers and directly create VCF
            numbers = text.strip().split('\n')
            contact_numbers = [num.strip() for num in numbers if num.strip()]
            contact_name = context.user_data['contact_name']
            
            # Create VCF file (without message)
            vcf_file_path = create_vcf_from_contacts([{'name': contact_name, 'number': num} for num in contact_numbers])
            
            if vcf_file_path:
                try:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(vcf_file_path, 'rb'),
                        filename=f"{contact_name}.vcf"
                    )
                    await update.message.reply_text("VCF file created successfully! ✅")
                except Exception as e:
                    await update.message.reply_text(f"❌ An error occurred while sending the file: {str(e)}")
            else:
                await update.message.reply_text("❌ An error occurred while creating the VCF file.")
            
            # Reset all states
            context.user_data['waiting_for_message_vcf'] = False
            context.user_data['contact_name'] = None
            context.user_data['contact_numbers'] = []
            context.user_data['waiting_for_numbers'] = False
            
            # Return to main menu
            return await start(update, context)

    # If no conditions are met
    await update.message.reply_text(
        "Please select an available menu option or send a file to convert."
    )
    
    return CHOOSING

async def button(update: Update, context: CallbackContext):
    """Function to handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'done': # Changed 'selesai' to 'done' for consistency
        # If the user clicks the 'Done' button, process VCF creation
        adm_numbers = context.user_data['adm_numbers']
        navy_numbers = context.user_data['navy_numbers']
        
        # Create VCF file with the given numbers
        vcf_file_path = create_vcf_from_numbers(adm_numbers, navy_numbers)
        
        if vcf_file_path:
            await context.bot.send_document(chat_id=query.message.chat.id, document=open(vcf_file_path, 'rb'), filename="contacts.vcf")
        else:
            await query.message.reply_text('An error occurred: VCF file could not be created.')
        
        # Reset state
        context.user_data['adm_numbers'] = []
        context.user_data['navy_numbers'] = []
        context.user_data['waiting_for_adm_number'] = False
        context.user_data['waiting_for_navy_number'] = False

    # Add other button logic if needed

async def save_message_to_txt(update: Update, context: CallbackContext):
    """Function to save a message to a TXT file"""
    try:
        number = context.user_data['number']
        filename = f"downloads/{context.user_data['filename']}.txt"
        
        # Ensure downloads directory exists
        os.makedirs('downloads', exist_ok=True)
        
        # Write number to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{number}\n")
        
        # Send file to user using file path
        with open(filename, 'rb') as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename=f"{context.user_data['filename']}.txt"
            )
        
        # Reset state
        context.user_data['waiting_for_message'] = False
        
        # Delete file after sending
        cleanup_files(filename)
        
        await update.message.reply_text("TXT file created successfully! ✅")
    
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
        context.user_data['waiting_for_message'] = False

async def message_handler(update: Update, context: CallbackContext):
    """Handler for all text messages"""
    if context.user_data.get('waiting_for_message'):
        await save_message_to_txt(update, context)
    else:
        await handle_text(update, context)

async def handle_file(update: Update, context: CallbackContext):
    """Function to handle files sent by the user"""
    try:
        user = update.effective_user
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        log_activity(user.id, user.username, "File upload", file_name)
        
        # Download file
        downloaded_file = f"downloads/{file_name}"
        os.makedirs('downloads', exist_ok=True)
        await file.download_to_drive(downloaded_file)
        
        if context.user_data.get('waiting_for_txt_file'):
            # Convert TXT to VCF
            vcf_filename = context.user_data.get('vcf_filename', 'contacts')
            contact_name = context.user_data.get('contact_name', 'Contact')
            vcf_files = convert_txt_to_vcf(downloaded_file, vcf_filename, contact_name, context.user_data.get('partition_size'))
            
            if vcf_files:
                for vcf_file in vcf_files:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(vcf_file, 'rb'),
                        filename=os.path.basename(vcf_file)
                    )
                await update.message.reply_text("All VCF files created successfully ✅!")
            else:
                await update.message.reply_text("❌ An error occurred while creating the VCF file.")
            
            # Reset state
            context.user_data.clear()
            return await start(update, context)
        
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")
        context.user_data.clear()
        return await start(update, context)

def cleanup_files(*files):
    """Function to clean up temporary files"""
    for file_path in files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {str(e)}")

def create_vcf_from_numbers(adm_numbers, navy_numbers):
    try:
        vcf_file_path = "downloads/Admin & Navy.vcf"  # Define VCF file name
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Write all numbers in one VCF file
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write("FN:Admin\n")
            for adm_number in adm_numbers:
                f.write(f"TEL;TYPE=CELL:{adm_number}\n")
            f.write("END:VCARD\n")
            
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write("FN:Navy\n")
            for navy_number in navy_numbers:
                f.write(f"TEL;TYPE=CELL:{navy_number}\n")
            f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error creating VCF: {str(e)}")
        return None

def create_vcf_from_message(contact_name, message_text, contact_numbers, vcf_filename=None):
    """Function to create a VCF file from a message and a list of contact numbers"""
    try:
        # Use the given filename or contact name if none
        filename = vcf_filename if vcf_filename else contact_name
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        vcf_file_path = f"downloads/{safe_filename}.vcf"
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            for number in contact_numbers:
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{contact_name}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")  # Store contact number
                f.write("NOTE:\n")
                
                # Split message into lines to avoid overly long lines
                message_lines = message_text.split('\n')
                for line in message_lines:
                    escaped_line = line.replace(',', '\\,').replace(';', '\\;')
                    f.write(escaped_line + '\\n')
                
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        print(f"Error creating VCF from message: {str(e)}")
        return None

def create_vcf_from_multiple_numbers(adm_numbers, navy_numbers):
    """Function to create VCF from Admin and Navy numbers"""
    try:
        logger.info(f"Creating VCF from multiple numbers - ADM: {len(adm_numbers)}, NAVY: {len(navy_numbers)}")
        vcf_file_path = "downloads/AdminNavy.vcf"
        os.makedirs('downloads', exist_ok=True)
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            # Write Admin numbers
            for i, number in enumerate(adm_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:Admin {i}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")
            
            # Write Navy numbers
            for i, number in enumerate(navy_numbers, 1):
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:Navy {i}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        logger.error(f"Error creating VCF: {str(e)}")
        return None

def create_vcf_from_contacts(contacts):
    """Function to create VCF from a list of contacts"""
    try:
        vcf_file_path = "downloads/contacts.vcf"
        os.makedirs('downloads', exist_ok=True)
        
        with open(vcf_file_path, 'w', encoding='utf-8') as f:
            for contact in contacts:
                f.write("BEGIN:VCARD\n")
                f.write("VERSION:3.0\n")
                f.write(f"FN:{contact['name']}\n")
                f.write(f"TEL;TYPE=CELL:{contact['number']}\n")
                f.write("END:VCARD\n")
        
        return vcf_file_path
    except Exception as e:
        logger.error(f"Error creating VCF: {str(e)}")
        return None

async def convert_and_send_vcf(update: Update, context: CallbackContext, file_path, adm_number, navy_number):
    try:
        vcf_file_path = convert_msg_to_vcf(file_path, adm_number, navy_number)
        
        if vcf_file_path:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(vcf_file_path, '

def _build_application(_token: str):
    application = ApplicationBuilder().token(_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(CallbackQueryHandler(button))
    return application

if __name__ == "__main__":
    import asyncio
    os.makedirs("downloads", exist_ok=True)

    _token = os.getenv("BOT_TOKEN") or "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE"
    if not _token or "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE" in _token:
        raise RuntimeError("Please set BOT_TOKEN env var or replace placeholder with your real token.")

    app = _build_application(_token)
    print("✅ Bot is running...")
    asyncio.run(app.run_polling())
