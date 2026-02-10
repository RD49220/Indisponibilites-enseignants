import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# ======================
# BREVO SDK (AJOUT)
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
ADMIN_PASSWORD = st.secrets.get("admin_password", "monmotdepasse")

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
# LECTURE CONFIG
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
# CHARGEMENT DONNÉES
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
# UTILS
# ======================
def generer_contenu_email_html(user_code, ponc, commentaire_global, timestamp):
    lines = [
        f"Bonjour {user_code},",
        f"Voici le récapitulatif de vos indisponibilités enregistré le {timestamp} :",
        "",
    ]
    if ponc:
        for p in ponc:
            semaine = p.get("semaine","")
            jour = CODE_TO_JOUR.get(p.get("jour",""), p.get("jour",""))
            creneau = CODE_TO_CREN.get(p.get("creneau",""), p.get("creneau",""))
            raison = p.get("raison","-")
            lines.append(f"- Semaine {semaine} | Jour {jour} | Créneau {creneau} | Commentaire : {raison}")
    else:
        lines.append("Aucune indisponibilité enregistrée.")

    lines.append("")
    lines.append(f"Commentaire global : {commentaire_global or '-'}")
    lines.append("")
    lines.append("Cordialement,")
    lines.append("Service Planning GEII")
    return "\n".join(lines)

# ======================
# SESSION INIT
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []
if "selected_user" not in st.session_state:
    st.session_state.selected_user = ""
if "email_utilisateur" not in st.session_state:
    st.session_state.email_utilisateur = ""

# ======================
# MODE
# ======================
mode = st.radio("Mode", ["Utilisateur", "Administrateur"])

# ======================
# ADMIN
# ======================
if mode == "Administrateur":
    pwd_input = st.text_input("Entrez le mot de passe administrateur :", type="password")
    if pwd_input != ADMIN_PASSWORD:
        st.error("❌ Mot de passe incorrect. Accès refusé.")
        st.stop()

    st.success("✅ Mode Administrateur activé.")

    if st.button("❌ Supprimer toutes les lignes de la Feuille 1 (à partir de la ligne 2)"):
        n_rows = len(st.session_state.sheet.get_all_values())
        if n_rows > 1:
            st.session_state.sheet.delete_rows(2, n_rows)
            st.success("✅ Toutes les lignes supprimées.")
        else:
            st.info("La feuille est déjà vide.")
    st.stop()

# ======================
# UTILISATEUR
# ======================
st.title("📅 Indisponibilités enseignants")

users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[label]

# ======================
# RELOAD COMME SCRIPT 1
# ======================
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code

    user_rows = [r for r in st.session_state.sheet.get_all_values()[1:] if r[0] == user_code]
    st.session_state.ponctuels = []
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
    st.rerun()

# ======================
# WARNING EXISTANT (SCRIPT 1)
# ======================
user_rows = [r for r in st.session_state.sheet.get_all_values()[1:] if r[0] == user_code]
codes_sheet = set()
dernier_timestamp = None

for r in user_rows:
    if len(r) > 5 and r[5].endswith("_P"):
        codes_sheet.add(r[5])
    if len(r) > 8 and r[8]:
        if dernier_timestamp is None or r[8] > dernier_timestamp:
            dernier_timestamp = r[8]

if codes_sheet:
    msg = (
        "⚠️ Des indisponibilités sont déjà enregistrées pour vous.\n"
        "Toute modification effacera les anciennes données lors de l'enregistrement.\n"
    )
    if dernier_timestamp:
        msg += f"Dernière modification effectuée le : {dernier_timestamp}"
    st.warning(msg)

# ======================
# EMAIL (AJOUT)
# ======================
st.text_input("Votre adresse email pour recevoir le récapitulatif :", key="email_utilisateur")

# ======================
# ENREGISTREMENT (SCRIPT 1 + MAIL)
# ======================
if st.button("💾 Enregistrer"):
    rows_to_delete = [i for i, r in enumerate(st.session_state.all_data[1:], start=2) if r[0] == user_code]
    for i in sorted(rows_to_delete, reverse=True):
        st.session_state.sheet.delete_rows(i)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.session_state.ponctuels:
        rows_to_append = []
        for p in st.session_state.ponctuels:
            code_cr = f"{p['jour']}_{p['creneau']}"
            code_streamlit = f"{user_code}_{code_cr}_P"
            rows_to_append.append([
                user_code,
                p.get("semaine", ""),
                CODE_TO_CREN.get(p.get("creneau", ""), p.get("creneau", "")),
                CODE_TO_JOUR.get(p.get("jour", ""), p.get("jour", "")),
                code_cr,
                code_streamlit,
                p.get("raison", ""),
                st.session_state.commentaire,
                now
            ])
        st.session_state.sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    else:
        st.session_state.sheet.append_row([
            user_code, "", "", "", "", f"{user_code}_AAA_0_P",
            "Aucune indisponibilité enregistrée.",
            st.session_state.commentaire,
            now
        ], value_input_option="USER_ENTERED")

    st.success("✅ Indisponibilités enregistrées")

    # ======================
    # ENVOI EMAIL
    # ======================
    destinataire = st.session_state.email_utilisateur
    if destinataire:
        sujet = f"Récapitulatif des indisponibilités - {now}"
        contenu = generer_contenu_email_html(
            user_code,
            st.session_state.ponctuels,
            st.session_state.commentaire,
            now
        )
        success, msg = envoyer_email(destinataire, sujet, contenu)
        if success:
            st.success(f"✅ Email envoyé à {destinataire}")
        else:
            st.error(f"❌ Erreur envoi mail : {msg}")
    else:
        st.warning("⚠️ Vous n'avez pas renseigné d'adresse mail.")
