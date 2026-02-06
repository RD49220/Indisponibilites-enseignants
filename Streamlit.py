import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ======================
# CONFIG
# ======================
st.set_page_config(page_title="Indisponibilités enseignants", layout="wide")

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
    1: "8h-9h30",
    2: "9h30-11h",
    3: "11h-12h30",
    5: "14h-15h30",
    6: "15h30-17h",
    7: "17h-18h30"
}

CRENEAUX_GROUPES = {
    "Matin": [1, 2, 3],
    "Après-midi": [5, 6, 7]
}

# ======================
# GOOGLE SHEETS AUTH (Streamlit Cloud OK)
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
defaults = {
    "ponctuels": [],
    "selected_user": None,
    "semaines_sel": [],
    "jours_sel": [],
    "creneaux_sel": [],
    "raison_sel": "",
    "commentaire_global": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# UTILISATEURS
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

# Reset si changement enseignant
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []
    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []
    st.session_state.raison_sel = ""
    st.session_state.commentaire_global = ""

# ======================
# DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
user_rows = [r for r in all_data[1:] if r and r[0] == user_code]

existing_codes = {r[5] for r in user_rows if len(r) > 5}

last_timestamp = user_rows[-1][8] if user_rows and len(user_rows[-1]) > 8 else None

if user_rows:
    st.warning(
        f"⚠️ Des indisponibilités sont déjà enregistrées pour vous.\n\n"
        f"Toute modification (ajout ou suppression) effacera les anciennes données lors de l'enregistrement.\n\n"
        f"Dernière modification effectuée le : {last_timestamp}"
    )

# Charger les créneaux existants
st.session_state.ponctuels = []
for r in user_rows:
    if len(r) > 5 and r[5].endswith("_P") and r[5] != f"{user_code}_0_P":
        st.session_state.ponctuels.append({
            "semaine": r[1],
            "jour": r[2],
            "creneau": r[3],
            "code": r[5],
            "raison": r[6] if len(r) > 6 else ""
        })

st.divider()

# ======================
# FORM CRÉNEAUX
# ======================
with st.form("ponctuel_form"):
    st.subheader("➕ Créneaux ponctuels")

    semaines = st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
    jours = st.multiselect("Jour(s)", list(JOURS.keys()), key="jours_sel")

    creneaux = st.multiselect(
        "Créneau(x)",
        list(CRENEAUX_GROUPES.keys()) + list(CRENEAUX.values()),
        key="creneaux_sel"
    )

    raison = st.text_area("Raisons / Commentaires", key="raison_sel", height=80)

    ajouter = st.form_submit_button("➕ Ajouter")

    if ajouter:
        added = False

        for s in semaines:
            for j in jours:
                j_code = JOURS[j]

                for c in creneaux:
                    nums = CRENEAUX_GROUPES.get(
                        c,
                        [k for k, v in CRENEAUX.items() if v == c]
                    )

                    for num in nums:
                        code = f"{user_code}_{j_code}_{num}_P"

                        if code in existing_codes:
                            continue
                        if any(p["code"] == code for p in st.session_state.ponctuels):
                            continue

                        st.session_state.ponctuels.append({
                            "semaine": s,
                            "jour": j,
                            "creneau": CRENEAUX[num],
                            "code": code,
                            "raison": raison
                        })
                        added = True

        if not added:
            st.warning("⚠️ Créneau déjà ajouté ou existant.")
        else:
            st.session_state.semaines_sel = []
            st.session_state.jours_sel = []
            st.session_state.creneaux_sel = []
            st.session_state.raison_sel = ""
            st.rerun()
            st.rerun()

# ======================
# TABLEAU RÉCAP
# ======================
if st.session_state.ponctuels:
    st.subheader("📝 Créneaux ajoutés")

    h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 2, 0.5])
    h1.markdown("**Semaine**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**Raison**")
    h5.markdown("**🗑️**")

    for idx, row in enumerate(st.session_state.ponctuels):
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 2, 0.5])
        c1.write(row["semaine"])
        c2.write(row["jour"])
        c3.write(row["creneau"])
        c4.write(row["raison"])

        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.ponctuels.pop(idx)
            st.rerun()
            st.rerun()

st.divider()

# ======================
# COMMENTAIRE GLOBAL
# ======================
st.text_area("💬 Commentaire global", key="commentaire_global")

# ======================
# ENREGISTREMENT
# ======================
if st.button("💾 Enregistrer"):
    rows_to_delete = [
        i for i, r in enumerate(all_data[1:], start=2)
        if r and r[0] == user_code
    ]

    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not st.session_state.ponctuels:
        sheet.append_row([
            user_code, "", "", "", "",
            f"{user_code}_0_P",
            "Aucune indisponibilité enregistrée",
            st.session_state.commentaire_global,
            now
        ])
    else:
        for p in st.session_state.ponctuels:
            sheet.append_row([
                user_code,
                p["semaine"],
                p["jour"],
                p["creneau"],
                "",
                p["code"],
                p["raison"],
                st.session_state.commentaire_global,
                now
            ])

    st.success("✅ Indisponibilités enregistrées")
    st.session_state.ponctuels = []
