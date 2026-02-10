import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# === AJOUT MAIL ===
import smtplib
from email.message import EmailMessage
# ===================
st.write(st.secrets["EMAIL_FROM"])


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
# === AJOUT MAIL ===
# Fonction envoi
# ======================
def envoyer_mail(destinataire, sujet, contenu):
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = st.secrets["EMAIL_FROM"]
    msg["To"] = destinataire
    msg.set_content(contenu)

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.starttls()
        server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
        server.send_message(msg)
# ======================

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
# SESSION STATE INIT
# ======================
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []
if "selected_user" not in st.session_state:
    st.session_state.selected_user = ""
if "commentaire" not in st.session_state:
    st.session_state.commentaire = ""

# ======================
# MODE
# ======================
mode = st.radio("Mode", ["Utilisateur", "Administrateur"])

# ======================
# MODE UTILISATEUR
# ======================
if mode == "Utilisateur":
    st.title("📅 Indisponibilités enseignants")

    users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
    options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
    label = st.selectbox("Choisissez votre nom", options.keys())
    user_code = options[label]

    # === AJOUT MAIL ===
    user_email = st.text_input("📧 Votre adresse email pour recevoir le récapitulatif")
    # ===================

    # ======================
    # Enregistrement
    # ======================
    if st.button("💾 Enregistrer"):
        rows_to_delete = [i for i, r in enumerate(st.session_state.all_data[1:], start=2) if r[0] == user_code]
        for i in sorted(rows_to_delete, reverse=True):
            st.session_state.sheet.delete_rows(i)

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
                    code_streamlit = f"{user_code}_AAA_0_P"
                    raison = "Aucune indisponibilité enregistrée."
                rows_to_append.append([
                    user_code,
                    p.get("semaine", ""),
                    CODE_TO_CREN.get(p.get("creneau", ""), p.get("creneau", "")),
                    CODE_TO_JOUR.get(p.get("jour", ""), p.get("jour", "")),
                    code_cr,
                    code_streamlit,
                    raison,
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
        # === AJOUT MAIL ===
        # ======================
        if user_email:
            sujet_mail = f"Récapitulatif des indisponibilités {now}"
            contenu_mail = "test"
            try:
                envoyer_mail(user_email, sujet_mail, contenu_mail)
                st.success(f"✅ Email envoyé à {user_email}")
            except Exception as e:
                st.error(f"❌ Erreur envoi mail : {e}")
