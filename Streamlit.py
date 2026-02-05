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
    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
user_rows = [r for r in all_data[1:] if r[0] == user_code]

# Accéder correctement à la colonne Commentaire
existing_comment = user_rows[0][6] if user_rows and len(user_rows[0]) > 6 else ""

# Charger les créneaux ponctuels existants pour cet enseignant
st.session_state.ponctuels = [
    {"semaine": r[1], "jour": r[2], "creneau": r[3]}
    for r in user_rows
    if len(r) > 5 and r[5].endswith("_P")
]

st.divider()

# ======================
# CRÉNEAUX PONCTUELS (FORMULAIRE)
# ======================
with st.form("ponctuel_form"):
    st.subheader("➕ Ajouter un créneau ponctuel")

    semaines = st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
    jours_sel = st.multiselect("Jour(s)", list(JOURS.keys()), key="jours_sel")
    creneaux_sel = st.multiselect("Créneau(x)", list(CRENEAUX.values()), key="creneaux_sel")

    ajouter = st.form_submit_button("➕ Ajouter")

    if ajouter:
        for s in semaines:
            for j in jours_sel:
                for c in creneaux_sel:
                    st.session_state.ponctuels.append({
                        "semaine": s,
                        "jour": j,
                        "creneau": c
                    })

# ======================
# TABLEAU DES CRÉNEAUX PONCTUELS
# ======================
if st.session_state.ponctuels:
    st.subheader("📝 Créneaux ponctuels ajoutés")

    h1, h2, h3, h4 = st.columns([1, 2, 2, 0.5])
    h1.markdown("**Semaine**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**🗑️**")

    to_delete = []

    for idx, row in enumerate(st.session_state.ponctuels):
        c1, c2, c3, c4 = st.columns([1, 2, 2, 0.5])
        c1.write(row["semaine"])
        c2.write(row["jour"])
        c3.write(row["creneau"])
        if c4.button("🗑️", key=f"del_{idx}"):
            to_delete.append(idx)

    for idx in sorted(to_delete, reverse=True):
        st.session_state.ponctuels.pop(idx)

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

    # Supprimer les anciennes lignes de cet enseignant
    rows_to_delete = [
        i for i, r in enumerate(all_data[1:], start=2)
        if r[0] == user_code
    ]
    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Enregistrer les créneaux ponctuels
    for p in st.session_state.ponctuels:
        j_code = JOURS[p["jour"]]
        num = [k for k, v in CRENEAUX.items() if v == p["creneau"]][0]
        code_cr = f"{j_code}_{num}"

        sheet.append_row([
            user_code,                            # A
            p["semaine"],                         # B
            p["jour"],                            # C
            p["creneau"],                         # D
            code_cr,                              # E
            f"{user_code}_{code_cr}_P",           # F
            commentaire,                          # G
            now                                   # H
        ])

    st.success("✅ Créneaux ponctuels enregistrés")
