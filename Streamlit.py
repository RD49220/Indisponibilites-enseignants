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

# ======================
# CACHE DES FEUILLES
# ======================
if "sheets_cache" not in st.session_state:
    st.session_state.sheets_cache = {}
    st.session_state.sheets_cache["main"] = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    st.session_state.sheets_cache["users"] = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
    st.session_state.sheets_cache["creneaux"] = client.open(NOM_SHEET).worksheet("Creneaux")
    st.session_state.sheets_cache["jours"] = client.open(NOM_SHEET).worksheet("Jours")
    st.session_state.sheets_cache["semaines"] = client.open(NOM_SHEET).worksheet("Semaines")

# Références aux feuilles
sheet = st.session_state.sheets_cache["main"]
users_sheet = st.session_state.sheets_cache["users"]
creneaux_sheet = st.session_state.sheets_cache["creneaux"]
jours_sheet = st.session_state.sheets_cache["jours"]
semaines_sheet = st.session_state.sheets_cache["semaines"]

# ======================
# CHARGEMENT DES DONNÉES
# ======================
creneaux_data = creneaux_sheet.get_all_values()[1:]
jours_data = jours_sheet.get_all_values()[1:]
semaines_data = semaines_sheet.get_all_values()[1:]
users_data = users_sheet.get_all_values()[1:]
all_data = sheet.get_all_values()

# ======================
# DICTIONNAIRES
# ======================
CRENEAUX_LABELS = {r[0]: r[1] for r in creneaux_data if len(r) >= 2}
CRENEAUX_GROUPES = {r[0]: r[2] for r in creneaux_data if len(r) >= 3}
JOURS_LABELS = {r[0]: r[1] for r in jours_data if len(r) >= 2}
JOURS_GROUPES = {r[0]: r[2] for r in jours_data if len(r) >= 3}
SEMAINES_LABELS = {r[0]: r[1] for r in semaines_data if len(r) >= 2}
SEMAINES_GROUPES = {r[0]: r[2] for r in semaines_data if len(r) >= 3}

CODE_TO_JOUR = {v: k for k, v in JOURS_LABELS.items()}
CODE_TO_CREN = {v: k for k, v in CRENEAUX_LABELS.items()}

# ======================
# SESSION STATE
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None
for k in ["semaines_sel", "jours_sel", "creneaux_sel", "raison_sel", "email_utilisateur"]:
    if k not in st.session_state:
        st.session_state[k] = "" if k in ["raison_sel","email_utilisateur"] else []
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
    st.session_state.email_utilisateur = ""  # <-- reset email aussi

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
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
# FONCTION AJOUT
# ======================
def ajouter_creneaux(codes_sheet, user_code):
    doublon = False
    semaines_sel = []
    for s in st.session_state.semaines_sel:
        if SEMAINES_LABELS[s].startswith("ALL_"):
            groupe = SEMAINES_GROUPES[s]
            semaines_sel.extend([r[1] for r in semaines_data if r[2] == groupe and not r[1].startswith("ALL_")])
        else:
            semaines_sel.append(SEMAINES_LABELS[s])
    jours_codes = []
    for j in st.session_state.jours_sel:
        if JOURS_LABELS[j].startswith("ALL_"):
            groupe = JOURS_GROUPES[j]
            jours_codes.extend([r[1] for r in jours_data if r[2] == groupe and not r[1].startswith("ALL_")])
        else:
            jours_codes.append(JOURS_LABELS[j])
    creneaux_nums = []
    for c in st.session_state.creneaux_sel:
        if CRENEAUX_LABELS[c].startswith("ALL_"):
            groupe = CRENEAUX_GROUPES[c]
            creneaux_nums.extend([r[1] for r in creneaux_data if r[2] == groupe and not r[1].startswith("ALL_")])
        else:
            creneaux_nums.append(CRENEAUX_LABELS[c])
    raison_texte = st.session_state.raison_sel

    for s in semaines_sel:
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
# AJOUT UI
# ======================
st.subheader("➕ Créneaux ponctuels")
st.multiselect("Semaine(s)", [r[0] for r in semaines_data], key="semaines_sel")
st.multiselect("Jour(s)", [r[0] for r in jours_data], key="jours_sel")
st.multiselect("Créneau(x)", [r[0] for r in creneaux_data], key="creneaux_sel")
st.text_area("Raisons/Commentaires", key="raison_sel", height=80, value=st.session_state.get("raison_sel", ""))

st.button("➕ Ajouter", on_click=ajouter_creneaux, args=(codes_sheet, user_code))
if st.session_state._warning_doublon:
    st.warning("⚠️ Certains créneaux existaient déjà et n'ont pas été ajoutés.")
    st.session_state._warning_doublon = False

# ======================
# TABLEAU CRÉNEAUX AJOUTÉS + SUPPRESSION
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
        c1, c2, c3, c4, c5 = st.columns([1,2,2,3,0.5])
        c1.write(r["semaine"] or "-")
        c2.write(CODE_TO_JOUR.get(r["jour"], r["jour"]))
        c3.write(CODE_TO_CREN.get(r["creneau"], r["creneau"]))
        c4.write(r.get("raison","") or "-")
        if c5.button("🗑️", key=f"del_{r['id']}"):
            delete_id = r["id"]
    if delete_id:
        st.session_state.ponctuels = [r for r in st.session_state.ponctuels if r["id"] != delete_id]
        st.experimental_rerun()
else:
    st.write("Aucune indisponibilité enregistrée.")

# ======================
# CHAMP E-MAIL OPTIONNEL
# ======================
st.subheader("✉️ Adresse e-mail (optionnel)")
st.text_input("Entrez votre adresse e-mail", key="email_utilisateur")

# ======================
# COMMENTAIRE GLOBAL
# ======================
commentaire = st.text_area(
    "💬 Commentaire global",
    value=st.session_state.get("commentaire", commentaire_existant if 'commentaire_existant' in locals() else ""),
    key="commentaire"
)

# ======================
# ENREGISTREMENT
# ======================
if st.button("💾 Enregistrer"):
    rows_to_delete = [i for i, r in enumerate(all_data[1:], start=2) if r[0] == user_code]
    for i in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(i)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if st.session_state.ponctuels:
        rows_to_append = []
        for p in st.session_state.ponctuels:
            code_cr = f"{p['jour']}_{p['creneau']}" if p["jour"] and p["creneau"] else ""
            code_streamlit = f"{user_code}_{code_cr}_P" if code_cr else f"{user_code}_0_P"
            raison = p.get("raison","") if code_cr else "Aucune indisponibilité enregistrée."
            rows_to_append.append([
                user_code,
                p.get("semaine", ""),
                CODE_TO_JOUR.get(p.get("jour",""), p.get("jour","")),
                CODE_TO_CREN.get(p.get("creneau",""), p.get("creneau","")),
                code_cr,
                code_streamlit,
                raison,
                st.session_state.commentaire,
                st.session_state.get("email_utilisateur",""),
                now
            ])
        sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    else:
        sheet.append_row([
            user_code, "", "", "", "", f"{user_code}_0_P",
            "Aucune indisponibilité enregistrée.",
            st.session_state.commentaire,
            st.session_state.get("email_utilisateur",""),
            now
        ], value_input_option="USER_ENTERED")
    st.success("✅ Indisponibilités enregistrées")
