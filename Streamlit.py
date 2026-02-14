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
# SUPABASE
# ======================

from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# CONFIG
# ======================
NOM_SHEET = "Indisponibilites-enseignants-configs"
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
    # 🔑 Vérification mot de passe
    pwd_input = st.text_input("Entrez le mot de passe administrateur :", type="password")
    if pwd_input != ADMIN_PASSWORD:
        st.error("❌ Mot de passe incorrect. Accès refusé.")
        st.stop()

    st.success("✅ Mode Administrateur activé.")

    # --- Choix du filtre semestre ---
    semestre_choice = st.selectbox(
        "Afficher les semaines :",
        ["Toutes", "Pairs", "Impairs"],
        index=["Toutes", "Pairs", "Impairs"].index(st.session_state.semestre_filter)
    )
    st.session_state.semestre_filter = semestre_choice
    st.write(f"Semestres configurés : {st.session_state.semestre_filter}")

    # --- Sauvegarde du filtre dans la feuille Config ---
    try:
        rows = st.session_state.config_sheet.get_all_values()
        if len(rows) < 2:
            st.session_state.config_sheet.append_row([st.session_state.semestre_filter])
        else:
            st.session_state.config_sheet.update("A2", [[st.session_state.semestre_filter]])
    except Exception as e:
        st.warning(f"⚠️ Impossible de sauvegarder le filtre dans Config.\n{e}")

    # ======================
    # SUPPRESSION DES LIGNES DE LA FEUILLE 1
    # ======================
    st.subheader("⚠️ Supprimer toutes les indisponibilités")
    st.write("Cette action supprimera toutes les lignes de la Feuille 1 à partir de la ligne 2, mais conservera l'en-tête.")

    #if st.button("❌ Supprimer toutes les lignes de la Feuille 1 (à partir de la ligne 2)",key="admin_delete_all_rows"):
        #try:
            # Récupération de l'en-tête (1ère ligne)
            #header = st.session_state.sheet.get_all_values()[0:1]

            # Vider entièrement la feuille
            #st.session_state.sheet.clear()

            # Réécrire uniquement l'en-tête
            #if header:
                #st.session_state.sheet.append_rows(header, value_input_option="USER_ENTERED")

            # Rafraîchir les données en mémoire
            #st.session_state.all_data = st.session_state.sheet.get_all_values()

            #st.success("✅ Toutes les lignes ont été supprimées, l'en-tête est conservé !")
        #except Exception as e:
            #st.error(f"⚠️ Impossible de supprimer les lignes : {e}")
    if st.button("❌ Supprimer toutes les lignes de la table datas", key="admin_delete_all_rows"):
        try:
            supabase.table("datas").delete().neq("id", 0).execute()
            st.session_state.all_data = []
            st.success("✅ Toutes les lignes ont été supprimées !")
        except Exception as e:
            st.error(f"⚠️ Impossible de supprimer les lignes : {e}")




