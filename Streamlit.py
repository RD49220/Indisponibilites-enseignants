import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import os

# ======================
# BREVO SDK
# ======================
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail

# ======================
# CONFIGURATION BREVO
# ======================
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
# CONFIG GOOGLE SHEETS
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
except Exception as e:
    st.error(f"Impossible d'accéder à une des feuilles Google Sheet.\n{e}")
    st.stop()

# ======================
# CHARGEMENT DES DONNÉES
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
for k in ["ponctuels","selected_user","semaines_sel","jours_sel","creneaux_sel","raison_sel","commentaire","email_utilisateur"]:
    if k not in st.session_state:
        st.session_state[k] = "" if k in ["selected_user","raison_sel","commentaire","email_utilisateur"] else []

# ======================
# UI UTILISATEUR
# ======================
st.title("📅 Indisponibilités enseignants")

# Sélection utilisateur
users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
label = st.selectbox("Choisissez votre nom", options.keys())
user_code = options[label]

# Reset si utilisateur change
if st.session_state.selected_user != user_code:
    st.session_state.selected_user = user_code
    st.session_state.ponctuels = []
    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []
    st.session_state.raison_sel = ""
    st.session_state.commentaire = ""
    st.session_state.email_utilisateur = ""

# ======================
# Champ email pour récap
# ======================
st.text_input("Votre adresse email pour recevoir le récapitulatif :", key="email_utilisateur")

# ======================
# Fonctions ajout créneaux
# ======================
def ajouter_creneaux():
    doublon = False
    semaines_sel = get_semaines_nums(st.session_state.semaines_sel)
    jours_codes = get_jours_codes(st.session_state.jours_sel)
    creneaux_nums = get_creneaux_nums(st.session_state.creneaux_sel)
    raison_texte = st.session_state.raison_sel

    for s in semaines_sel:
        for j in jours_codes:
            for num in creneaux_nums:
                code = f"{user_code}_{j}_{num}_P"
                existe_streamlit = any(
                    p["semaine"] == s and p["jour"] == j and p["creneau"] == num
                    for p in st.session_state.ponctuels
                )
                if existe_streamlit:
                    doublon = True
                else:
                    st.session_state.ponctuels.append({
                        "id": str(uuid.uuid4()),
                        "semaine": s,
                        "jour": j,
                        "creneau": num,
                        "raison": raison_texte
                    })
    st.session_state.semaines_sel = []
    st.session_state.jours_sel = []
    st.session_state.creneaux_sel = []
    st.session_state.raison_sel = ""
    if doublon:
        st.warning("⚠️ Certains créneaux existaient déjà et n'ont pas été ajoutés.")

# ======================
# UI ajout créneaux
# ======================
st.subheader("➕ Créneaux ponctuels")
st.multiselect("Semaine(s)", [r[0] for r in st.session_state.semaines_data], key="semaines_sel")
st.multiselect("Jour(s)", [r[0] for r in st.session_state.jours_data], key="jours_sel")
st.multiselect("Créneau(x)", [r[0] for r in st.session_state.creneaux_data], key="creneaux_sel")
st.text_area("Raisons/Commentaires", key="raison_sel", height=80)
st.button("➕ Ajouter", on_click=ajouter_creneaux)

# ======================
# Tableau créneaux ajoutés
# ======================
st.subheader("📝 Créneaux ajoutés/enregistrés")
if st.session_state.ponctuels:
    delete_id = None
    h1, h2, h3, h4, h5 = st.columns([1,1,1,2,0.5])
    h1.markdown("**Semaine**")
    h2.markdown("**Jour**")
    h3.markdown("**Créneau**")
    h4.markdown("**Raison/Commentaire**")
    h5.markdown("**🗑️**")
    for r in st.session_state.ponctuels:
        c1,c2,c3,c4,c5 = st.columns([1,1,1,2,0.5])
        c1.write(r["semaine"])
        c2.write(CODE_TO_JOUR.get(r["jour"], r["jour"]))
        c3.write(CODE_TO_CREN.get(r["creneau"], r["creneau"]))
        c4.write(r.get("raison",""))
        if c5.button("🗑️", key=f"del_{r['id']}"):
            delete_id = r["id"]
    if delete_id:
        st.session_state.ponctuels = [r for r in st.session_state.ponctuels if r["id"] != delete_id]
        st.rerun()
else:
    st.write("Aucune indisponibilité enregistrée.")

# ======================
# Commentaire global
# ======================
st.text_area("💬 Commentaire global", value=st.session_state.commentaire, key="commentaire")

# ======================
# Enregistrement final + envoi email
# ======================
if st.button("💾 Enregistrer"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Suppression anciennes lignes utilisateur
    rows_to_delete = [i for i,r in enumerate(st.session_state.all_data[1:], start=2) if r[0]==user_code]
    for i in sorted(rows_to_delete, reverse=True):
        st.session_state.sheet.delete_rows(i)
    # Ajout des nouveaux créneaux
    rows_to_append = []
    for p in st.session_state.ponctuels:
        rows_to_append.append([
            user_code,
            p.get("semaine",""),
            CODE_TO_CREN.get(p.get("creneau",""), p.get("creneau","")),
            CODE_TO_JOUR.get(p.get("jour",""), p.get("jour","")),
            f"{p.get('jour','')}_{p.get('creneau','')}",
            f"{user_code}_{p.get('jour','')}_{p.get('creneau','')}_P",
            p.get("raison",""),
            st.session_state.commentaire,
            now
        ])
    if not rows_to_append:
        rows_to_append.append([
            user_code,"","","","","Aucune indisponibilité enregistrée.","",
            st.session_state.commentaire, now
        ])
    st.session_state.sheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
    st.success("✅ Indisponibilités enregistrées dans Google Sheets")

    # ======================
    # Envoi Brevo
    # ======================
    destinataire = st.session_state.email_utilisateur
    sujet = f"Récapitulatif des indisponibilités - {now}"
    contenu = "test"  # Plus tard remplacer par le vrai récap
    success, msg = envoyer_email(destinataire, sujet, contenu)
    if success:
        st.success(f"✅ Email envoyé à {destinataire}")
    else:
        st.error(f"❌ Erreur envoi mail : {msg}")
