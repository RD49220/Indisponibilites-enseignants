import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# ======================
# AJOUT EMAIL (BREVO)
# ======================
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail

configuration = Configuration()
configuration.api_key['api-key'] = st.secrets["BREVO_API_KEY"]

def envoyer_email(destinataire, sujet, contenu):
    try:
        api_instance = TransactionalEmailsApi(ApiClient(configuration))
        send_smtp_email = SendSmtpEmail(
            to=[{"email": destinataire}],
            sender={"email": st.secrets["EMAIL_FROM"], "name": "Planning GEII"},
            subject=sujet,
            text_content=contenu
        )
        api_instance.send_transac_email(send_smtp_email)
        return True, ""
    except Exception as e:
        return False, str(e)

# ======================
# CONFIG
# ======================
NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"
ADMIN_PASSWORD = st.secrets.get("admin_password", "monmotdepasse")  # 🔑 mot de passe admin

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
        st.session_state.config_sheet = client.open(NOM_SHEET).worksheet("Config")
except Exception as e:
    st.error(f"Impossible d'accéder à une des feuilles Google Sheet.\n{e}")
    st.stop()

# ======================
# LECTURE CONFIG AU DEMARRAGE
# ======================
if "semestre_filter" not in st.session_state:
    try:
        config_rows = st.session_state.config_sheet.get_all_values()
        if len(config_rows) > 1 and config_rows[1]:
            st.session_state.semestre_filter = config_rows[1][0]
        else:
            st.session_state.semestre_filter = "Toutes"
    except:
        st.session_state.semestre_filter = "Toutes"

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
# FONCTION CONTENU EMAIL
# ======================
def generer_contenu_email(user_code, ponc, commentaire, timestamp):
    lignes = [
        f"Bonjour {user_code},",
        f"Voici le récapitulatif de vos indisponibilités enregistré le {timestamp}.",
        ""
    ]
    if ponc:
        for p in ponc:
            lignes.append(
                f"- Semaine {p.get('semaine','')} | "
                f"Jour {CODE_TO_JOUR.get(p.get('jour',''), p.get('jour',''))} | "
                f"Créneau {CODE_TO_CREN.get(p.get('creneau',''), p.get('creneau',''))} | "
                f"Raison : {p.get('raison','-')}"
            )
    else:
        lignes.append("Aucune indisponibilité enregistrée.")
    lignes.append("")
    lignes.append(f"Commentaire global : {commentaire or '-'}")
    lignes.append("")
    lignes.append("Service Planning GEII")
    return "\n".join(lignes)

# ======================
# SESSION STATE INIT
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []
if "selected_user" not in st.session_state:
    st.session_state.selected_user = ""
if "semaines_sel" not in st.session_state:
    st.session_state.semaines_sel = []
if "jours_sel" not in st.session_state:
    st.session_state.jours_sel = []
if "creneaux_sel" not in st.session_state:
    st.session_state.creneaux_sel = []
if "raison_sel" not in st.session_state:
    st.session_state.raison_sel = ""
if "commentaire" not in st.session_state:
    st.session_state.commentaire = ""
if "_warning_doublon" not in st.session_state:
    st.session_state._warning_doublon = False
if "semestre_filter" not in st.session_state:
    st.session_state.semestre_filter = "Toutes"
# AJOUT
if "email_utilisateur" not in st.session_state:
    st.session_state.email_utilisateur = ""

# ======================
# MODE UTILISATEUR / ADMIN
# ======================
mode = st.radio("Mode", ["Utilisateur", "Administrateur"])

# ======================
# MODE ADMIN (IDENTIQUE)
# ======================
if mode == "Administrateur":
    pwd_input = st.text_input("Entrez le mot de passe administrateur :", type="password")
    if pwd_input != ADMIN_PASSWORD:
        st.error("❌ Mot de passe incorrect. Accès refusé.")
        st.stop()

    st.success("✅ Mode Administrateur activé.")

    semestre_choice = st.selectbox(
        "Afficher les semaines :",
        ["Toutes", "Pairs", "Impairs"],
        index=["Toutes","Pairs","Impairs"].index(st.session_state.semestre_filter)
    )
    st.session_state.semestre_filter = semestre_choice
    st.write(f"Semestres configurés : {st.session_state.semestre_filter}")

    try:
        rows = st.session_state.config_sheet.get_all_values()
        if len(rows) < 2:
            st.session_state.config_sheet.append_row([st.session_state.semestre_filter])
        else:
            st.session_state.config_sheet.update("A2", [[st.session_state.semestre_filter]])
    except Exception as e:
        st.warning(f"⚠️ Impossible de sauvegarder le filtre dans Config.\n{e}")

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

    if st.session_state.semestre_filter == "Impairs":
        st.info("Choix pour le semestre Impairs. (La période correspond au S1)")
    elif st.session_state.semestre_filter == "Pairs":
        st.info("Choix pour le semestre Pair. (La période correspond au S6)")
    else:
        st.info("Choix pour tous les semestres.")

    all_semaines = st.session_state.semaines_data
    if st.session_state.semestre_filter == "Pairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SP"]
    elif st.session_state.semestre_filter == "Impairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SI"]
    else:
        filtered_semaines = all_semaines

    users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
    options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
    label = st.selectbox("Choisissez votre nom", options.keys())
    user_code = options[label]

    # AJOUT EMAIL
    st.text_input("📧 Adresse mail pour recevoir le récapitulatif", key="email_utilisateur")

    # --- TOUT LE RESTE EST STRICTEMENT TON SCRIPT ---
