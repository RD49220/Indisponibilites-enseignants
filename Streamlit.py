import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import os

# ======================
# BREVO SDK
# ======================
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail

# ======================
# CONFIGURATION BREVO
# ======================
configuration = Configuration()
configuration.api_key['api-key'] = st.secrets["BREVO_API_KEY"]  # clé stockée dans st.secrets
def envoyer_email(destinataire, sujet, contenu):
    try:
        api_instance = TransactionalEmailsApi(ApiClient(configuration))
        send_smtp_email = SendSmtpEmail(
            to=[{"email": destinataire}],
            sender={"email": st.secrets["EMAIL_FROM"], "name": "Planning GEII"},
            subject=sujet,
            text_content=contenu
        )
        api_instance.send_transac_email(send_smtp_email)
        return True, ""
    except Exception as e:
        return False, str(e)

# ======================
# CONFIG GOOGLE SHEETS
# ======================
NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"
ADMIN_PASSWORD = st.secrets.get("admin_password", "monmotdepasse")  # 🔑 mot de passe admin

# ======================
# AUTH GOOGLE
# ======================
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
client = gspread.authorize(creds)

# ======================
# CHARGEMENT DES FEUILLES
# ======================
try:
    if "sheet" not in st.session_state:
        st.session_state.sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    if "users_sheet" not in st.session_state:
        st.session_state.users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
except Exception as e:
    st.error(f"Impossible d'accéder à une des feuilles Google Sheet.\n{e}")
    st.stop()

# ======================
# CHARGEMENT DES DONNÉES
# ======================
if "all_data" not in st.session_state:
    st.session_state.all_data = st.session_state.sheet.get_all_values()
if "users_data" not in st.session_state:
    st.session_state.users_data = st.session_state.users_sheet.get_all_values()[1:]

# ======================
# SESSION STATE
# ======================
if "selected_user" not in st.session_state:
    st.session_state.selected_user = ""
if "email_utilisateur" not in st.session_state:
    st.session_state.email_utilisateur = ""

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# UTILISATEUR
# ======================
users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[label]

# 🔄 Reset si utilisateur change
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code

# ======================
# EMAIL UTILISATEUR
# ======================
st.text_input("Votre adresse email pour recevoir le récapitulatif :", key="email_utilisateur")

# ======================
# BOUTON ENREGISTRER
# ======================
if st.button("💾 Enregistrer"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Enregistrement minimal dans Google Sheets
    st.session_state.sheet.append_row([
        user_code, now, "Test d'enregistrement"
    ], value_input_option="USER_ENTERED")

    st.success("✅ Indisponibilités enregistrées dans Google Sheets")

    # ======================
    # ENVOI EMAIL
    # ======================
    destinataire = st.session_state.email_utilisateur
    sujet = f"Récapitulatif des indisponibilités - {now}"
    contenu = "test"

    success, msg = envoyer_email(destinataire, sujet, contenu)

    if success:
        st.success(f"✅ Email envoyé à {destinataire}")
    else:
        st.error(f"❌ Erreur envoi mail : {msg}")
