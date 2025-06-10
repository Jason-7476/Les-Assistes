from flask import Flask, request, jsonify
import uuid
import random

app = Flask(__name__)

# Stockage des parties en mémoire
games = {}

# Liste des cartes disponibles
MAPS = [
    "Hôpital Sainte Dérive",
    "Carrefour Saint-Sever",
    "Quartier Yvetot",
    "Restaurant Flunch"
]

@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    if not data or 'player_id' not in data:
        return jsonify({'error': 'player_id requis'}), 400
    
    game_id = str(uuid.uuid4())[:8]
    games[game_id] = {
        'status': 'waiting_player2',
        'player1_id': data['player_id'],
        'player2_id': None,
        'equipe1': None,
        'equipe2': None,
        'tour_actuel': 1,
        'equipe_active_nom': None,
        'map': None,
        'stats': {
            data['player_id']: {'degats_infliges': 0, 'soins_effectues': 0, 'morts': 0},
            'equipe2': {'degats_infliges': 0, 'soins_effectues': 0, 'morts': 0}
        }
    }
    return jsonify({'game_id': game_id})

@app.route('/join_game', methods=['POST'])
def join_game():
    data = request.json
    if not data or 'game_id' not in data or 'player_id' not in data:
        return jsonify({'error': 'game_id et player_id requis'}), 400
    
    game_id = data['game_id']
    if game_id not in games:
        return jsonify({'error': 'Partie non trouvée'}), 404
    if games[game_id]['player2_id']:
        return jsonify({'error': 'Partie déjà pleine'}), 400
    
    games[game_id]['player2_id'] = data['player_id']
    games[game_id]['status'] = 'waiting_teams'
    games[game_id]['stats'][data['player_id']] = {'degats_infliges': 0, 'soins_effectues': 0, 'morts': 0}
    return jsonify({'message': 'Partie rejointe avec succès'})

@app.route('/submit_team', methods=['POST'])
def submit_team():
    data = request.json
    if not data or 'game_id' not in data or 'player_id' not in data or 'equipe' not in data:
        return jsonify({'error': 'game_id, player_id et equipe requis'}), 400
    
    game_id = data['game_id']
    if game_id not in games:
        return jsonify({'error': 'Partie non trouvée'}), 404
    
    game = games[game_id]
    if data['player_id'] == game['player1_id']:
        game['equipe1'] = data['equipe']
        game['stats'][game['equipe1']['nom']] = game['stats'].pop(game['player1_id'])
    elif data['player_id'] == game['player2_id']:
        game['equipe2'] = data['equipe']
        game['stats'][game['equipe2']['nom']] = game['stats'].pop(game['player2_id'])
    else:
        return jsonify({'error': 'Joueur non autorisé'}), 403
    
    if game['equipe1'] and game['equipe2']:
        game['status'] = 'waiting_map'
        game['equipe_active_nom'] = game['equipe1']['nom']
    
    return jsonify({'message': f"Équipe {data['equipe']['nom']} soumise avec succès"})

@app.route('/submit_map', methods=['POST'])
def submit_map():
    data = request.json
    if not data or 'game_id' not in data or 'player_id' not in data or 'map' not in data:
        return jsonify({'error': 'game_id, player_id et map requis'}), 400
    
    game_id = data['game_id']
    if game_id not in games:
        return jsonify({'error': 'Partie non trouvée'}), 404
    
    game = games[game_id]
    if data['player_id'] != game['player1_id']:
        return jsonify({'error': 'Seul le joueur 1 peut choisir la carte'}), 403
    if data['map'] not in MAPS:
        return jsonify({'error': 'Carte invalide'}), 400
    
    game['map'] = data['map']
    game['status'] = 'ongoing'
    return jsonify({'message': f"Carte {data['map']} sélectionnée"})

@app.route('/game_state/<game_id>', methods=['GET'])
def get_game_state(game_id):
    if game_id not in games:
        return jsonify({'error': 'Partie non trouvée'}), 404
    return jsonify(games[game_id])

