import sys
import os
import json
import random
import time
import requests
import uuid

# URL du serveur
SERVER_URL = "http://localhost:5000"

# --- Chargement/Sauvegarde des paramètres ---
SETTINGS_FILE = "settings.json"

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"music_volume": 0.5, "hover_volume": 0.5, "click_volume": 0.5, "fullscreen": False}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# --- Classes pour les personnages et équipes ---
class Personnage:
    def __init__(self, nom, classe, pv=100, arme="arme par défaut"):
        self.nom = nom
        self.classe = classe
        self.pv_max = pv
        self.pv = pv
        self.vivant = True
        self.arme = arme

    def est_vivant(self):
        return self.pv > 0

    def subir_degats(self, degats, jeu=None):
        self.pv -= degats
        if self.pv <= 0:
            self.pv = 0
            self.vivant = False
            if jeu:
                equipe_cible = "equipe1" if self in jeu.equipe2.personnages else "equipe2"
                jeu.stats[equipe_cible]["morts"] += 1
            return f"{self.nom} est mort !"
        return f"{self.nom} a subi {degats} points de dégâts ! Il lui reste {self.pv} PV."

    def soigner(self, soins, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas être soigné !"
        avant = self.pv
        self.pv = min(self.pv + soins, self.pv_max)
        soins_reels = self.pv - avant
        if jeu and soins_reels > 0:
            equipe_soigneur = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_soigneur]["soins_effectues"] += soins_reels
        return f"{self.nom} a récupéré {soins_reels} points de vie ! Il a maintenant {self.pv} PV."

    def __str__(self):
        status = "Mort" if not self.vivant else f"{self.pv}/{self.pv_max} PV"
        return f"{self.nom} ({self.classe} - {self.arme}) - {status}"

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "nom": self.nom,
            "classe": self.classe,
            "pv": self.pv,
            "pv_max": self.pv_max,
            "vivant": self.vivant,
            "arme": self.arme,
        }

    @staticmethod
    def from_dict(data):
        cls_map = {"Warrior": Warrior, "Druide": Druide, "Archer": Archer}
        cls = cls_map.get(data["type"], Personnage)
        perso = cls(data["nom"], pv=data["pv_max"], arme=data["arme"])
        perso.pv = data["pv"]
        perso.vivant = data["vivant"]
        return perso

class Warrior(Personnage):
    PHRASES_ATTAQUE = {
        "Tic-Tac Man": {
            "basique": "Tic-Tac Man fait tournoyer son tronc rageusement",
            "puissante": "Tic-Tac Man explose de colère et fracasse tout avec son tronc"
        },
        "UK": {
            "basique": "UK frappe méthodiquement avec son crâne ensanglanté",
            "puissante": "UK entre en rage et charge à toute vitesse"
        },
        "Tony Start": {
            "basique": "Tony Start électrocute légèrement son ennemi",
            "puissante": "Tony Start libère une surcharge électrique foudroyante"
        },
        "Dr. Colon": {
            "basique": "Dr. Colon sonde la douleur avec son coloscope",
            "puissante": "Dr. Colon pousse un hurlement viscéral et frappe sans retenue"
        },
        "Dr. Morbide": {
            "basique": "Dr. Morbide cogne brutalement avec ses mains",
            "puissante": "Dr. Morbide devient fou et détruit tout sur son passage"
        },
    }

    def __init__(self, nom, pv=130, arme="arme"):
        super().__init__(nom, "Warrior", pv, arme)

    def attaque_basique(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas attaquer !"
        degats = random.randint(35, 50)
        phrase = Warrior.PHRASES_ATTAQUE.get(self.nom, {}).get("basique", f"{self.nom} attaque {cible.nom} avec son {self.arme}")
        if jeu:
            equipe_attaquant = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_attaquant]["degats_infliges"] += degats
        cible.subir_degats(degats, jeu)
        message = f"{phrase}, infligeant {degats} points de dégâts à {cible.nom} ({cible.pv} PV restants) !"
        if not cible.vivant:
            message += f"\n{cible.nom} est mort !"
        return message

    def attaque_puissante(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas attaquer !"
        degats = random.randint(45, 60)
        degats_self = random.randint(3, 8)
        phrase = Warrior.PHRASES_ATTAQUE.get(self.nom, {}).get("puissante", f"{self.nom} utilise une attaque puissante sur {cible.nom}")
        if jeu:
            equipe_attaquant = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_attaquant]["degats_infliges"] += degats
        cible.subir_degats(degats, jeu)
        message = f"{phrase}, infligeant {degats} points de dégâts à {cible.nom} ({cible.pv} PV restants) !"
        if not cible.vivant:
            message += f"\n{cible.nom} est mort !"
        self.subir_degats(degats_self, jeu)
        message += f"\n{self.nom} subit un contrecoup de {degats_self} points de dégâts ({self.pv} PV restants) !"
        if not self.vivant:
            message += f"\n{self.nom} est mort !"
        return message

    def get_actions(self):
        return {
            "1": ("Attaque basique", self.attaque_basique),
            "2": ("Attaque puissante", self.attaque_puissante),
        }

