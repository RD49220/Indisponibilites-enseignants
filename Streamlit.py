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
    "5": "14h-15h30",
    "6": "15h30-17h",
    "7": "17h-18h30"
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

try:
    sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
except gspread.exceptions.APIError:
    st.error("Impossible d'accéder à la feuille Google Sheets. Réessayez plus tard.")
    st.stop()

# ======================
# SESSION STATE
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# Clés pour multiselect
for key in ["semaines_sel", "jours_sel", "creneaux_sel"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# CHARGER UTILISATEURS
# ======================
try:
    users_data = users_sheet.get_all_values()[1:]
except gspread.exceptions.APIError:
    st.error("Impossible de lire les utilisateurs depuis Google Sheets.")
    st.stop()

users = [
    {"code": r[0], "nom": r[1], "prenom": r[2]}
    for r in users_data if len(r) >= 3
]

options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}

selected_label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[selected_label]

# ======================
# RESET SI CHANGEMENT UTILISATEUR
# ======================
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []
    st.session_state["semaines_sel"] = []
    st.session_state["jours_sel"] = []
    st.session_state["creneaux_sel"] = []

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
try:
    all_data = sheet.get_all_values()
except gspread.exceptions.APIError:
    st.error("Impossible de lire les créneaux depuis Google Sheets.")
    st.stop()

user_rows = [r for r in all_data[1:] if r[0] == user_code]
existing_comment = user_rows[0][6] if user_rows and len(user_rows[0]) > 6 else ""

# Charger les créneaux ponctuels existants
if not st.session_state.ponctuels:
    st.session_state.ponctuels = [
        {"semaine": r[1], "jour": r[2], "creneau": r[3]}
        for r in user_rows if len(r) > 5 and r[5].endswith("_P")
    ]

st.divider()

# ======================
# FORMULAIRE AJOUT
# ======================
st.subheader("➕ Ajouter un créneau ponctuel")
semaines_sel = st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
jours_sel = st.multiselect("Jour(s)", list(JOURS.keys()), key="jours_sel")
creneaux_sel = st.multiselect("Créneau(x)", list(CRENEAUX.values()), key="creneaux_sel")

if st.button("➕ Ajouter"):
    if not semaines_sel or not jours_sel or not creneaux_sel:
        st.warning("Veuillez sélectionner au moins une semaine, un jour et un créneau.")
    else:
        added = 0
        for s in semaines_sel:
            for j in jours_sel:
                for c in creneaux_sel:
                    if not any(p["semaine"] == s and p["jour"] == j and p["creneau"] == c
                               for p in st.session_state.ponctuels):
                        st.session_state.ponctuels.append({
                            "semaine": s,
                            "jour": j,
                            "creneau": c
                        })
                        added += 1
        if added > 0:
            st.success(f"{added} créneau(x) ajouté(s).")
        else:
            st.info("Tous les créneaux sélectionnés étaient déjà dans la liste.")

# ======================
# TABLEAU PONCTUELS
# ======================
if st.session_state.ponctuels:
    st.subheader("📝 Créneaux ponctuels ajoutés")
    for idx, row in enumerate(st.session_state.ponctuels):
        cols = st.columns([1, 2, 2, 0.5])
        cols[0].write(row["semaine"])
        cols[1].write(row["jour"])
        cols[2].write(row["creneau"])
        # Supprimer un créneau avec clé stable
        key_btn = f"{row['semaine']}_{row['jour']}_{row['creneau']}"
        if cols[3].button("🗑️", key=f"del_{key_btn}"):
            st.session_state.ponctuels.pop(idx)
            st.experimental_rerun()  # Rafraîchit immédiatement le tableau

st.divider()

# ======================
# COMMENTAIRE
# ======================
commentaire = st.text_area("💬 Commentaire", value=existing_comment)

# ======================
# ENREGISTREMENT
# ======================
if st.button("💾 Enregistrer"):
    if not st.session_state.ponctuels:
        st.warning("Aucun créneau ponctuel sélectionné.")
        st.stop()

    # Supprimer les anciennes lignes de l'utilisateur
    rows_to_delete = [i for i, r in enumerate(all_data[1:], start=2) if r[0] == user_code]
    for i in sorted(rows_to_delete, reverse=True):
        try:
            sheet.delete_rows(i)
        except gspread.exceptions.APIError:
            st.error("Erreur lors de la suppression des anciennes lignes.")
            st.stop()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ajouter chaque créneau ponctuel
    for p in st.session_state.ponctuels:
        j_code = JOURS[p["jour"]]
        num = [k for k, v in CRENEAUX.items() if v == p["creneau"]][0]
        code_cr = f"{j_code}_{num}"
        try:
            sheet.append_row([
                user_code,
                p["semaine"],
                p["jour"],
                p["creneau"],
                code_cr,
                f"{user_code}_{code_cr}_P",
                commentaire,
                now
            ])
        except gspread.exceptions.APIError:
            st.error("Erreur lors de l'enregistrement des créneaux.")
            st.stop()

    st.success("✅ Créneaux ponctuels enregistrés")
