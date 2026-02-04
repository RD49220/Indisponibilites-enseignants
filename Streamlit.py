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

JOURS_CODE = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN"
}

CRENEAUX_CODE = {
    "8h-9h30": "_1",
    "9h30-11h": "_2",
    "11h-12h30": "_3",
    "14h-15h30": "_4",
    "15h30-17h": "_5",
    "17h-18h30": "_6"
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

NOM_SHEET = "Indisponibilites-enseignants"

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
# UTILISATEURS
# ==============================

worksheet_users = client.open(NOM_SHEET).worksheet("Utilisateurs")
data_users = worksheet_users.get_all_values()[1:]
utilisateurs = [f"{r[0]} ({r[1]} {r[2]})" for r in data_users]

# ==============================
# INTERFACE
# ==============================

st.set_page_config(page_title="Indisponibilités", layout="centered")
st.title("📅 Saisie des indisponibilités")

user_selection = st.selectbox(
    "Sélectionnez votre enseignant",
    utilisateurs
)
user_code = user_selection.split(" ")[0]

st.divider()

# ==============================
# 🔹 PRÉ-COCHAGE DES ANCIENNES DONNÉES
# ==============================

# Réinitialiser les cases si on change d'utilisateur
if "current_user" not in st.session_state or st.session_state.current_user != user_code:
    st.session_state.clear()
    st.session_state.current_user = user_code

    all_data = sheet.get_all_values()

    for row in all_data[1:]:
        if row[0] == user_code:
            jour = row[1]
            creneau = row[2]
            key = f"{jour}_{creneau}"
            st.session_state[key] = True

# ==============================
# CHECKBOXES
# ==============================

selections = []

for jour in JOURS:
    st.subheader(jour)
    cols = st.columns(3)
    for i, creneau in enumerate(CRENEAUX):
        key = f"{jour}_{creneau}"
        if cols[i % 3].checkbox(creneau, key=key):
            code_creneau = JOURS_CODE[jour] + CRENEAUX_CODE[creneau]
            selections.append([
                user_code,
                jour,
                creneau,
                code_creneau,
                datetime.now().isoformat()
            ])

st.divider()

commentaire = st.text_area("💬 Commentaire libre (optionnel)")

st.divider()

# ==============================
# ENREGISTREMENT
# ==============================

if st.button("💾 Enregistrer"):
    if not selections:
        st.warning("Aucun créneau sélectionné.")
        st.stop()

    # En-têtes si feuille vide
    if sheet.get_all_values() == []:
        sheet.append_row([
            "Utilisateur",
            "Jour",
            "Créneau",
            "Code_Créneau",
            "Commentaire",
            "Timestamp"
        ])

    all_data = sheet.get_all_values()
    existing_rows = [
        i for i, row in enumerate(all_data[1:], start=2)
        if row[0] == user_code
    ]

    if existing_rows:
        st.warning(
            "⚠️ Vous avez déjà enregistré des indisponibilités.\n"
            "Confirmez pour écraser les anciennes données."
        )

        confirmer = st.checkbox("Je confirme l’écrasement")

        if not confirmer:
            st.stop()

        for r in reversed(existing_rows):
            sheet.delete_rows(r)

    for row in selections:
        sheet.append_row(row[:4] + [commentaire] + [row[4]])

    st.success("✅ Indisponibilités enregistrées avec succès")
