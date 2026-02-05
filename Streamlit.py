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

# reset si changement d’enseignant
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
user_rows = [r for r in all_data[1:] if r[0] == user_code]

existing_codes = {r[6] for r in user_rows if len(r) > 6}
existing_comment = user_rows[0][4] if user_rows else ""

st.divider()

# ======================
# CRÉNEAUX RÉGULIERS
# ======================
selections = []

for jour, j_code in JOURS.items():
    st.subheader(jour)
    cols = st.columns(3)
    i = 0

    for num, label in CRENEAUX.items():
        code_streamlit = f"{user_code}_{j_code}_{num}"
        checked = code_streamlit in existing_codes

        if cols[i % 3].checkbox(label, value=checked, key=code_streamlit):
            selections.append({
                "jour": jour,
                "creneau": label,
                "code_cr": f"{j_code}_{num}",
                "code_streamlit": code_streamlit,
                "semaine": ""
            })
        i += 1

st.divider()

# ======================
# CRÉNEAUX PONCTUELS (FORM)
# ======================
with st.form("ponctuel_form"):
    st.subheader("➕ Créneaux ponctuels")

    semaines = st.multiselect(
        "Semaine(s)",
        list(range(1, 53))
    )

    jours_sel = st.multiselect(
        "Jour(s)",
        list(JOURS.keys())
    )

    creneaux_sel = st.multiselect(
        "Créneau(x)",
        list(CRENEAUX.values())
    )

    ajouter = st.form_submit_button("➕ Ajouter")

    if ajouter:
        for s in semaines:
            for j in jours_sel:
                for c in creneaux_sel:
                    st.session_state.ponctuels.append({
                        "Semaine": s,
                        "Jour": j,
                        "Créneau": c
                    })

# ======================
# TABLEAU PONCTUELS COMPACT 🗑️
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
        c1.write(row["Semaine"])
        c2.write(row["Jour"])
        c3.write(row["Créneau"])
        if c4.button("🗑️", key=f"del_{idx}"):
            to_delete.append(idx)

    if to_delete:
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
    if not selections and not st.session_state.ponctuels:
        st.warning("Aucune indisponibilité sélectionnée.")
        st.stop()

    rows_to_delete = [
        i for i, r in enumerate(all_data[1:], start=2)
        if r[0] == user_code
    ]

    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)

    # réguliers
    for s in selections:
        sheet.append_row([
            user_code,
            s["jour"],
            s["creneau"],
            s["code_cr"],
            commentaire,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            s["code_streamlit"]
        ])

    # ponctuels
    for p in st.session_state.ponctuels:
        sheet.append_row([
            user_code,
            p["Jour"],
            p["Créneau"],
            "PONCTUEL",
            commentaire,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{user_code}_{p['Jour']}_{p['Créneau']}",
            p["Semaine"]
        ])

    st.success("✅ Indisponibilités enregistrées")
