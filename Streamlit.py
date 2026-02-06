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

# ✅ Vérification des accès
try:
    sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
    creneaux_sheet = client.open(NOM_SHEET).worksheet("Creneaux")
    jours_sheet = client.open(NOM_SHEET).worksheet("Jours")
except Exception as e:
    st.error(f"Impossible d'accéder à une des feuilles Google Sheet.\n{e}")
    st.stop()

# ======================
# LECTURE CRÉNEAUX DE LA FEUILLE GOOGLE
# ======================
creneaux_data = creneaux_sheet.get_all_values()[1:]  # skip header
CRENEAUX_LABELS = {r[0]: r[1] for r in creneaux_data if len(r) >= 2}  # label_affiche → code_num
CRENEAUX_GROUPES = {r[0]: r[2] for r in creneaux_data if len(r) >= 3}  # label_affiche → groupe

def get_creneaux_nums(selection):
    result = []
    for c in selection:
        if c not in CRENEAUX_LABELS:
            continue
        code_num = CRENEAUX_LABELS[c]
        groupe = CRENEAUX_GROUPES[c]
        if code_num.startswith("ALL_"):  # label général
            nums_du_groupe = [r[1] for r in creneaux_data if r[2] == groupe and not r[1].startswith("ALL_")]
            result.extend(nums_du_groupe)
        else:
            result.append(code_num)
    return result

# ======================
# LECTURE JOURS DE LA FEUILLE GOOGLE
# ======================
jours_data = jours_sheet.get_all_values()[1:]  # skip header
JOURS_LABELS = {r[0]: r[1] for r in jours_data if len(r) >= 2}  # label_affiche → code_num
JOURS_GROUPES = {r[0]: r[2] for r in jours_data if len(r) >= 3}  # label_affiche → groupe

def get_jours_codes(selection):
    result = []
    for label in selection:
        if label not in JOURS_LABELS:
            continue
        code_num = JOURS_LABELS[label]
        groupe = JOURS_GROUPES[label]
        if code_num.startswith("ALL_"):
            nums_du_groupe = [r[1] for r in jours_data if r[2] == groupe and not r[1].startswith("ALL_")]
            result.extend(nums_du_groupe)
        else:
            result.append(code_num)
    return result

# ======================
# SESSION STATE
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

for k in ["semaines_sel", "jours_sel", "creneaux_sel", "raison_sel"]:
    if k not in st.session_state:
        st.session_state[k] = "" if k == "raison_sel" else []

if "_warning_doublon" not in st.session_state:
    st.session_state._warning_doublon = False

if "commentaire" not in st.session_state:
    st.session_state.commentaire = ""

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
    st.session_state.raison_sel = ""
    st.session_state.commentaire = ""

# ======================
# LECTURE GOOGLE SHEET
# ======================
all_data = sheet.get_all_values()
user_rows = [r for r in all_data[1:] if r[0] == user_code]

codes_sheet = set()
commentaire_existant = ""
dernier_timestamp = None

for r in user_rows:
    if len(r) > 5 and r[5].endswith("_P"):
        codes_sheet.add(r[5])
        commentaire_existant = r[6] if len(r) > 6 else ""
    if len(r) > 8 and r[8]:
        if dernier_timestamp is None or r[8] > dernier_timestamp:
            dernier_timestamp = r[8]

# ======================
# MESSAGE SI CRÉNEAUX EXISTANTS
# ======================
if codes_sheet:
    msg = (
        "⚠️ Des indisponibilités sont déjà enregistrées pour vous.<br>"
        "Toute modification (ajout ou suppression) effacera les anciennes données lors de l'enregistrement.<br>"
    )
    if dernier_timestamp:
        msg += f"Dernière modification effectuée le : {dernier_timestamp}"
    st.markdown(msg, unsafe_allow_html=True)

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
                    "creneau": r[3],
                    "raison": r[6] if len(r) > 6 else ""
                })

st.divider()

