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

NOM_SHEET = "Indisponibilites-enseignants"  # <- ton nom exact de Google Sheet

# ==============================
# CONNEXION GOOGLE SHEETS
# ==============================

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open(NOM_SHEET).sheet1

# ==============================
# INTERFACE
# ==============================

st.set_page_config(page_title="Indisponibilités", layout="centered")

st.title("📅 Saisie des indisponibilités")
st.write(
    "Cochez les créneaux où vous êtes **indisponible** puis cliquez sur **Enregistrer**."
)

user = st.text_input("Vos initiales / votre nom")

st.divider()

selections = []

for jour in JOURS:
    st.subheader(jour)
    cols = st.columns(3)
    for i, creneau in enumerate(CRENEAUX):
        if cols[i % 3].checkbox(creneau, key=f"{jour}_{creneau}"):
            selections.append([
                user,
                jour,
                creneau,
                datetime.now().isoformat()
            ])

st.divider()

# ==============================
# ENREGISTREMENT
# ==============================

if st.button("💾 Enregistrer"):
    if not user:
        st.error("Merci d’indiquer votre nom ou vos initiales.")
    elif not selections:
        st.warning("Aucun créneau sélectionné.")
    else:
        for row in selections:
            sheet.append_row(row)

        st.success("✅ Vos indisponibilités ont été enregistrées.")
