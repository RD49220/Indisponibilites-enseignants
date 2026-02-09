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
ONGLET_CONFIG = "Config"  # nouvelle feuille pour persistance
ADMIN_PASSWORD = st.secrets.get("admin_password", "monmotdepasse")  # 🔑 mot de passe admin

# ======================
# DEBUG SECRET
# ======================
if "admin_password" in st.secrets:
    st.success("✅ Secret admin_password détecté")
else:
    st.error("❌ Secret admin_password INTROUVABLE")

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
# CHARGEMENT DES FEUILLES
# ======================
try:
    if "sheet" not in st.session_state:
        st.session_state.sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
    if "users_sheet" not in st.session_state:
        st.session_state.users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)
    if "creneaux_sheet" not in st.session_state:
        st.session_state.creneaux_sheet = client.open(NOM_SHEET).worksheet("Creneaux")
    if "jours_sheet" not in st.session_state:
        st.session_state.jours_sheet = client.open(NOM_SHEET).worksheet("Jours")
    if "semaines_sheet" not in st.session_state:
        st.session_state.semaines_sheet = client.open(NOM_SHEET).worksheet("Semaines")
    if "config_sheet" not in st.session_state:
        # Nouvelle feuille Config pour stocker filtre admin
        st.session_state.config_sheet = client.open(NOM_SHEET).worksheet(ONGLET_CONFIG)
except Exception as e:
    st.error(f"Impossible d'accéder à une des feuilles Google Sheet.\n{e}")
    st.stop()

# ======================
# CHARGEMENT DES DONNÉES EN SESSION
# ======================
if "creneaux_data" not in st.session_state:
    st.session_state.creneaux_data = st.session_state.creneaux_sheet.get_all_values()[1:]
if "jours_data" not in st.session_state:
    st.session_state.jours_data = st.session_state.jours_sheet.get_all_values()[1:]
if "semaines_data" not in st.session_state:
    st.session_state.semaines_data = st.session_state.semaines_sheet.get_all_values()[1:]
if "users_data" not in st.session_state:
    st.session_state.users_data = st.session_state.users_sheet.get_all_values()[1:]
if "all_data" not in st.session_state:
    st.session_state.all_data = st.session_state.sheet.get_all_values()

# ======================
# DICTIONNAIRES
# ======================
CRENEAUX_LABELS = {r[0]: r[1] for r in st.session_state.creneaux_data if len(r) >= 2}
CRENEAUX_GROUPES = {r[0]: r[2] for r in st.session_state.creneaux_data if len(r) >= 3}

JOURS_LABELS = {r[0]: r[1] for r in st.session_state.jours_data if len(r) >= 2}
JOURS_GROUPES = {r[0]: r[2] for r in st.session_state.jours_data if len(r) >= 3}

SEMAINES_LABELS = {r[0]: r[1] for r in st.session_state.semaines_data if len(r) >= 2}
SEMAINES_GROUPES = {r[0]: r[2] for r in st.session_state.semaines_data if len(r) >= 3}

CODE_TO_JOUR = {v: k for k, v in JOURS_LABELS.items()}
CODE_TO_CREN = {v: k for k, v in CRENEAUX_LABELS.items()}

# ======================
# FONCTIONS UTILITAIRES
# ======================
def get_creneaux_nums(selection):
    result = []
    for c in selection:
        if c not in CRENEAUX_LABELS:
            continue
        code_num = CRENEAUX_LABELS[c]
        groupe = CRENEAUX_GROUPES[c]
        if code_num.startswith("ALL_"):
            nums_du_groupe = [r[1] for r in st.session_state.creneaux_data if r[2] == groupe and not r[1].startswith("ALL_")]
            result.extend(nums_du_groupe)
        else:
            result.append(code_num)
    return result

