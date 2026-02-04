import streamlit as st
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

NOM_SHEET = "Indisponibilites-enseignants"

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
    data_users = worksheet_users.get_all_values()[1:]
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
user_code = user_selection.split(" ")[0]

st.divider()

# ==============================
# AFFICHAGE DES CHECKBOXES
# ==============================

selections = []

for jour in JOURS:
    st.subheader(jour)
    cols = st.columns(3)
    for i, creneau in enumerate(CRENEAUX):
        key = f"{jour}_{creneau}"
        # 🔹 On ne modifie pas st.session_state, juste on lit la valeur de la checkbox
        checked = cols[i % 3].checkbox(creneau, key=key)
        if checked:
            selections.append([
                user_code,
                jour,
                creneau,
                datetime.now().isoformat()  # timestamp
            ])

st.divider()

# Champ commentaire juste avant le bouton
commentaire = st.text_area("💬 Commentaire libre (optionnel)")

st.divider()

# ==============================
# ENREGISTREMENT
# ==============================

if st.button("💾 Enregistrer"):
    if not user_code:
        st.error("Merci de sélectionner votre nom / initiales.")
    elif not selections:
        st.warning("Aucun créneau sélectionné.")
    else:
        # 🔹 Ajouter les en-têtes si le Sheet est vide
        try:
            if sheet.row_count == 0 or sheet.get_all_values() == []:
                sheet.append_row(["Utilisateur", "Jour", "Créneau", "Commentaire", "Timestamp"])
        except Exception as e:
            st.error(f"❌ Impossible d'ajouter les en-têtes : {e}")
            st.stop()

        # 🔹 Ajouter le commentaire avant le timestamp
        for row in selections:
            row = row[:3] + [commentaire] + [row[3]]
            sheet.append_row(row)

        st.success("✅ Vos indisponibilités et commentaires ont été enregistrés.")