# ======================
# FONCTION AJOUT AVEC RESET LISTES
# ======================
def ajouter_creneaux(codes_sheet, user_code):
    doublon = False

    semaines = st.session_state.semaines_sel
    jours_sel = st.session_state.jours_sel
    creneaux_sel = st.session_state.creneaux_sel
    raison_texte = st.session_state.raison_sel

    jours_codes = get_jours_codes(jours_sel)
    creneaux_nums = get_creneaux_nums(creneaux_sel)

    for s in semaines:
        for j_code in jours_codes:
            for num in creneaux_nums:
                code = f"{user_code}_{j_code}_{num}_P"

                existe_streamlit = any(
                    p["semaine"] == s and p["jour"] == j_code and p["creneau"] == num
                    for p in st.session_state.ponctuels
                )

                existe_sheet = code in codes_sheet

                if existe_streamlit or existe_sheet:
                    doublon = True
                else:
                    st.session_state.ponctuels.append({
                        "id": str(uuid.uuid4()),
                        "semaine": s,
                        "jour": j_code,
                        "creneau": num,
                        "raison": raison_texte
                    })

    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []
    st.session_state.raison_sel = ""
    st.session_state._warning_doublon = doublon

# ======================
# AJOUT (BOUTON)
# ======================
st.subheader("➕ Créneaux ponctuels")

st.multiselect("Semaine(s)", list(range(1, 53)), key="semaines_sel")
st.multiselect("Jour(s)", [r[0] for r in jours_data], key="jours_sel")
st.multiselect("Créneau(x)", [r[0] for r in creneaux_data], key="creneaux_sel")
st.text_area("Raisons/Commentaires", key="raison_sel", height=80, value=st.session_state.get("raison_sel", ""))

st.button("➕ Ajouter", on_click=ajouter_creneaux, args=(codes_sheet, user_code))

if st.session_state._warning_doublon:
    st.warning("⚠️ Certains créneaux existaient déjà et n'ont pas été ajoutés.")
    st.session_state._warning_doublon = False

st.divider()

# ======================
# TABLEAU + SUPPRESSION
# ======================
st.subheader("📝 Créneaux ajoutés")

if st.session_state.ponctuels:
    delete_id = None

    h1, h2, h3, h4, h5 = st.columns([1, 2, 2, 3, 0.5])
    h1.markdown("**Semaine**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**Raison/Commentaire**")
    h5.markdown("**🗑️**")

    for r in st.session_state.ponctuels:
        c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 3, 0.5])
        c1.write(r["semaine"] or "-")
        c2.write(r["jour"] or "-")
        c3.write(r["creneau"] or "-")
        c4.write(r.get("raison", "") or "-")

        if c5.button("🗑️", key=f"del_{r['id']}"):
            delete_id = r["id"]

    if delete_id:
        st.session_state.ponctuels = [
            r for r in st.session_state.ponctuels if r["id"] != delete_id
        ]
        st.rerun()
else:
    st.write("Aucune indisponibilité enregistrée.")

st.divider()

# ======================
# COMMENTAIRE GLOBAL
# ======================
commentaire = st.text_area(
    "💬 Commentaire global",
    value=st.session_state.get("commentaire", commentaire_existant if 'commentaire_existant' in locals() else ""),
    key="commentaire"
)

# ======================
# ENREGISTREMENT OPTIMISÉ AVEC append_rows
# ======================
if st.button("💾 Enregistrer"):
    # Supprimer toutes les anciennes indisponibilités pour cet utilisateur
    rows_to_delete = [i for i, r in enumerate(all_data[1:], start=2) if r[0] == user_code]
    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.session_state.ponctuels:
        rows_to_append = []
        for p in st.session_state.ponctuels:
            if p["jour"] and p["creneau"]:
                code_cr = f"{p['jour']}_{p['creneau']}"
                code_streamlit = f"{user_code}_{code_cr}_P"
                raison = p.get("raison", "")
            else:
                code_cr = ""
                code_streamlit = f"{user_code}_0_P"
                raison = "Aucune indisponibilité enregistrée."

            rows_to_append.append([
                user_code,
                p.get("semaine", ""),
                p.get("jour", ""),
                p.get("creneau", ""),
                code_cr,
                code_streamlit,
                raison,
                st.session_state.commentaire,
                now
            ])
        # ⚡ Envoi en batch
        sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    else:
        sheet.append_row([
            user_code, "", "", "", "", f"{user_code}_0_P",
            "Aucune indisponibilité enregistrée.",
            st.session_state.commentaire,
            now
        ], value_input_option="USER_ENTERED")

    st.success("✅ Indisponibilités enregistrées")