def get_jours_codes(selection):
    result = []
    for label in selection:
        if label not in JOURS_LABELS:
            continue
        code_num = JOURS_LABELS[label]
        groupe = JOURS_GROUPES[label]
        if code_num.startswith("ALL_"):
            nums_du_groupe = [r[1] for r in st.session_state.jours_data if r[2] == groupe and not r[1].startswith("ALL_")]
            result.extend(nums_du_groupe)
        else:
            result.append(code_num)
    return result

def get_semaines_nums(selection):
    result = []
    for label in selection:
        if label not in SEMAINES_LABELS:
            continue
        code_num = SEMAINES_LABELS[label]
        groupe = SEMAINES_GROUPES[label]
        if code_num.startswith("ALL_"):
            nums_du_groupe = [r[1] for r in st.session_state.semaines_data if r[2] == groupe and not r[1].startswith("ALL_")]
            result.extend(nums_du_groupe)
        else:
            result.append(code_num)
    return result

# ======================
# SESSION STATE INIT
# ======================
for k in ["ponctuels", "selected_user", "semaines_sel", "jours_sel", "creneaux_sel", "raison_sel", "_warning_doublon", "commentaire"]:
    if k not in st.session_state:
        st.session_state[k] = [] if k.endswith("_sel") or k == "ponctuels" else "" if k != "_warning_doublon" else False

# Lecture du filtre depuis Config Sheet si existant
if "semestre_filter" not in st.session_state:
    try:
        config_rows = st.session_state.config_sheet.get_all_values()
        filtre = [r[1] for r in config_rows if r[0] == "semestre_filter"]
        st.session_state.semestre_filter = filtre[0] if filtre else "Toutes"
    except:
        st.session_state.semestre_filter = "Toutes"

# ======================
# MODE UTILISATEUR / ADMIN
# ======================
mode = st.radio("Mode", ["Utilisateur", "Administrateur"])

# ======================
# MODE ADMIN
# ======================
if mode == "Administrateur":
    pwd_input = st.text_input("Entrez le mot de passe administrateur :", type="password")
    if pwd_input != ADMIN_PASSWORD:
        st.error("❌ Mot de passe incorrect. Accès refusé.")
        st.stop()

    st.success("✅ Mode Administrateur activé.")

    # Choix semestre pair/impair (stocké globalement)
    semestre_choice = st.selectbox(
        "Afficher les semaines :",
        ["Toutes", "Pairs", "Impairs"],
        index=["Toutes","Pairs","Impairs"].index(st.session_state.semestre_filter)
    )
    if semestre_choice != st.session_state.semestre_filter:
        st.session_state.semestre_filter = semestre_choice
        # Sauvegarde dans Config Sheet
        rows = st.session_state.config_sheet.get_all_values()
        # Si clé existe, update
        found = False
        for idx, r in enumerate(rows, start=1):
            if r[0] == "semestre_filter":
                st.session_state.config_sheet.update_cell(idx, 2, semestre_choice)
                found = True
                break
        if not found:
            st.session_state.config_sheet.append_row(["semestre_filter", semestre_choice])

    st.write(f"Semestres configurés : {st.session_state.semestre_filter}")

    # Suppression globale
    if st.button("❌ Supprimer toutes les lignes de la Feuille 1 (à partir de la ligne 2)"):
        n_rows = len(st.session_state.all_data)
        if n_rows > 1:
            st.session_state.sheet.delete_rows(2, n_rows)
            st.success("✅ Toutes les lignes à partir de la ligne 2 ont été supprimées !")
        else:
            st.info("La feuille est déjà vide après la ligne 1.")

# ======================
# MODE UTILISATEUR
# ======================
else:
    st.title("📅 Indisponibilités enseignants")

    # Filtrage des semaines selon groupe choisi par admin
    all_semaines = st.session_state.semaines_data
    if st.session_state.semestre_filter == "Pairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SP"]
    elif st.session_state.semestre_filter == "Impairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SI"]
    else:
        filtered_semaines = all_semaines

    # … (reste de ton code utilisateur inchangé)
    # Ici tu continues avec la sélection utilisateur, ajout, tableau et enregistrement
