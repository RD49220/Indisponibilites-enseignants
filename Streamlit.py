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

sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)

# ======================
# SESSION STATE
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# CHARGER UTILISATEURS
# ======================
users_data = users_sheet.get_all_values()[1:]
users = [
    {"code": r[0], "nom": r[1], "prenom": r[2]}
    for r in users_data if len(r) >= 3
]

options = {
    f"{u['code']} – {u['nom']} {u['prenom']}": u["code"]
    for u in users
}

selected_label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[selected_label]

# Reset si changement d’enseignant
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
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
semaines_sel = st.multiselect("Semaine(s)", list(range(1, 53)))
jours_sel = st.multiselect("Jour(s)", list(JOURS.keys()))
creneaux_sel = st.multiselect("Créneau(x)", list(CRENEAUX.values()))

if st.button("➕ Ajouter"):
    if not semaines_sel or not jours_sel or not creneaux_sel:
        st.warning("Veuillez sélectionner au moins une semaine, un jour et un créneau.")
    else:
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
        st.success("Créneaux ajoutés !")

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
        # Supprimer un créneau
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.ponctuels.pop(idx)
            break  # stoppe la boucle pour éviter conflits de clés

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
        sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ajouter chaque créneau ponctuel
    for p in st.session_state.ponctuels:
        j_code = JOURS[p["jour"]]
        num = [k for k, v in CRENEAUX.items() if v == p["creneau"]][0]
        code_cr = f"{j_code}_{num}"
        sheet.append_row([
            user_code,            # A
            p["semaine"],         # B
            p["jour"],            # C
            p["creneau"],         # D
            code_cr,              # E
            f"{user_code}_{code_cr}_P", # F
            commentaire,          # G
            now                   # H
        ])

    st.success("✅ Créneaux ponctuels enregistrés")
