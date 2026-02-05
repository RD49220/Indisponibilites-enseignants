import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

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
# AUTH GOOGLE
# ======================
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
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

for k in ["semaines_sel", "jours_sel", "creneaux_sel"]:
    if k not in st.session_state:
        st.session_state[k] = []

# ======================
# UI
# ======================
st.title("📅 Indisponibilités enseignants")

# ======================
# UTILISATEURS
# ======================
users_data = users_sheet.get_all_values()[1:]
users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in users_data if len(r) >= 3]

options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[label]

# ======================
# RESET SI CHANGEMENT ENSEIGNANT
# ======================
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []
    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []

# ======================
# LECTURE GOOGLE SHEET
# ======================
all_data = sheet.get_all_values()
user_rows = [r for r in all_data[1:] if r[0] == user_code]

codes_sheet = set()
commentaire_existant = ""

for r in user_rows:
    if len(r) > 5 and r[5].endswith("_P"):
        codes_sheet.add(r[5])
        commentaire_existant = r[6] if len(r) > 6 else ""

# ======================
# CHARGEMENT STREAMLIT (DEDUP)
# ======================
if not st.session_state.ponctuels:
    deja_vus = set()

    for r in user_rows:
        if len(r) > 5 and r[5].endswith("_P"):
            key = (r[1], r[2], r[3])
            if key not in deja_vus:
                deja_vus.add(key)
                st.session_state.ponctuels.append({
                    "id": str(uuid.uuid4()),
                    "semaine": r[1],
                    "jour": r[2],
                    "creneau": r[3]
                })

st.divider()

# ======================
# AJOUT (COMPARAISON STREAMLIT + SHEET)
# ======================
st.subheader("➕ Créneaux ponctuels")

semaines = st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
jours_sel = st.multiselect("Jour(s)", list(JOURS.keys()), key="jours_sel")
creneaux_sel = st.multiselect("Créneau(x)", list(CRENEAUX.values()), key="creneaux_sel")

if st.button("➕ Ajouter"):
    doublon = False

    for s in semaines:
        for j in jours_sel:
            for c in creneaux_sel:
                jour_code = JOURS[j]
                num = [k for k, v in CRENEAUX.items() if v == c][0]
                code = f"{user_code}_{jour_code}_{num}_P"

                existe_streamlit = any(
                    p["semaine"] == s and p["jour"] == j and p["creneau"] == c
                    for p in st.session_state.ponctuels
                )

                existe_sheet = code in codes_sheet

                if existe_streamlit or existe_sheet:
                    doublon = True
                else:
                    st.session_state.ponctuels.append({
                        "id": str(uuid.uuid4()),
                        "semaine": s,
                        "jour": j,
                        "creneau": c
                    })

    if doublon:
        st.warning("⚠️ Certains créneaux existaient déjà (tableau ou Google Sheet) et n'ont pas été ajoutés.")

st.divider()

# ======================
# TABLEAU + SUPPRESSION
# ======================
if st.session_state.ponctuels:
    st.subheader("📝 Créneaux ajoutés")

    delete_id = None

    h1, h2, h3, h4 = st.columns([1, 2, 2, 0.5])
    h1.markdown("**Semaine**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**🗑️**")

    for r in st.session_state.ponctuels:
        c1, c2, c3, c4 = st.columns([1, 2, 2, 0.5])
        c1.write(r["semaine"])
        c2.write(r["jour"])
        c3.write(r["creneau"])

        if c4.button("🗑️", key=f"del_{r['id']}"):
            delete_id = r["id"]

    if delete_id:
        st.session_state.ponctuels = [
            r for r in st.session_state.ponctuels if r["id"] != delete_id
        ]
        st.rerun()

st.divider()

# ======================
# COMMENTAIRE
# ======================
commentaire = st.text_area("💬 Commentaire", value=commentaire_existant)

# ======================
# ENREGISTREMENT
# ======================
if st.button("💾 Enregistrer"):
    rows_to_delete = [
        i for i, r in enumerate(all_data[1:], start=2)
        if r[0] == user_code
    ]

    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for p in st.session_state.ponctuels:
        j_code = JOURS[p["jour"]]
        num = [k for k, v in CRENEAUX.items() if v == p["creneau"]][0]
        code_cr = f"{j_code}_{num}"

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

    st.success("✅ Indisponibilités enregistrées")