# ======================
# MODE UTILISATEUR
# ======================
else:
    st.title("📅 Gestion des indisponibilités enseignants")

    # Message spécifique semestre
    if st.session_state.semestre_filter == "Impairs":
        st.caption("     *Voeux semestres impairs— période correspondante : S1*")
    elif st.session_state.semestre_filter == "Pairs":
        st.caption("     *Voeux semestres pairs— période correspondante : S6*")
    else:
        st.caption("     *Voeux pour tous les semestres.*")

    st.divider()
    st.subheader("👨‍🏫 Informations Enseignant")

    # ======================
    # 1️⃣ Charger enseignants depuis Supabase
    # ======================
    try:
        resp_enseignants = supabase.table("enseignants").select("*").order("code").execute()
        enseignants = resp_enseignants.data
    except Exception as e:
        st.error(f"Erreur chargement enseignants : {e}")
        st.stop()

    if not enseignants:
        st.error("⚠️ Aucun enseignant trouvé dans Supabase")
        st.stop()

    # ======================
    # 2️⃣ Selectbox
    # ======================
    options = {f"{e['code']} – {e['nom']} {e['prenom']}": e["code"] for e in enseignants}
    label = st.selectbox("Choisissez votre nom", options.keys(), index=0)
    user_code = options[label].strip().upper()

    # ======================
    # 3️⃣ Récupérer ID enseignant
    # ======================
    resp_user = supabase.table("enseignants").select("id").eq("code", user_code).execute()

    if not resp_user.data:
        st.error("⚠️ Enseignant introuvable dans la base")
        st.stop()

    enseignant_id = resp_user.data[0]["id"]

    st.text_input("Votre adresse email pour recevoir le récapitulatif (facultatif):", key="email_utilisateur")

    # ======================
    # Filtrage semaines
    # ======================
    all_semaines = st.session_state.semaines_data
    if st.session_state.semestre_filter == "Pairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SP"]
    elif st.session_state.semestre_filter == "Impairs":
        filtered_semaines = [s for s in all_semaines if s[2] == "SI"]
    else:
        filtered_semaines = all_semaines

    # ======================
    # 🔄 Reset si changement utilisateur
    # ======================
    if st.session_state.selected_user != user_code:
        st.session_state.selected_user = user_code

        resp_data = supabase.table("datas").select("*").eq("enseignant_id", enseignant_id).execute()
        user_rows = resp_data.data

        st.session_state.ponctuels = []
        deja_vus = set()

        for r in user_rows:
			if r.get("code_streamlit", "").endswith("_P"):
				semaine = str(r.get("semaine", ""))
				jour = r.get("jour", "")
				creneau = r.get("creneau", "")

				key = (semaine, jour, creneau)

				if key not in deja_vus:
				    deja_vus.add(key)
				    st.session_state.ponctuels.append({
					    "id": str(uuid.uuid4()),
					    "semaine": semaine,
					    "jour": jour,
					    "creneau": creneau,
					    "raison": r.get("raisons", "")
                })


        # reset UI
        st.session_state.semaines_sel = []
        st.session_state.jours_sel = []
        st.session_state.creneaux_sel = []
        st.session_state.raison_sel = ""
        st.session_state.commentaire = ""
        if "email_utilisateur" in st.session_state:
            del st.session_state["email_utilisateur"]

        st.rerun()

    # ======================
    # Lecture données existantes
    # ======================
    resp_data = supabase.table("datas").select("*").eq("enseignant_id", enseignant_id).execute()
    user_rows = resp_data.data
    codes_sheet = {r["code_streamlit"] for r in user_rows} if user_rows else set()
    commentaire_existant = user_rows[-1]["commentaires_global"] if user_rows else ""
    dernier_timestamp = user_rows[-1].get("timestamp") if user_rows else None

    if codes_sheet:
        msg = (
            "⚠️ Des indisponibilités sont déjà enregistrées pour vous.<br>"
            "Toute modification effacera les anciennes données lors de l'enregistrement.<br>"
        )
        if dernier_timestamp:
            msg += f"Dernière modification effectuée le : {dernier_timestamp}"
        st.markdown(msg, unsafe_allow_html=True)

    # ======================
    # Fonctions ajout (INCHANGÉES)
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
    # UI ajout (INCHANGÉE)
    # ======================
    st.divider()
    st.subheader("🖊️ Saisir vos créneaux")

    st.multiselect("Semaine(s)", [r[0] for r in filtered_semaines], key="semaines_sel")
    st.multiselect("Jour(s)", [r[0] for r in st.session_state.jours_data], key="jours_sel")
    st.multiselect("Créneau(x)", [r[0] for r in st.session_state.creneaux_data], key="creneaux_sel")

    st.text_area("Raisons", key="raison_sel", height=80)
    st.button("➕ Ajouter", on_click=ajouter_creneaux, args=(codes_sheet, user_code))

    if st.session_state._warning_doublon:
        st.warning("⚠️ Certains créneaux existaient déjà et n'ont pas été ajoutés.")
        st.session_state._warning_doublon = False

    st.divider()

    # ======================
    # Tableau (INCHANGÉ)
    # ======================
    st.subheader("🗓️ Créneaux ajoutés/enregistrés")

    if st.session_state.ponctuels:
        if st.button("❌ Supprimer tous les créneaux"):
            st.session_state.ponctuels = []
            st.success("✅ Tous les créneaux ont été supprimés !")
            st.rerun()

        with st.expander("Voir les créneaux ajoutés/enregistrés", expanded=True):
            h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 1, 1])
            h1.markdown("**Semaine**")
            h2.markdown("**Jour**")
            h3.markdown("**Créneau**")
            h4.markdown("**Raison**")
            h5.markdown("**🗑️**")

            delete_id = None
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
    # Commentaire global (INCHANGÉ)
    # ======================
    commentaire_value = st.session_state.get("commentaire", commentaire_existant)
    st.text_area("💬 Commentaire global", value=commentaire_value, key="commentaire")

    # ======================
    # Enregistrement (INCHANGÉ)
    # ======================
    if st.button("💾 Enregistrer"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        supabase.table("datas").delete().eq("enseignant_id", enseignant_id).execute()

        for p in st.session_state.ponctuels:
            supabase.table("datas").insert({
                "enseignant_id": enseignant_id,
                "semaine": int(p.get("semaine", 0)),
                "jour": p.get("jour", ""),
                "creneau": p.get("creneau", ""),
                "code_creneau": f"{p.get('jour','')}_{p.get('creneau','')}",
                "code_streamlit": f"{user_code}_{p.get('semaine','')}_{p.get('jour','')}_{p.get('creneau','')}_P",
                "raisons": p.get("raison", ""),
                "commentaires_global": st.session_state.commentaire
            }).execute()

        st.success("✅ Indisponibilités enregistrées dans la base Supabase")

        # email
        destinataire = st.session_state.email_utilisateur
        if destinataire:
            sujet = f"Récapitulatif des indisponibilités - {now}"
            contenu = generer_contenu_email(user_code, st.session_state.ponctuels, st.session_state.commentaire, now)
            success, msg = envoyer_email(destinataire, sujet, contenu)

            if success:
                st.success(f"✅ Email envoyé à {destinataire}")
            else:
                st.error(f"❌ Erreur envoi mail : {msg}")
