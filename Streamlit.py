import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
# ======================
# BREVO SDK
# ======================
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail



# ======================
# CONFIG
# ======================
NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"
ADMIN_PASSWORD = st.secrets.get("admin_password", "monmotdepasse")  # 🔑 mot de passe admin

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
# DEBUG SECRET
# ======================
#if "admin_password" in st.secrets:
#    st.success("✅ Secret admin_password détecté")
#else:
#    st.error("❌ Secret admin_password INTROUVABLE")

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

#st.write(f"Config chargée au démarrage : {st.session_state.semestre_filter}")

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
# DICTIONNAIRES CRÉNEAUX, JOURS, SEMAINES
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
def generer_contenu_email(user_code, ponc, commentaire_global, timestamp):
    lines = [
        f"Bonjour {user_code},\n",
        f"Voici le récapitulatif de vos indisponibilités enregistré le {timestamp} :\n",
        "Semaine | Jour | Créneau | Commentaire",
        "----------------------------------------"
    ]

    if ponc:
        for p in ponc:
            semaine = p.get("semaine", "")
            jour = CODE_TO_JOUR.get(p.get("jour",""), p.get("jour",""))
            creneau = CODE_TO_CREN.get(p.get("creneau",""), p.get("creneau",""))
            raison = p.get("raison","")
            lines.append(f"{semaine} | {jour} | {creneau} | {raison}")
    else:
        lines.append("Aucune indisponibilité enregistrée.")

    lines.append(f"\nCommentaire global : {commentaire_global or '-'}\n")
    lines.append("Cordialement,\nService Planning GEII")

    return "\n".join(lines)

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
if "email_utilisateur" not in st.session_state:
    st.session_state.email_utilisateur = ""


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

    # Message spécifique semestre
    if st.session_state.semestre_filter == "Impairs":
        st.info("Choix pour le semestre Impairs. (La période correspond au S1)")
    elif st.session_state.semestre_filter == "Pairs":
        st.info("Choix pour le semestre Pair. (La période correspond au S6)")
    else:
        st.info("Choix pour tous les semestres.")

    # Filtrage semaines
    all_semaines = st.session_state.semaines_data
    if st.session_state.semestre_filter == "Pairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SP"]
    elif st.session_state.semestre_filter == "Impairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SI"]
    else:
        filtered_semaines = all_semaines

    # Choix utilisateur
    users = [{"code": r[0], "nom": r[1], "prenom": r[2]} for r in st.session_state.users_data if len(r) >= 3]
    options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}
    label = st.selectbox("Choisissez votre nom", options.keys())
    user_code = options[label]
    
    st.text_input("Votre adresse email pour recevoir le récapitulatif :", key="email_utilisateur")

        
    # 🔄 Reset et reload créneaux depuis Google Sheet si changement utilisateur
    if st.session_state.selected_user != user_code:
        st.session_state.selected_user = user_code

        # Rechargement depuis la feuille
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

        # Reset sélections
        st.session_state.semaines_sel = []
        st.session_state.jours_sel = []
        st.session_state.creneaux_sel = []
        st.session_state.raison_sel = ""
        st.session_state.commentaire = ""
        if "email_utilisateur" in st.session_state:
            del st.session_state["email_utilisateur"]



        st.rerun()  # 🔹 Rerun pour afficher les derniers créneaux

    # Lecture des données existantes pour affichage et doublons
    user_rows = [r for r in st.session_state.sheet.get_all_values()[1:] if r[0] == user_code]
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

    if codes_sheet:
        msg = (
            "⚠️ Des indisponibilités sont déjà enregistrées pour vous.<br>"
            "Toute modification effacera les anciennes données lors de l'enregistrement.<br>"
        )
        if dernier_timestamp:
            msg += f"Dernière modification effectuée le : {dernier_timestamp}"
        st.markdown(msg, unsafe_allow_html=True)

    # ======================
    # Fonctions ajout
    # ======================
    def ajouter_creneaux(codes_sheet, user_code):
        doublon = False
        semaines_sel = get_semaines_nums(st.session_state.semaines_sel)
        jours_codes = get_jours_codes(st.session_state.jours_sel)
        creneaux_nums = get_creneaux_nums(st.session_state.creneaux_sel)
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
    # UI ajout
    # ======================
    st.subheader("➕ Créneaux ponctuels")
    st.multiselect("Semaine(s)", [r[0] for r in filtered_semaines], key="semaines_sel")
    st.multiselect("Jour(s)", [r[0] for r in st.session_state.jours_data], key="jours_sel")
    st.multiselect("Créneau(x)", [r[0] for r in st.session_state.creneaux_data], key="creneaux_sel")

    st.text_area("Raisons/Commentaires", key="raison_sel", height=80)
    st.button("➕ Ajouter", on_click=ajouter_creneaux, args=(codes_sheet, user_code))

    if st.session_state._warning_doublon:
        st.warning("⚠️ Certains créneaux existaient déjà et n'ont pas été ajoutés.")
        st.session_state._warning_doublon = False

    st.divider()

    # ======================
    # Tableau + suppression individuelle
    # ======================
    st.subheader("📝 Créneaux ajoutés/enregistrés")
    if st.session_state.ponctuels:
        delete_id = None
        h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 1, 1])
        h1.markdown("**Semaine**")
        h2.markdown("**Jour**")
        h3.markdown("**Créneau**")
        h4.markdown("**Raisons/Commentaires**")
        h5.markdown("**🗑️**")

        for r in st.session_state.ponctuels:
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
            c1.write(r["semaine"] or "-")
            c2.write(CODE_TO_JOUR.get(r["jour"], r["jour"]) or "-")
            c3.write(CODE_TO_CREN.get(r["creneau"], r["creneau"]) or "-")
            c4.write(r.get("raison", "") or "-")
            if c5.button("🗑️", key=f"del_{r['id']}"):
                delete_id = r["id"]
        if delete_id:
            st.session_state.ponctuels = [r for r in st.session_state.ponctuels if r["id"] != delete_id]
            st.rerun()
    else:
        st.write("Aucune indisponibilité enregistrée.")

    st.divider()

    # ======================
    # Commentaire global
    # ======================
    commentaire_value = st.session_state.get("commentaire", commentaire_existant if 'commentaire_existant' in locals() else "")
    if commentaire_value is None or not isinstance(commentaire_value, str):
        commentaire_value = str(commentaire_value)

    st.text_area("💬 Commentaire global", value=commentaire_value, key="commentaire")