@app.route('/make_move', methods=['POST'])
def make_move():
    data = request.json
    if not data or not all(k in data for k in ['game_id', 'player_id', 'personnage_index', 'action_key', 'cible_index']):
        return jsonify({'error': 'Données incomplètes'}), 400
    
    game_id = data['game_id']
    if game_id not in games:
        return jsonify({'error': 'Partie non trouvée'}), 404
    
    game = games[game_id]
    if game['status'] != 'ongoing':
        return jsonify({'error': 'Partie non en cours'}), 400

    # Vérifier si c'est le tour du joueur
    is_player1 = data['player_id'] == game['player1_id']
    is_player1_turn = game['equipe_active_nom'] == game['equipe1']['nom']
    if (is_player1 and not is_player1_turn) or (not is_player1 and is_player1_turn):
        return jsonify({'error': 'Ce n’est pas votre tour'}), 403

    # Sélectionner l'équipe active et inactive
    equipe_active = game['equipe1'] if is_player1_turn else game['equipe2']
    equipe_inactive = game['equipe2'] if is_player1_turn else game['equipe1']

    try:
        # Vérifier les indices
        personnage_index = data['personnage_index']
        cible_index = data['cible_index']
        if not (0 <= personnage_index < len(equipe_active['personnages'])):
            return jsonify({'error': 'Index de personnage invalide'}), 400
        if not equipe_active['personnages'][personnage_index]['vivant']:
            return jsonify({'error': 'Personnage mort'}), 400

        perso = equipe_active['personnages'][personnage_index]
        action_key = data['action_key']

        # Déterminer l'équipe cible (soin -> équipe active, attaque -> équipe inactive)
        cible_equipe = equipe_active if (perso['type'] == 'Druide' and action_key == '1') else equipe_inactive
        if not (0 <= cible_index < len(cible_equipe['personnages'])):
            return jsonify({'error': 'Index de cible invalide'}), 400
        if not cible_equipe['personnages'][cible_index]['vivant'] and action_key != '1':
            return jsonify({'error': 'Cible morte'}), 400

        cible = cible_equipe['personnages'][cible_index]
        message = ""

        # Appliquer l'action
        if perso['type'] == 'Warrior':
            if action_key == '1':  # Attaque basique
                degats = random.randint(35, 50)
                cible['pv'] = max(0, cible['pv'] - degats)
                game['stats'][equipe_active['nom']]['degats_infliges'] += degats
                message = f"{perso['nom']} inflige {degats} dégâts à {cible['nom']} ({cible['pv']} PV restants)."
                if cible['pv'] <= 0:
                    cible['vivant'] = False
                    game['stats'][cible_equipe['nom']]['morts'] += 1
                    message += f" {cible['nom']} est mort !"
            elif action_key == '2':  # Attaque puissante
                degats = random.randint(45, 60)
                degats_self = random.randint(3, 8)
                cible['pv'] = max(0, cible['pv'] - degats)
                perso['pv'] = max(0, perso['pv'] - degats_self)
                game['stats'][equipe_active['nom']]['degats_infliges'] += degats
                message = f"{perso['nom']} inflige {degats} dégâts à {cible['nom']} ({cible['pv']} PV restants)."
                if cible['pv'] <= 0:
                    cible['vivant'] = False
                    game['stats'][cible_equipe['nom']]['morts'] += 1
                    message += f" {cible['nom']} est mort !"
                message += f" {perso['nom']} subit {degats_self} dégâts de contrecoup ({perso['pv']} PV restants)."
                if perso['pv'] <= 0:
                    perso['vivant'] = False
                    game['stats'][equipe_active['nom']]['morts'] += 1
                    message += f" {perso['nom']} est mort !"
            else:
                return jsonify({'error': 'Action invalide pour Warrior'}), 400
        elif perso['type'] == 'Druide':
            if action_key == '1':  # Soin puissant
                if cible['vivant']:
                    soins = random.randint(35, 55)
                    avant = cible['pv']
                    cible['pv'] = min(cible['pv_max'], cible['pv'] + soins)
                    game['stats'][equipe_active['nom']]['soins_effectues'] += (cible['pv'] - avant)
                    message = f"{perso['nom']} soigne {cible['nom']} pour {cible['pv'] - avant} PV ({cible['pv']} PV)."
                else:
                    message = f"{cible['nom']} est mort et ne peut être soigné."
            elif action_key == '2':  # Attaque naturelle
                degats = random.randint(25, 40)
                cible['pv'] = max(0, cible['pv'] - degats)
                game['stats'][equipe_active['nom']]['degats_infliges'] += degats
                message = f"{perso['nom']} inflige {degats} dégâts à {cible['nom']} ({cible['pv']} PV restants)."
                if cible['pv'] <= 0:
                    cible['vivant'] = False
                    game['stats'][cible_equipe['nom']]['morts'] += 1
                    message += f" {cible['nom']} est mort !"
            else:
                return jsonify({'error': 'Action invalide pour Druide'}), 400
        elif perso['type'] == 'Archer':
            if action_key == '1':  # Tir simple
                degats = random.randint(50, 70)
                cible['pv'] = max(0, cible['pv'] - degats)
                game['stats'][equipe_active['nom']]['degats_infliges'] += degats
                message = f"{perso['nom']} inflige {degats} dégâts à {cible['nom']} ({cible['pv']} PV restants)."
                if cible['pv'] <= 0:
                    cible['vivant'] = False
                    game['stats'][cible_equipe['nom']]['morts'] += 1
                    message += f" {cible['nom']} est mort !"
            elif action_key == '2':  # Tir précis
                critique = random.random() < 0.3
                degats = random.randint(60, 80)
                if critique:
                    degats = int(degats * 1.5)
                    message = f"🎯 CRITIQUE ! "
                cible['pv'] = max(0, cible['pv'] - degats)
                game['stats'][equipe_active['nom']]['degats_infliges'] += degats
                message += f"{perso['nom']} inflige {degats} dégâts à {cible['nom']} ({cible['pv']} PV restants)."
                if cible['pv'] <= 0:
                    cible['vivant'] = False
                    game['stats'][cible_equipe['nom']]['morts'] += 1
                    message += f" {cible['nom']} est mort !"
            else:
                return jsonify({'error': 'Action invalide pour Archer'}), 400
        else:
            return jsonify({'error': 'Type de personnage inconnu'}), 400

        # Vérifier si la partie est terminée
        equipe1_vivante = any(p['vivant'] for p in game['equipe1']['personnages'])
        equipe2_vivante = any(p['vivant'] for p in game['equipe2']['personnages'])
        if not equipe1_vivante or not equipe2_vivante:
            game['status'] = 'finished'
            return jsonify({'message': message})

        # Changer le tour
        game['tour_actuel'] += 1
        game['equipe_active_nom'] = game['equipe2']['nom'] if is_player1_turn else game['equipe1']['nom']

        return jsonify({'message': message})
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l’action : {str(e)}'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)