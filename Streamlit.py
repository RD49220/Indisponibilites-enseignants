import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ======================
# CONFIG
# ======================
NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"

JOURS = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN"
}

CRENEAUX = {
    "1": "8h-9h30",
    "2": "9h30-11h",
    "3": "11h-12h30",
    "4": "13h30-15h",
    "5": "15h-16h30"
}

# ======================
# AUTH GOOGLE SHEETS
# ======================
creds_dict = st.secrets["gcp_service_account"]

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# CHARGER UTILISATEURS
# ======================
users_data = users_sheet.get_all_values()[1:]  # skip header
users = [
    {
        "code": row[0],
        "nom": row[1],
        "prenom": row[2]
    }
    for row in users_data if row
]

options = {
    f"{u['code']} – {u['nom']} {u['prenom']}": u["code"]
    for u in users
}

selected_label = st.selectbox(
    "Choisissez votre nom",
    options.keys()
)

user_code = options[selected_label]

# ======================
# RESET CHECKBOXES SI CHANGEMENT D'UTILISATEUR
# ======================
if 'last_user' not in st.session_state:
    st.session_state['last_user'] = None

if st.session_state['last_user'] != user_code:
    # reset toutes les checkbox de créneaux
    for jour_code in JOURS.values():
        for num in CRENEAUX.keys():
            key = f"{jour_code}_{num}"
            if key in st.session_state:
                del st.session_state[key]
    st.session_state['last_user'] = user_code

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
user_rows = [
    row for row in all_data[1:]
    if row[0] == user_code
]

existing_codes = set()
for row in user_rows:
    if len(row) > 3:
        existing_codes.add(row[3].strip())

existing_comment = user_rows[0][4] if user_rows and len(user_rows[0]) > 4 else ""

st.divider()

# ======================
# SÉLECTION INDISPONIBILITÉS
# ======================
selections = []

for jour, jour_code in JOURS.items():
    st.subheader(jour)
    for num, label in CRENEAUX.items():
        code_creneau = f"{jour_code}_{num}"
        key = f"{jour_code}_{num}"

        # précoché si existant pour l'utilisateur actuel
        checked = code_creneau in existing_codes

        if st.checkbox(label, value=checked, key=key):
            selections.append([
                user_code,
                jour,
                label,
                code_creneau,
                "",  # commentaire ajouté plus bas
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

st.divider()

# ======================
# COMMENTAIRE
# ======================
commentaire = st.text_area(
    "💬 Commentaire",
    value=existing_comment,
    height=100
)

# ======================
# ENREGISTREMENT
# ======================
rows_to_delete = [
    i for i, row in enumerate(all_data[1:], start=2)
    if row[0] == user_code
]

if rows_to_delete:
    st.warning(
        "⚠️ Vous avez déjà enregistré vos indisponibilités."
    )

    confirm = st.checkbox("Je confirme l’écrasement des anciennes données")

    if st.button("💾 Enregistrer / Écraser"):
        if not selections:
            st.warning("Aucun créneau sélectionné.")
            st.stop()

        # suppression du bas vers le haut
        for row_index in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(row_index)

        # ajout nouvelles lignes
        for row in selections:
            sheet.append_row([
                row[0],        # Code enseignant
                row[1],        # Jour
                row[2],        # Créneau
                row[3],        # Code créneau
                commentaire,   # Commentaire
                row[5]         # Timestamp
            ])
        st.success("✅ Indisponibilités mises à jour avec succès")

else:
    if st.button("💾 Enregistrer"):
        if not selections:
            st.warning("Aucun créneau sélectionné.")
            st.stop()

        # ajout nouvelles lignes
        for row in selections:
            sheet.append_row([
                row[0],
                row[1],
                row[2],
                row[3],
                commentaire,
                row[5]
            ])
        st.success("✅ Indisponibilités enregistrées avec succès")
