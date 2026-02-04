import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==============================
# CONFIGURATION
# ==============================

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

CRENEAUX = [
    "8h-9h30",
    "9h30-11h",
    "11h-12h30",
    "14h-15h30",
    "15h30-17h",
    "17h-18h30"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

NOM_SHEET = "Indisponibilites-enseignants"  # <- ton nom exact du Google Sheet

# ==============================
# CONNEXION GOOGLE SHEETS
# ==============================

try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open(NOM_SHEET).sheet1
    st.success("✅ Connexion Google Sheets OK")
except Exception as e:
    st.error(f"❌ Erreur connexion Google Sheets : {e}")
    st.stop()

# ==============================
# RÉCUPÉRATION LISTE UTILISATEURS
# ==============================

try:
    worksheet_users = client.open(NOM_SHEET).worksheet("Utilisateurs")
    data_users = worksheet_users.get_all_values()[1:]  # ignorer la ligne d'en-tête
    utilisateurs = [f"{row[0]} ({row[1]} {row[2]})" for row in data_users]
except Exception as e:
    st.error(f"❌ Impossible de récupérer la liste des utilisateurs : {e}")
    st.stop()

# ==============================
# INTERFACE
# ==============================

st.set_page_config(page_title="Indisponibilités", layout="centered")
st.title("📅 Saisie des indisponibilités")
st.write(
    "Sélectionnez votre nom, cochez les créneaux où vous êtes **indisponible** puis cliquez sur **Enregistrer**."
)

# Menu déroulant pour sélectionner l'utilisateur
user_selection = st.selectbox(
    "Sélectionnez votre enseignant",
    utilisateurs,
    index=0
)
# Extraire juste le code pour l'enregistrement
user_code = user_selection.split(" ")[0]

st.divider()

sel