class Druide(Personnage):
    PHRASES_DRUIDE = {
        "Sbaver-Man": {
            "attaque": "Sbaver-Man libère un torrent de bave corrosive !",
            "soin": "Sbaver-Man souffle une brume régénératrice !"
        },
        "Natasha": {
            "attaque": "Natasha projette un nuage empoisonné !",
            "soin": "Natasha envoie des bisous magiques qui guérissent !"
        },
        "Collette": {
            "attaque": "Collette déchaîne une vague d'énergie sauvage !",
            "soin": "Collette injecte une dose de vitalité fulgurante !"
        }
    }

    def __init__(self, nom, pv=90, arme="arme"):
        super().__init__(nom, "Druide", pv, arme)

    def soin_puissant(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas soigner !"
        soins = random.randint(35, 55)
        phrase = Druide.PHRASES_DRUIDE.get(self.nom, {}).get("soin", f"{self.nom} soigne {cible.nom} avec son {self.arme} !")
        message = f"{phrase}\n"
        message += cible.soigner(soins, jeu)
        return message

    def attaque_naturelle(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas attaquer !"
        degats = random.randint(25, 40)
        phrase = Druide.PHRASES_DRUIDE.get(self.nom, {}).get("attaque", f"{self.nom} attaque {cible.nom} avec la force de la nature !")
        if jeu:
            equipe_attaquant = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_attaquant]["degats_infliges"] += degats
        message = f"{phrase}\n"
        message += cible.subir_degats(degats, jeu)
        return message

    def get_actions(self):
        return {
            "1": ("Soin puissant", self.soin_puissant),
            "2": ("Attaque naturelle", self.attaque_naturelle)
        }

class Archer(Personnage):
    PHRASES_ARCHER = {
        "L'oeil de con": {
            "simple": "L'oeil de con décoche une flèche bancale mais rapide.",
            "precis": "L'oeil de con vise entre les deux yeux avec précision !"
        },
        "Bruno le Clown": {
            "simple": "Bruno le Clown tire une flèche surprise cachée dans un ballon !",
            "precis": "Bruno le Clown ajuste son tir avec un rire démoniaque."
        }
    }

    def __init__(self, nom, pv=85, arme="arme"):
        super().__init__(nom, "Archer", pv, arme)

    def tir_simple(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas attaquer !"
        degats = random.randint(50, 70)
        phrase = Archer.PHRASES_ARCHER.get(self.nom, {}).get("simple", f"{self.nom} tire une flèche sur {cible.nom} !")
        if jeu:
            equipe_attaquant = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_attaquant]["degats_infliges"] += degats
        message = f"{phrase}\n"
        message += cible.subir_degats(degats, jeu)
        return message

    def tir_precis(self, cible, jeu=None):
        if not self.vivant:
            return f"{self.nom} est mort et ne peut pas attaquer !"
        critique = random.random() < 0.3
        degats = random.randint(60, 80)
        if critique:
            degats = int(degats * 1.5)
            phrase = Archer.PHRASES_ARCHER.get(self.nom, {}).get("precis", f"{self.nom} réalise un tir critique sur {cible.nom} !")
            phrase = "🎯 TIR CRITIQUE ! " + phrase
        else:
            phrase = Archer.PHRASES_ARCHER.get(self.nom, {}).get("precis", f"{self.nom} vise avec précision.")
        if jeu:
            equipe_attaquant = "equipe1" if self in jeu.equipe1.personnages else "equipe2"
            jeu.stats[equipe_attaquant]["degats_infliges"] += degats
        message = f"{phrase}\n"
        message += cible.subir_degats(degats, jeu)
        return message

    def get_actions(self):
        return {
            "1": ("Tir simple", self.tir_simple),
            "2": ("Tir précis", self.tir_precis),
        }

class Equipe:
    def __init__(self, nom, personnages):
        self.nom = nom
        self.personnages = personnages

    def est_vivante(self):
        return any(perso.est_vivant() for perso in self.personnages)

    def membres_vivants(self):
        return [perso for perso in self.personnages if perso.est_vivant()]

    def __str__(self):
        resultat = f"Équipe {self.nom}:\n"
        for i, perso in enumerate(self.personnages, 1):
            resultat += f"{i}. {perso}\n"
        return resultat

    def to_dict(self):
        return {
            "nom": self.nom,
            "personnages": [p.to_dict() for p in self.personnages]
        }

    @staticmethod
    def from_dict(data):
        persos = [Personnage.from_dict(p) for p in data["personnages"]]
        return Equipe(data["nom"], persos)

class LoadGamePanel:
    def __init__(self):
        self.save_files = self.get_save_files()
        self.selected_save = 0

    def get_save_files(self):
        save_dir = "saves"
        if not os.path.exists(save_dir):
            return []
        return [f for f in os.listdir(save_dir) if f.endswith('.json')]

    def display(self):
        if not self.save_files:
            print("Aucune sauvegarde trouvée.")
            return
        print("\nCharger une partie :")
        for i, save_file in enumerate(self.save_files):
            try:
                with open(os.path.join("saves", save_file), 'r') as f:
                    data = json.load(f)
                    save_name = data.get("save_name", save_file)
            except:
                save_name = save_file
            prefix = "> " if i == self.selected_save else "  "
            print(f"{prefix}{i + 1}. {save_name}")
        print("\nUtilisez les touches 1, 2, ... pour sélectionner une sauvegarde, 'r' pour revenir.")

    def load_game(self, save_file):
        try:
            with open(os.path.join("saves", save_file), 'r') as f:
                save_data = json.load(f)
            jeu = Jeu.from_dict(save_data)
            return GamePanel(jeu, mode='local')
        except Exception as e:
            print(f"Erreur lors du chargement de la partie : {e}")
            return None

    def handle_input(self, choice):
        if choice == 'r':
            return False
        try:
            index = int(choice) - 1
            if 0 <= index < len(self.save_files):
                self.selected_save = index
                panel = self.load_game(self.save_files[self.selected_save])
                if panel:
                    return panel
            else:
                print("Choix invalide.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro ou 'r'.")
        return True

class SettingsPanel:
    def __init__(self):
        settings = load_settings()
        self.music_volume = settings.get("music_volume", 0.5)
        self.hover_volume = settings.get("hover_volume", 0.5)
        self.click_volume = settings.get("click_volume", 0.5)
        self.fullscreen = settings.get("fullscreen", False)

    def display(self):
        print("\nParamètres :")
        print(f"1. Volume de la musique : {int(self.music_volume * 100)}%")
        print(f"2. Volume des survols : {int(self.hover_volume * 100)}%")
        print(f"3. Volume des clics : {int(self.click_volume * 100)}%")
        print(f"4. Plein écran : {'Oui' if self.fullscreen else 'Non'}")
        print("\nEntrez le numéro (1-4) pour modifier un paramètre, ou 'r' pour revenir.")

    def handle_input(self, choice):
        if choice == 'r':
            save_settings({
                "music_volume": self.music_volume,
                "hover_volume": self.hover_volume,
                "click_volume": self.click_volume,
                "fullscreen": self.fullscreen
            })
            return False
        try:
            choice = int(choice)
            if choice == 1:
                value = input("Entrez le volume de la musique (0-100) : ")
                try:
                    self.music_volume = max(0, min(float(value) / 100, 1.0))
                    print(f"Volume de la musique défini à {int(self.music_volume * 100)}%")
                except ValueError:
                    print("Valeur invalide. Utilisez un nombre entre 0 et 100.")
            elif choice == 2:
                value = input("Entrez le volume des survols (0-100) : ")
                try:
                    self.hover_volume = max(0, min(float(value) / 100, 1.0))
                    print(f"Volume des survols défini à {int(self.hover_volume * 100)}%")
                except ValueError:
                    print("Valeur invalide. Utilisez un nombre entre 0 et 100.")
            elif choice == 3:
                value = input("Entrez le volume des clics (0-100) : ")
                try:
                    self.click_volume = max(0, min(float(value) / 100, 1.0))
                    print(f"Volume des clics défini à {int(self.click_volume * 100)}%")
                except ValueError:
                    print("Valeur invalide. Utilisez un nombre entre 0 et 100.")
            elif choice == 4:
                self.fullscreen = not self.fullscreen
                print(f"Plein écran : {'Oui' if self.fullscreen else 'Non'}")
            else:
                print("Choix invalide.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro ou 'r'.")
        return True

class LocalGameModePanel:
    def __init__(self):
        self.selected_mode = 0
        self.modes = ["Classique", "Personnalisé"]

    def display(self):
        print("\nNouvelle partie locale - Sélection du mode :")
        for i, mode in enumerate(self.modes):
            prefix = "> " if i == self.selected_mode else "  "
            print(f"{prefix}{i + 1}. {mode}")
        print("\nUtilisez les touches 1-2 pour sélectionner un mode, 'r' pour revenir.")

    def handle_input(self, choice):
        if choice == 'r':
            return False
        try:
            index = int(choice) - 1
            if 0 <= index < len(self.modes):
                self.selected_mode = index
                if index == 0:
                    return TeamSelectionPanel()
                else:
                    return CustomTeamSelectionPanel()
            else:
                print("Choix invalide.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro ou 'r'.")
        return True

class OnlineGameModePanel:
    def __init__(self):
        self.player_id = str(uuid.uuid4())[:8]
        self.game_id = None
        self.mode = None  # 'host' ou 'join'

    def display(self):
        print("\nMode en ligne :")
        print("1. Héberger une partie")
        print("2. Rejoindre une partie")
        print("\nEntrez 1 ou 2, ou 'r' pour revenir.")

    def handle_input(self, choice):
        if choice == 'r':
            return False
        try:
            choice = int(choice)
            if choice == 1:
                self.mode = 'host'
                response = requests.post(f"{SERVER_URL}/create_game", json={'player_id': self.player_id})
                if response.status_code != 200:
                    print(f"Erreur : {response.json()['error']}")
                    return True
                self.game_id = response.json()['game_id']
                print(f"Partie créée avec l’ID : {self.game_id}")
                print("En attente d’un second joueur...")
                while True:
                    response = requests.get(f"{SERVER_URL}/game_state/{self.game_id}")
                    if response.status_code != 200:
                        print("Erreur lors de la récupération de l’état")
                        return True
                    game = response.json()
                    if game['status'] == 'waiting_teams':
                        print("Un joueur a rejoint ! Veuillez sélectionner votre équipe.")
                        return TeamSelectionPanel(mode='online', player_id=self.player_id, game_id=self.game_id, player_team='equipe1')
                    time.sleep(0.5)
            elif choice == 2:
                self.mode = 'join'
                self.game_id = input("Entrez l’ID de la partie : ").strip()
                response = requests.post(f"{SERVER_URL}/join_game", json={'game_id': self.game_id, 'player_id': self.player_id})
                if response.status_code != 200:
                    print(f"Erreur : {response.json()['error']}")
                    return True
                print("Partie rejointe ! Veuillez sélectionner votre équipe.")
                return TeamSelectionPanel(mode='online', player_id=self.player_id, game_id=self.game_id, player_team='equipe2')
            else:
                print("Choix invalide.")
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro ou 'r'.")
        return True

class MapSelectionPanel:
    def __init__(self, jeu, mode='local', player_id=None, game_id=None, player_team=None):
        self.jeu = jeu
        self.maps = [
            "Hôpital Sainte Dérive",
            "Carrefour Saint-Sever",
            "Quartier Yvetot",
            "Restaurant Flunch"
        ]
        self.selected_map = 0
        self.mode = mode
        self.player_id = player_id
        self.game_id = game_id
        self.player_team = player_team

    def display(self):
        clear_screen()
        print(f"\n{'='*50}")
        print("Sélection de la carte".center(50))
        print(f"{'='*50}\n")
        print("Choisissez une carte pour le combat :")
        print("-"*50)
        for i, map_name in enumerate(self.maps, 1):
            prefix = "> " if i - 1 == self.selected_map else "  "
            print(f"{prefix}{i}. {map_name}")
        print("-"*50)
        print("\nEntrez le numéro de la carte (1-4), ou 'r' pour revenir à la sélection des équipes.")

    def handle_input(self, choice):
        if choice == 'r':
            return TeamSelectionPanel(mode=self.mode, player_id=self.player_id, game_id=self.game_id, player_team=self.player_team)
        try:
            choix = int(choice)
            if 1 <= choix <= len(self.maps):
                self.jeu.map = self.maps[choix - 1]
                print(f"\nCarte sélectionnée : {self.jeu.map}")
                if self.mode == 'online':
                    if self.player_team != 'equipe1':
                        print("Seul le joueur 1 peut sélectionner la carte.")
                        return True
                    response = requests.post(f"{SERVER_URL}/submit_map", json={
                        'game_id': self.game_id,
                        'player_id': self.player_id,
                        'map': self.jeu.map
                    })
                    if response.status_code != 200:
                        print(f"Erreur : {response.json()['error']}")
                        return True
                    print(response.json()['message'])
                    return GamePanel(self.jeu, mode='online', player_id=self.player_id, game_id=self.game_id, player_team=self.player_team)
                return GamePanel(self.jeu, mode='local')
            else:
                print(f"Veuillez entrer un nombre entre 1 et {len(self.maps)}.")
                return True
        except ValueError:
            print("Veuillez entrer un nombre valide ou 'r'.")
        return True

class TeamSelectionPanel:
    def __init__(self, mode='local', player_id=None, game_id=None, player_team=None):
        self.jeu = Jeu()
        self.current_player = "Joueur 1" if player_team == 'equipe1' else "Joueur 2"
        self.equipes_disponibles = list(Jeu.EQUIPES_PERSONNAGES.keys())
        self.equipe_choisie = None
        self.mode = mode
        self.player_id = player_id
        self.game_id = game_id
        self.player_team = player_team

    def display(self):
        clear_screen()
        print(f"\n{'='*50}")
        print(f"Mode {'En ligne' if self.mode == 'online' else 'Classique'} - Sélection de l'équipe pour {self.current_player}".center(50))
        print(f"{'='*50}\n")
        print("Choisissez une équipe prédéfinie :")
        print("-"*50)
        for i, equipe in enumerate(self.equipes_disponibles, 1):
            print(f"{i}. {equipe}")
            for perso in Jeu.EQUIPES_PERSONNAGES[equipe]:
                nom, cls, pv, arme = perso
                print(f"   - {nom} ({cls.__name__}, {pv} PV, Arme: {arme})")
        print("-"*50)
        print("\nEntrez le numéro de l'équipe (1-{})".format(len(self.equipes_disponibles)))

    def handle_input(self, choice):
        try:
            choix = int(choice)
            if 1 <= choix <= len(self.equipes_disponibles):
                self.equipe_choisie = self.equipes_disponibles[choix - 1]
                equipe = self.jeu.selectionner_equipe(self.current_player, equipe_choisie=self.equipe_choisie)
                equipe.nom = self.equipe_choisie
                if self.mode == 'online':
                    response = requests.post(f"{SERVER_URL}/submit_team", json={
                        'game_id': self.game_id,
                        'player_id': self.player_id,
                        'equipe': equipe.to_dict()
                    })
                    if response.status_code != 200:
                        print(f"Erreur : {response.json()['error']}")
                        return True
                    print(response.json()['message'])
                    print("En attente de l’autre joueur...")
                    while True:
                        response = requests.get(f"{SERVER_URL}/game_state/{self.game_id}")
                        if response.status_code != 200:
                            print(f"Erreur : {response.json()['error']}")
                            return True
                        game = response.json()
                        if game['status'] == 'waiting_map':
                            self.jeu.equipe1 = Equipe.from_dict(game['equipe1'])
                            self.jeu.equipe2 = Equipe.from_dict(game['equipe2'])
                            if self.player_team == 'equipe1':
                                return MapSelectionPanel(self.jeu, mode='online', player_id=self.player_id, game_id=self.game_id, player_team=self.player_team)
                            else:
                                print("En attente de la sélection de la carte par le Joueur 1...")
                                while True:
                                    response = requests.get(f"{SERVER_URL}/game_state/{self.game_id}")
                                    if response.status_code != 200:
                                        print(f"Erreur : {response.json()['error']}")
                                        return True
                                    game_state = response.json()
                                    if game_state['status'] == 'ongoing':
                                        self.jeu.map = game_state['map']
                                        return GamePanel(self.jeu, mode='online', player_id=self.player_id, game_id=self.game_id, player_team=self.player_team)
                                    time.sleep(0.5)
                        time.sleep(0.5)
                else:
                    if self.current_player == "Joueur 1":
                        self.jeu.equipe1 = equipe
                        self.current_player = "Joueur 2"
                        return True
                    else:
                        self.jeu.equipe2 = equipe
                        print("\n=== Équipes sélectionnées ===")
                        print(self.jeu.equipe1)
                        print(self.jeu.equipe2)
                        self.jeu.initialiser_jeu(self.jeu.equipe1, self.jeu.equipe2)
                        return MapSelectionPanel(self.jeu, mode='local')
            else:
                print(f"Veuillez entrer un nombre entre 1 et {len(self.equipes_disponibles)}.")
                return True
        except ValueError:
            print("Veuillez entrer un nombre valide.")
            return True

class CustomTeamSelectionPanel:
    def __init__(self):
        self.jeu = Jeu()
        self.equipe1 = None
        self.equipe2 = None
        self.current_player = "Joueur 1"
        self.personnages = self.get_all_personnages()
        self.state = "nom_equipe"
        self.nom_equipe = ""
        self.equipe_temp = []
        self.personnage_index = 0

    def get_all_personnages(self):
        personnages = []
        for equipe in Jeu.EQUIPES_PERSONNAGES.values():
            personnages.extend(equipe)
        return list(set(personnages))

    @property
    def input_prompt(self):
        if self.state == "nom_equipe":
            return f"Entrez le nom de votre équipe ({self.current_player}) : "
        elif self.state == "selection_personnages":
            return "Entrez le numéro du personnage choisi : "

    def display(self):
        if self.state == "nom_equipe":
            print(f"\nSélection de l’équipe pour {self.current_player} (Mode Personnalisé)")
        elif self.state == "selection_personnages":
            print(f"\nSélection des personnages pour {self.current_player} (Mode Personnalisé)")
            print(f"Équipe : {self.nom_equipe}")
            print(f"Choisissez 5 personnages pour votre équipe ({self.personnage_index + 1}/5) :")
            for i, (nom, cls, pv, arme) in enumerate(self.personnages, 1):
                print(f"{i}. {nom} ({cls.__name__}, {pv} PV, Arme: {arme})")
            if self.equipe_temp:
                print("\nPersonnages déjà sélectionnés :")
                for i, perso in enumerate(self.equipe_temp, 1):
                    print(f"{i}. {perso.nom} ({perso.classe}, {perso.pv} PV, Arme: {perso.arme})")

    def handle_input(self, choice):
        if self.state == "nom_equipe":
            self.nom_equipe = choice.strip() or f"Équipe du {self.current_player}"
            self.state = "selection_personnages"
            return True
        elif self.state == "selection_personnages":
            try:
                choix = int(choice)
                if 1 <= choix <= len(self.personnages):
                    nom, cls, pv, arme = self.personnages[choix - 1]
                    self.equipe_temp.append(cls(nom, pv=pv, arme=arme))
                    print(f"{nom} ajouté à l’équipe.")
                    self.personnage_index += 1
                    if self.personnage_index >= 5:
                        if self.current_player == "Joueur 1":
                            self.equipe1 = Equipe(self.nom_equipe, self.equipe_temp)
                            self.current_player = "Joueur 2"
                            self.state = "nom_equipe"
                            self.nom_equipe = ""
                            self.equipe_temp = []
                            self.personnage_index = 0
                            return True
                        else:
                            self.equipe2 = Equipe(self.nom_equipe, self.equipe_temp)
                            print("\n=== Équipes sélectionnées ===")
                            print(self.equipe1)
                            print(self.equipe2)
                            self.jeu.initialiser_jeu(self.equipe1, self.equipe2)
                            return MapSelectionPanel(self.jeu)
                    return True
                else:
                    print(f"Veuillez entrer un nombre entre 1 et {len(self.personnages)}.")
                    return True
            except ValueError:
                print("Veuillez entrer un nombre valide.")
                return True

class GamePanel:
    def __init__(self, jeu, mode='local', player_id=None, game_id=None, player_team=None):
        self.jeu = jeu
        self.mode = mode
        self.player_id = player_id
        self.game_id = game_id
        self.player_team = player_team
        self.last_action_message = None

    def display(self):
        if self.mode == 'online':
            response = requests.get(f"{SERVER_URL}/game_state/{self.game_id}")
            if response.status_code != 200:
                print(f"Erreur : {response.json()['error']}")
                return True
            game_state = response.json()
            self.jeu = Jeu.from_dict(game_state)

            if game_state['status'] == 'waiting_player2':
                print("En attente d’un second joueur...")
                time.sleep(0.5)
                return True
            if game_state['status'] == 'waiting_teams':
                print("En attente de la sélection des équipes...")
                time.sleep(0.5)
                return True
            if game_state['status'] == 'waiting_map' and self.player_team != 'equipe1':
                print("En attente de la sélection de la carte par le Joueur 1...")
                time.sleep(0.5)
                return True
            if game_state['status'] == 'finished':
                self.afficher_vainqueur(game_state)
                return False

            is_player_turn = (
                (self.player_team == 'equipe1' and game_state['equipe_active_nom'] == self.jeu.equipe1.nom) or
                (self.player_team == 'equipe2' and game_state['equipe_active_nom'] == self.jeu.equipe2.nom)
            )

            self.jeu.afficher_etat()
            if is_player_turn:
                print("🎮 À votre tour ! Choisissez un personnage, une action et une cible.")
            else:
                print(f"⏳ En attente du tour de l’équipe {game_state['equipe_active_nom']}...")
            if self.last_action_message:
                print(f"\nDernière action : {self.last_action_message}")

            if not is_player_turn:
                time.sleep(0.5)
                return True
            return True
        else:
            self.jeu.tour_de_jeu()
            return True

    def afficher_vainqueur(self, game_state):
        vainqueur = game_state['equipe2']['nom'] if not any(p['vivant'] for p in game_state['equipe1']['personnages']) else game_state['equipe1']['nom']
        print(f"\n{'='*50}")
        print(f"L'équipe {vainqueur} a gagné en {game_state['tour_actuel']} tours sur la carte {game_state['map']} !")
        print(f"{'='*50}")
        print("\n=== Statistiques de la partie ===")
        print(f"Nombre de tours joués : {game_state['tour_actuel']}")
        print(f"\nÉquipe {game_state['equipe1']['nom']}:")
        print(f"  Dégâts infligés : {game_state['stats'][game_state['equipe1']['nom']]['degats_infliges']} PV")
        print(f"  Soins effectués : {game_state['stats'][game_state['equipe1']['nom']]['soins_effectues']} PV")
        print(f"  Personnages perdus : {game_state['stats'][game_state['equipe1']['nom']]['morts']}")
        print(f"  Personnages vivants : {len([p for p in game_state['equipe1']['personnages'] if p['vivant']])}")
        print(f"\nÉquipe {game_state['equipe2']['nom']}:")
        print(f"  Dégâts infligés : {game_state['stats'][game_state['equipe2']['nom']]['degats_infliges']} PV")
        print(f"  Soins effectués : {game_state['stats'][game_state['equipe2']['nom']]['soins_effectues']} PV")
        print(f"  Personnages perdus : {game_state['stats'][game_state['equipe2']['nom']]['morts']}")
        print(f"  Personnages vivants : {len([p for p in game_state['equipe2']['personnages'] if p['vivant']])}")
        print(f"{'='*50}")
        choix = input("\nVoulez-vous recommencer une partie ? (O/N): ").strip()
        if choix.upper() == 'O':
            print("Retour au menu principal...")
            return False
        else:
            print("Merci d'avoir joué !")
            return False

    def handle_input(self, choice):
        if self.mode == 'online':
            response = requests.get(f"{SERVER_URL}/game_state/{self.game_id}")
            if response.status_code != 200:
                print(f"Erreur : {response.json()['error']}")
                return True
            game_state = response.json()
            self.jeu = Jeu.from_dict(game_state)

            if game_state['status'] == 'finished':
                self.afficher_vainqueur(game_state)
                return False

            is_player_turn = (
                (self.player_team == 'equipe1' and game_state['equipe_active_nom'] == self.jeu.equipe1.nom) or
                (self.player_team == 'equipe2' and game_state['equipe_active_nom'] == self.jeu.equipe2.nom)
            )
            if not is_player_turn:
                print(f"Ce n’est pas votre tour ! En attente de l’équipe {game_state['equipe_active_nom']}.")
                return True

            personnage = self.jeu.choisir_personnage()
            if not personnage:
                print("Pas de personnage disponible !")
                return True
            action = self.jeu.choisir_action(personnage)
            cible = self.jeu.choisir_cible(action)
            if not cible:
                print("Aucune cible disponible !")
                return True

            personnage_index = self.jeu.equipe_active.membres_vivants().index(personnage)
            action_key = None
            for k, (nom_action, func) in personnage.get_actions().items():
                if func.__name__ == action.__name__:
                    action_key = k
                    break
            if not action_key:
                print("Erreur : Action non trouvée.")
                return True

            cible_equipe = self.jeu.equipe_active if action == Druide.soin_puissant else self.jeu.equipe_inactive
            cible_index = cible_equipe.membres_vivants().index(cible)

            response = requests.post(f"{SERVER_URL}/make_move", json={
                'game_id': self.game_id,
                'player_id': self.player_id,
                'personnage_index': personnage_index,
                'action_key': action_key,
                'cible_index': cible_index
            })
            if response.status_code != 200:
                print(f"Erreur : {response.json()['error']}")
                return True

            result = response.json()
            self.last_action_message = result['message']
            print("\nRésultat de l’action :")
            print(self.last_action_message)
            input("\nAppuyez sur Entrée pour continuer...")
            return True
        else:
            if self.jeu.est_termine():
                self.jeu.afficher_etat()
                result = self.jeu.afficher_vainqueur()
                return result
            return True

class Jeu:
    EQUIPES_PERSONNAGES = {
        "Pilules Bleues": [
            ("Natasha", Druide, 90, "bouche"),
            ("Collette", Druide, 90, "seringue"),
            ("Dr. Colon", Warrior, 130, "coloscope"),
            ("Bruno le Clown", Archer, 85, "ballon"),
            ("Dr. Morbide", Warrior, 130, "mains")
        ],
        "4 Fantastiques et Demi": [
            ("Tic-Tac Man", Warrior, 130, "tronc"),
            ("UK", Warrior, 130, "crâne"),
            ("Tony Start", Warrior, 130, "pile électrique"),
            ("Sbaver-Man", Druide, 90, "salive"),
            ("L'oeil de con", Archer, 85, "arc")
        ]
    }

    def __init__(self):
        self.equipe1 = None
        self.equipe2 = None
        self.tour_actuel = 1
        self.equipe_active = None
        self.equipe_inactive = None
        self.map = None
        self.stats = {
            "equipe1": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0},
            "equipe2": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0}
        }

    def selectionner_equipe(self, joueur="Joueur", equipe_choisie=None):
        if equipe_choisie is None:
            print(f"\n=== Sélection de l'équipe pour {joueur} ===")
            print("Choisissez votre équipe :")
            equipes_disponibles = list(self.EQUIPES_PERSONNAGES.keys())
            for i, equipe in enumerate(equipes_disponibles, 1):
                print(f"{i}. {equipe}")
            
            while True:
                try:
                    choix_equipe = input("Entrez le numéro de l’équipe : ")
                    choix_equipe = int(choix_equipe)
                    if 1 <= choix_equipe <= len(equipes_disponibles):
                        equipe_choisie = equipes_disponibles[choix_equipe - 1]
                        break
                    else:
                        print(f"Veuillez entrer un nombre entre 1 et {len(equipes_disponibles)}.")
                except ValueError:
                    print("Veuillez entrer un nombre valide.")

        print(f"\nVous avez choisi l’équipe : {equipe_choisie}")
        equipe = []
        personnages_disponibles = self.EQUIPES_PERSONNAGES[equipe_choisie]
        
        for nom, cls, pv, arme in personnages_disponibles:
            equipe.append(cls(nom, pv=pv, arme=arme))
        
        return Equipe(equipe_choisie, equipe)

    def initialiser_jeu(self, equipe1=None, equipe2=None):
        self.equipe1 = equipe1 if equipe1 else Equipe("4 Fantastiques et Demi", [
            Warrior("Tic-Tac Man", 130, "tronc"),
            Warrior("UK", 130, "crâne"),
            Warrior("Tony Start", 130, "pile électrique"),
            Druide("Sbaver-Man", 90, "salive"),
            Archer("L'oeil de con", 85, "arc")
        ])
        self.equipe2 = equipe2 if equipe2 else Equipe("Pilules Bleues", [
            Druide("Natasha", 90, "bouche"),
            Druide("Collette", 90, "seringue"),
            Warrior("Dr. Colon", 130, "coloscope"),
            Archer("Bruno le Clown", 85, "ballon"),
            Warrior("Dr. Morbide", 130, "mains")
        ])
        self.tour_actuel = 1
        self.equipe_active = self.equipe1
        self.equipe_inactive = self.equipe2
        self.stats = {
            "equipe1": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0},
            "equipe2": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0}
        }
        print("\nJeu initialisé ! Les équipes sont prêtes pour le combat.")
        return True

    def to_dict(self):
        return {
            "equipe1": self.equipe1.to_dict() if self.equipe1 else None,
            "equipe2": self.equipe2.to_dict() if self.equipe2 else None,
            "tour_actuel": self.tour_actuel,
            "equipe_active_nom": self.equipe_active.nom if self.equipe_active else None,
            "map": self.map,
            "save_name": f"Partie_{self.tour_actuel}",
            "stats": self.stats
        }

    @staticmethod
    def from_dict(data):
        jeu = Jeu()
        jeu.equipe1 = Equipe.from_dict(data["equipe1"]) if data["equipe1"] else None
        jeu.equipe2 = Equipe.from_dict(data["equipe2"]) if data["equipe2"] else None
        jeu.tour_actuel = data["tour_actuel"]
        jeu.map = data["map"]
        jeu.stats = data.get("stats", {
            "equipe1": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0},
            "equipe2": {"degats_infliges": 0, "soins_effectues": 0, "morts": 0}
        })
        if jeu.equipe1 and data["equipe_active_nom"] == jeu.equipe1.nom:
            jeu.equipe_active = jeu.equipe1
            jeu.equipe_inactive = jeu.equipe2
        elif jeu.equipe2:
            jeu.equipe_active = jeu.equipe2
            jeu.equipe_inactive = jeu.equipe1
        return jeu

    def changer_tour(self):
        self.tour_actuel += 1
        self.equipe_active, self.equipe_inactive = self.equipe_inactive, self.equipe_active

    def afficher_etat(self):
        clear_screen()
        print(f"\n{'='*60}")
        print(f"Carte : {self.map if self.map else 'Non sélectionnée'}")
        print(f"Tour {self.tour_actuel} - Équipe active : {self.equipe_active.nom}")
        print(f"{'='*60}")

        print(f"\nÉquipe {self.equipe_active.nom} (ACTIVE):")
        for i, perso in enumerate(self.equipe_active.personnages, 1):
            status = "MORT" if not perso.vivant else f"{perso.pv}/{perso.pv_max} PV"
            print(f"{i}. {perso.nom} ({perso.classe} - {perso.arme}) - {status}")
        print(f"\nÉquipe {self.equipe_inactive.nom}:")
        for i, perso in enumerate(self.equipe_inactive.personnages, 1):
            status = "MORT" if not perso.vivant else f"{perso.pv}/{perso.pv_max} PV"
            print(f"{i}. {perso.nom} ({perso.classe} - {perso.arme}) - {status}")
        print(f"\n{'='*60}\n")

    def choisir_personnage(self):
        personnages_vivants = self.equipe_active.membres_vivants()
        if not personnages_vivants:
            return None
        print(f"\nChoisissez un personnage de l’équipe {self.equipe_active.nom}:")
        for i, perso in enumerate(personnages_vivants, 1):
            print(f"{i}. {perso.nom} ({perso.classe} - {perso.arme}) - {perso.pv}/{perso.pv_max} PV")
        while True:
            try:
                choix = input("Votre choix : ")
                choix = int(choix)
                if 1 <= choix <= len(personnages_vivants):
                    return personnages_vivants[choix - 1]
                else:
                    print(f"Veuillez entrer un nombre entre 1 et {len(personnages_vivants)}")
            except ValueError:
                print("Veuillez entrer un nombre valide")

    def choisir_action(self, personnage):
        actions = personnage.get_actions()
        print(f"\nChoisissez une action pour {personnage.nom} ({personnage.arme}):")
        for key, (nom_action, _) in actions.items():
            print(f"{key}. {nom_action}")
        while True:
            choix = input("Votre choix : ")
            if choix in actions:
                return actions[choix][1]
            else:
                print(f"Veuillez entrer un choix valide ({', '.join(actions.keys())}")

    def choisir_cible(self, action):
        actions_soin = [Druide.soin_puissant]
        if action in actions_soin:
            cibles = self.equipe_active.membres_vivants()
            equipe_cible = self.equipe_active
            cible_type = "allié"
        else:
            cibles = self.equipe_inactive.membres_vivants()
            equipe_cible = self.equipe_inactive
            cible_type = "ennemi"

        if not cibles:
            return None

        print(f"\nChoisissez une cible {cible_type} dans l'équipe {equipe_cible.nom}:")
        for i, perso in enumerate(cibles, 1):
            print(f"{i}. {perso.nom} ({perso.classe} - {perso.arme}) - {perso.pv}/{perso.pv_max} PV")
        while True:
            try:
                choix = input("Votre choix : ")
                choix = int(choix)
                if 1 <= choix <= len(cibles):
                    return cibles[choix - 1]
                else:
                    print(f"Veuillez entrer un nombre entre 1 et {len(cibles)}")
            except ValueError:
                print("Veuillez entrer un nombre valide")

    def tour_de_jeu(self):
        self.afficher_etat()
        personnage = self.choisir_personnage()
        if not personnage:
            print("Pas de personnage disponible.")
            return
        action = self.choisir_action(personnage)
        cible = self.choisir_cible(action)
        if not cible:
            print("Aucune cible disponible.")
            return
        clear_screen()
        self.afficher_etat()
        resultat = action(cible, self)
        print("\nRésultat de l’action:")
        print(resultat)
        SauvegardeJeu.sauvegarder(self)
        input("\nAppuyez sur Entrée pour continuer...")
        self.changer_tour()

    def est_termine(self):
        return not self.equipe1.est_vivante() or not self.equipe2.est_vivante()

    def afficher_vainqueur(self):
        if not self.equipe1.est_vivante():
            vainqueur = self.equipe2.nom
        else:
            vainqueur = self.equipe1.nom
        print(f"\n{'='*50}")
        print(f"L'équipe {vainqueur} a gagné en {self.tour_actuel} tours sur la carte {self.map} !")
        print(f"{'='*50}")
        print("\n=== Statistiques de la partie ===")
        print(f"Nombre de tours joués : {self.tour_actuel}")
        print(f"\nÉquipe {self.equipe1.nom}:")
        print(f"  Dégâts infligés : {self.stats['equipe1']['degats_infliges']} PV")
        print(f"  Soins effectués : {self.stats['equipe1']['soins_effectues']} PV")
        print(f"  Personnages perdus : {self.stats['equipe1']['morts']}")
        print(f"  Personnages vivants : {len(self.equipe1.membres_vivants())}")
        print(f"\nÉquipe {self.equipe2.nom}:")
        print(f"  Dégâts infligés : {self.stats['equipe2']['degats_infliges']} PV")
        print(f"  Soins effectués : {self.stats['equipe2']['soins_effectues']} PV")
        print(f"  Personnages perdus : {self.stats['equipe2']['morts']}")
        print(f"  Personnages vivants : {len(self.equipe2.membres_vivants())}")
        print(f"{'='*50}")
        choix = input("\nVoulez-vous recommencer une partie ? (O/N): ").strip()
        if choix.upper() == 'O':
            print("Retour au menu de sélection du mode...")
            return LocalGameModePanel()
        else:
            print("Merci d'avoir joué !")
            return False