# ======================
# Enregistrement final + envoi email
# ======================
if st.button("💾 Enregistrer"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Suppression des anciennes lignes pour cet utilisateur ---
    rows_to_delete = [
        i for i, r in enumerate(st.session_state.all_data[1:], start=2)
        if r[0] == user_code
    ]
    for i in sorted(rows_to_delete, reverse=True):
        st.session_state.sheet.delete_rows(i)

    # --- Préparation des nouvelles lignes à ajouter ---
    rows_to_append = []
    for p in st.session_state.ponctuels:
        semaine = p.get("semaine", "")
        jour = p.get("jour", "")
        creneau = p.get("creneau", "")
        raison = p.get("raison", "")

        rows_to_append.append([
            user_code,        # Col A : user_code
            semaine,          # Col B : semaine
            jour,             # Col C : jour
            creneau,          # Col D : créneau
            f"{jour}_{creneau}",  # Col E : code interne (jour_creneau)
            f"{user_code}_{jour}_{creneau}_P",  # Col F : code complet
            raison,           # Col G : raison
            st.session_state.commentaire,  # Col H : commentaire global
            now               # Col I : timestamp
        ])

    # --- Ajout dans Google Sheets ---
    if rows_to_append:
        st.session_state.sheet.append_rows(
            rows_to_append,
            value_input_option="USER_ENTERED"
        )
        st.success("✅ Indisponibilités enregistrées dans Google Sheets")
    else:
        st.info("ℹ️ Aucun créneau à enregistrer")

    # ======================
    # Envoi email Brevo
    # ======================
    destinataire = st.session_state.email_utilisateur
    if destinataire:
        sujet = f"Récapitulatif des indisponibilités - {now}"
        contenu = generer_contenu_email(
            user_code,
            st.session_state.ponctuels,
            st.session_state.commentaire,
            now
        )
        success, msg = envoyer_email(destinataire, sujet, contenu)
        if success:
            st.success(f"✅ Email envoyé à {destinataire}")

