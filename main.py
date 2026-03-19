#!/usr/bin/env python3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from google.oauth2.service_account import Credentials
from google.calendar import Calendar
import gspread
from datetime import datetime, timedelta
import logging
import os
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8607882635:AAGLElvbJwrnz4r8oyJzf4xwG11pbR0Gd60"
ADMIN_ID = 6485042007
NAME, PHONE, EMAIL, DATE, EVENT_TYPE, GUESTS, SERVICES = range(7)
clients = {}
PRICES = {"salle": 8550, "decoration": 3000, "vestiaire": 2000, "parking_unit": 50}

def get_google_creds():
try:
creds_json = os.getenv("GOOGLE_CREDS")
if creds_json:
import json
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/calendar"])
return creds
except:
pass
return None

def save_to_sheets(data, total_ttc):
try:
creds = get_google_creds()
if not creds:
return False
gc = gspread.authorize(creds)
sheet = gc.open("ArielEvents - Demandes").sheet1
sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), data.get("nom"), data.get("telephone"), data.get("email"), data.get("date"), data.get("type"), data.get("invites"), ", ".join(data.get("services", [])), total_ttc * 0.30, "En attente"])
return True
except Exception as e:
logger.error(f"Erreur Sheets: {e}")
return False

def generate_pdf_devis(data, total_ht, tva, total_ttc):
try:
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=letter)
elements = []
styles = getSampleStyleSheet()
title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#003366'), spaceAfter=12)
elements.append(Paragraph("DEVIS ARIELEVENTS", title_style))
elements.append(Spacer(1, 0.3*inch))
data_table = [["Client:", data['nom']], ["Téléphone:", data['telephone']], ["Email:", data['email']], ["", ""], ["Événement:", data['type']], ["Date:", data['date']], ["Invités:", str(data['invites'])]]
t = Table(data_table, colWidths=[2*inch, 4*inch])
t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.lightgrey), ('TEXTCOLOR', (0, 0), (-1, -1), colors.black), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 12), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
elements.append(t)
elements.append(Spacer(1, 0.5*inch))
pricing_data = [["DÉTAIL", "MONTANT"], ["Salle Wagram", f"{PRICES['salle']}€"]]
if "decoration" in data.get("services", []):
pricing_data.append(["Décoration", f"{PRICES['decoration']}€"])
if "vestiaire" in data.get("services", []):
pricing_data.append(["Vestiaire", f"{PRICES['vestiaire']}€"])
if "parking" in data.get("services", []):
parking = PRICES["parking_unit"] * data['invites']
pricing_data.append(["Parking voiturier", f"{parking}€"])
pricing_data.extend([["", ""], ["TOTAL HT", f"{total_ht}€"], ["TVA (20%)", f"{tva:.2f}€"], ["TOTAL TTC", f"{total_ttc:.2f}€"], ["", ""], ["ACOMPTE 30%", f"{total_ttc * 0.30:.2f}€"]])
pt = Table(pricing_data, colWidths=[3*inch, 3*inch])pt.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 12), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (-1, -3), (-1, -1), colors.HexColor('#FFFFCC')), ('FONTNAME', (-1, -3), (-1, -1), 'Helvetica-Bold')]))elements.append(pt)
doc.build(elements)
buffer.seek(0)
return buffer
except Exception as e:
logger.error(f"Erreur PDF: {e}")
return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id] = {}
await update.message.reply_text("Bonjour! Bienvenue chez ArielEvents! Quel est votre nom et prénom?")
return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id]["nom"] = update.message.text
await update.message.reply_text("Quel est votre numéro de téléphone?")
return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id]["telephone"] = update.message.text
await update.message.reply_text("Votre adresse e-mail?")
return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id]["email"] = update.message.text
await update.message.reply_text("La date de l'événement? (JJ/MM/YYYY)")
return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id]["date"] = update.message.text
await update.message.reply_text("Type d'événement?")
return EVENT_TYPE

async def get_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
clients[user_id]["type"] = update.message.text
await update.message.reply_text("Nombre d'invités?")
return GUESTS

