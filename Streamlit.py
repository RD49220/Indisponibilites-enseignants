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

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
CRENEAUX = ["8h-9h30", "9h30-11h", "11h-12h30", "14h-15h30", "15h30-17h", "17h-18h30"]

# ======================
# AUTH GOOGLE SHEETS
# ======================
creds_dict = st.secrets["gcp_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

try:
    sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
except gspread.exceptions.APIError:
    st.error("Impossible d'accéder à la feuille Google Sheets.")
    st.stop()

# ======================
# SESSION STATE
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# Clés multiselect
for key in ["semaines_sel", "jours_sel", "creneaux_sel"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# UTILISATEURS
# ======================
try:
    users_data = users_sheet.get_all_values()[1:]
except gspread.exceptions.APIError:
    st.error("Impossible de lire les utilisateurs depuis Google Sheets.")
    st.stop()

users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in users_data if len(r) >= 3]
options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}

selected_label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[selected_label]

# RESET SI CHANGEMENT UTILISATEUR
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []
    st.session_state["semaines_sel"] = []
    st.session_state["jours_sel"] = []
    st.session_state["creneaux_sel"] = []

# ======================
# CHARGER CRÉNEAUX EXISTANTS
# ======================
try:
    all_data = sheet.get_all_values()
except gspread.exceptions.APIError:
    st.error("Impossible de lire les créneaux depuis Google Sheets.")
    st.stop()

user_rows = [r for r in all_data[1:] if r[0] == user_code]
existing_comment = user_rows[0][6] if user_rows and len(user_rows[0]) > 6 else ""

if not st.session_state.ponctuels:
    st.session_state.ponctuels = [
        {"Semaine": r[1], "Jour": r[2], "Créneau": r[3]} for r in user_rows if len(r) > 5 and r[5].endswith("_P")
    ]

st.divider()

# ======================
# FORMULAIRE AJOUT
# ======================
st.subheader("➕ Ajouter un créneau ponctuel")
semaines_sel = st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
jours_sel = st.multiselect("Jour(s)", JOURS, key="jours_sel")
creneaux_sel = st.multiselect("Créneau(x)", CRENEAUX, key="creneaux_sel")

if st.button("➕ Ajouter"):
    for s in semaines_sel:
        for j in jours_sel:
            for c in creneaux_sel:
                if not any(p["Semaine"] == s and p["Jour"] == j and p["Créneau"] == c for p in st.session_state.ponctuels):
                    st.session_state.ponctuels.append({"Semaine": s, "Jour": j, "Créneau": c})

# ======================
# TABLEAU LECTURE SEULE + SUPPRESSION
# ======================
if st.session_state.ponctuels:
    st.subheader("📝 Créneaux ponctuels ajoutés")
    for idx, row in enumerate(st.session_state.ponctuels):
        cols = st.columns([1, 2, 2, 0.5])
        cols[0].write(row["Semaine"])
        cols[1].write(row["Jour"])
        cols[2].write(row["Créneau"])
        if cols[3].button("🗑️", key=f"del_{row['Semaine']}_{row['Jour']}_{row['Créneau']}"):
            st.session_state.ponctuels.pop(idx)
            break  # On stoppe la boucle pour éviter conflit d’indices

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

    # Supprimer anciennes lignes de l'utilisateur
    rows_to_delete = [i for i, r in enumerate(all_data[1:], start=2) if r[0] == user_code]
    for i in sorted(rows_to_delete, reverse=True):
        try:
            sheet.delete_rows(i)
        except gspread.exceptions.APIError:
            st.error("Erreur lors de la suppression des anciennes lignes.")
            st.stop()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ajouter les créneaux ponctuels
    for p in st.session_state.ponctuels:
        j_code = p["Jour"][:3].upper()
        num = CRENEAUX.index(p["Créneau"]) + 1
        code_cr = f"{j_code}_{num}"
        try:
            sheet.append_row([
                user_code,
                p["Semaine"],
                p["Jour"],
                p["Créneau"],
                code_cr,
                f"{user_code}_{code_cr}_P",
                commentaire,
                now
            ])
        except gspread.exceptions.APIError:
            st.error("Erreur lors de l'enregistrement des créneaux.")
            st.stop()

    st.success("✅ Créneaux ponctuels enregistrés")
