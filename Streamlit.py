import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Indisponibilités enseignants", layout="wide")

NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"
ONGLET_CRENEAUX = "Creneaux"

JOURS = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN"
}

# ================= GOOGLE AUTH =================
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
creneaux_sheet = client.open(NOM_SHEET).worksheet(ONGLET_CRENEAUX)

# ================= LOAD CRENEAUX =================
creneaux_data = creneaux_sheet.get_all_records()

labels_creaneaux = [r["label_affiche"] for r in creneaux_data]

def resolve_creneaux(label):
    """Retourne la liste des numéros de créneaux à enregistrer"""
    row = next(r for r in creneaux_data if r["label_affiche"] == label)

    if row["code_num"] == "ALL_M":
        return [int(r["code_num"]) for r in creneaux_data if r["groupe"] == "MA" and r["code_num"].isdigit()]

    if row["code_num"] == "ALL_A":
        return [int(r["code_num"]) for r in creneaux_data if r["groupe"] == "AP" and r["code_num"].isdigit()]

    return [int(row["code_num"])]

# ================= SESSION =================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

# ================= UI =================
st.title("📅 Indisponibilités enseignants")

# ================= USERS =================
users = users_sheet.get_all_records()
options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}

label_user = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[label_user]

if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []

# ================= FORM =================
with st.form("ajout"):
    col1, col2, col3 = st.columns(3)

    with col1:
        semaine = st.selectbox("Semaine", list(range(1, 53)))
    with col2:
        jour = st.selectbox("Jour", list(JOURS.keys()))
    with col3:
        label_creneau = st.selectbox("Créneau", labels_creaneaux)

    raison = st.text_area("Raisons / commentaires", height=80)
    submit = st.form_submit_button("➕ Ajouter")

    if submit:
        nums = resolve_creneaux(label_creneau)
        j_code = JOURS[jour]

        for num in nums:
            code = f"{user_code}_{j_code}_{num}_P"

            if any(p["code"] == code for p in st.session_state.ponctuels):
                continue

            st.session_state.ponctuels.append({
                "semaine": semaine,
                "jour": jour,
                "num": num,
                "code": code,
                "raison": raison
            })

# ================= TABLE =================
if st.session_state.ponctuels:
    st.subheader("📝 Récapitulatif")

    h1, h2, h3, h4, h5 = st.columns([1, 2, 1, 2, 0.5])
    h1.markdown("**Sem**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**Raison**")
    h5.markdown("**🗑️**")

    for i, r in enumerate(st.session_state.ponctuels):
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1, 2, 0.5])
        c1.write(r["semaine"])
        c2.write(r["jour"])
        c3.write(r["num"])
        c4.write(r["raison"])

        if c5.button("🗑️", key=f"del_{i}"):
            st.session_state.ponctuels.pop(i)
            st.rerun()

# ================= SAVE =================
commentaire_global = st.text_area("💬 Commentaire global")

if st.button("💾 Enregistrer"):
    all_data = sheet.get_all_values()
    for i in range(len(all_data) - 1, 0, -1):
        if all_data[i][0] == user_code:
            sheet.delete_rows(i + 1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not st.session_state.ponctuels:
        sheet.append_row([
            user_code, "", "", "", "",
            f"{user_code}_0_P",
            "Aucune indisponibilité enregistrée",
            commentaire_global,
            now
        ])
    else:
        for r in st.session_state.ponctuels:
            sheet.append_row([
                user_code,
                r["semaine"],
                r["jour"],
                r["num"],
                "",
                r["code"],
                r["raison"],
                commentaire_global,
                now
            ])

    st.success("✅ Enregistrement effectué")
    st.session_state.ponctuels = []