async def get_guests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
user_id = update.effective_user.id
try:
clients[user_id]["invites"] = int(update.message.text)
except ValueError:
await update.message.reply_text("Nombre valide svp")
return GUESTS
keyboard = [[InlineKeyboardButton("Décoration", callback_data="decoration"), InlineKeyboardButton("Vestiaire", callback_data="vestiaire"), InlineKeyboardButton("Parking", callback_data="parking")], [InlineKeyboardButton("TERMINER", callback_data="finish")]]
reply_markup = InlineKeyboardMarkup(keyboard)
clients[user_id]["services"] = []
await update.message.reply_text("Quels services désirez-vous?", reply_markup=reply_markup)
return SERVICES

async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
query = update.callback_query
await query.answer()
user_id = query.from_user.id
if query.data == "finish":
await generate_quote(query, context, user_id)
return ConversationHandler.END
else:
if query.data not in clients[user_id]["services"]:
clients[user_id]["services"].append(query.data)
services_text = ", ".join(clients[user_id]["services"]) if clients[user_id]["services"] else "Aucun"
keyboard = [[InlineKeyboardButton("Décoration", callback_data="decoration"), InlineKeyboardButton("Vestiaire", callback_data="vestiaire"), InlineKeyboardButton("Parking", callback_data="parking")], [InlineKeyboardButton("TERMINER", callback_data="finish")]]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(text=f"Sélectionnés: {services_text}", reply_markup=reply_markup)
return SERVICES

async def generate_quote(query, context, user_id):
data = clients[user_id]
total_ht = PRICES["salle"]
if "decoration" in data["services"]: total_ht += PRICES["decoration"]
if "vestiaire" in data["services"]: total_ht += PRICES["vestiaire"]
if "parking" in data["services"]: total_ht += PRICES["parking_unit"] * data["invites"]
tva = total_ht * 0.20total_ttc = total_ht + tva
acompte = total_ttc * 0.30
quote_msg = f"DEVIS: {data['nom']} - {data['type']} - {data['date']}\nTotal HT: {total_ht}€\nTVA: {tva:.2f}€\nTOTAL TTC: {total_ttc:.2f}€\nAcompte 30%: {acompte:.2f}€"
await query.edit_message_text(text=quote_msg)
pdf_buffer = generate_pdf_devis(data, total_ht, tva, total_ttc)
if pdf_buffer:
await context.bot.send_document(chat_id=user_id, document=pdf_buffer, filename=f"devis_{data['nom']}.pdf")
admin_msg = f"NOUVELLE DEMANDE\nNom: {data['nom']}\nTel: {data['telephone']}\nEmail: {data['email']}\nDate: {data['date']}\nTotal: {total_ttc:.2f}€"
keyboard = [[InlineKeyboardButton("CONFIRMER", callback_data=f"confirm_{user_id}"), InlineKeyboardButton("REFUSER", callback_data=f"refuse_{user_id}")]]
reply_markup = InlineKeyboardMarkup(keyboard)
await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=reply_markup)
save_to_sheets(data, total_ttc)

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if query.data.startswith("confirm"):
user_id = int(query.data.split("_")[1])
await query.edit_message_text(text="CONFIRMEE")
await context.bot.send_message(chat_id=user_id, text="CONFIRME! Votre réservation est validée!")
else:
user_id = int(query.data.split("_")[1])
await query.edit_message_text(text="REFUSEE")
await context.bot.send_message(chat_id=user_id, text="Non disponible")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
await update.message.reply_text("Annulé")
return ConversationHandler.END

def main():
app = Application.builder().token(TOKEN).build()
conv_handler = ConversationHandler(entry_points=[CommandHandler("start", start)], states={NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)], PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)], EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)], DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)], EVENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event_type)], GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_guests)], SERVICES: [CallbackQueryHandler(handle_services)]}, fallbacks=[CommandHandler("cancel", cancel)])
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(confirm|refuse)_"))
logger.info("BOT ARIEL EVENTS DEMARRÉ!")
app.run_polling()

if __name__ == "__main__":
main()