class SauvegardeJeu:
    FICHIER_SAUVEGARDE = "saves/sauvegarde_jeu.json"

    @staticmethod
    def sauvegarder(jeu):
        os.makedirs(os.path.dirname(SauvegardeJeu.FICHIER_SAUVEGARDE), exist_ok=True)
        with open(SauvegardeJeu.FICHIER_SAUVEGARDE, 'w', encoding='utf-8') as f:
            json.dump(jeu.to_dict(), f, indent=4)
        print("💾 Sauvegarde effectuée.")

    @staticmethod
    def charger():
        try:
            with open(SauvegardeJeu.FICHIER_SAUVEGARDE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print("✅ Sauvegarde chargée avec succès.")
            return Jeu.from_dict(data)
        except FileNotFoundError:
            print("❌ Aucun fichier de sauvegarde trouvé.")
            return None

def nouvelle_partie_locale():
    return LocalGameModePanel()

def nouvelle_partie_en_ligne():
    return OnlineGameModePanel()

def ouvrir_load_game():
    return LoadGamePanel()

def ouvrir_options():
    return SettingsPanel()

def quitter_jeu():
    settings_panel = SettingsPanel()
    save_settings({
        "music_volume": settings_panel.music_volume,
        "hover_volume": settings_panel.hover_volume,
        "click_volume": settings_panel.click_volume,
        "fullscreen": settings_panel.fullscreen
    })
    sys.exit()

def display_main_menu(selected_option):
    print("\n=== LES ASSISTÉS ===")
    print("Un combat stratégique au tour par tour\n")
    options = [
        "Nouvelle partie locale",
        "Nouvelle partie en ligne",
        "Charger une partie",
        "Options",
        "Quitter"
    ]
    for i, option in enumerate(options):
        prefix = "> " if i == selected_option else "  "
        print(f"{prefix}{i + 1}. {option}")
    print("\nUtilisez les touches 1-5 pour sélectionner une option.")

def main():
    random.seed(time.time())
    settings_panel = SettingsPanel()
    selected_option = 0
    current_panel = None

    while True:
        if current_panel is None:
            display_main_menu(selected_option)
            choice = input("Entrez votre choix (1-5) : ").strip()
            try:
                choice = int(choice)
                if 1 <= choice <= 5:
                    selected_option = choice - 1
                    if choice == 1:
                        current_panel = nouvelle_partie_locale()
                    elif choice == 2:
                        current_panel = nouvelle_partie_en_ligne()
                    elif choice == 3:
                        current_panel = ouvrir_load_game()
                    elif choice == 4:
                        current_panel = ouvrir_options()
                    elif choice == 5:
                        quitter_jeu()
                else:
                    print("Choix invalide. Veuillez entrer un numéro entre 1 et 5.")
            except ValueError:
                print("Entrée invalide. Veuillez entrer un numéro.")
        else:
            current_panel.display()
            if isinstance(current_panel, GamePanel) and current_panel.jeu and current_panel.jeu.est_termine():
                result = current_panel.handle_input(None)
                if result is not True:
                    current_panel = result
            else:
                prompt = getattr(current_panel, 'input_prompt', "Entrez votre choix : ")
                choice = input(prompt).strip()
                result = current_panel.handle_input(choice)
                if result is not True:
                    current_panel = result

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    main()