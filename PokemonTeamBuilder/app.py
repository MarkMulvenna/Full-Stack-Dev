#region Imports
import datetime
from functools import wraps
from bson import ObjectId
from pymongo import MongoClient
from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import get_jwt_identity
import bcrypt
import jwt
from flask_cors import CORS, cross_origin
#endregion Imports

app = Flask(__name__)
CORS(app)

# region Database Information
client = MongoClient('mongodb://127.0.0.1:27017')
db = client.pokemonTeamBuilderDb
pokemon = db.Pokemon
users = db.users
blacklist = db.blacklist
teams = db.teams
moves = db.Moves

app.config['SECRET_KEY'] = 'mysecret'
# endregion Database Information

#region Helper Methods

def error_response(message, status_code):
    return make_response(jsonify({'error': message}), status_code)

def message_response(message, status_code):
    return make_response(jsonify ( { 'message' : message} ) , status_code)

def admin_required(func):
    @wraps(func)
    def admin_required_wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        print(token)
        data = jwt.decode( token, app.config['SECRET_KEY'] , algorithms=['HS256'])
        print(data)
        if data['admin']:
            return func(*args, **kwargs)
        else:
            return error_response('Admin acesss is required.' , 401)
    
    return admin_required_wrapper

def is_admin(user):
    return bool(user.get('is_admin').lower() == 'true')

def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
            print(token)
        if not token:
            return message_response('Token is missing', 401)
        print(app.config['SECRET_KEY'])
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return func(*args, **kwargs)
    return jwt_required_wrapper



def can_perform_operation(user_id, target_user_id, item_type, field_type, target_id):
    if user_id is not None:
        requester = users.get(user_id)
        target_user = users.get(target_user_id)

        if is_admin(requester):
            return True

        if user_id == target_user_id:
            target_collection = target_user.get(item_type, [])
            found_item = next((item for item in target_collection if item.get(field_type) == target_id), None)
            if found_item is not None:
                return True

    return False


#endregion 

#region Flask Routes

#region Pokemon Routes
@app.route('/api/v1.0/pokemon', methods=['GET'])
def show_all_pokemon():
    page_num, page_size = 1, 12
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = (page_size * (page_num - 1))

    order_by = request.args.get('order_by')
    if order_by:
        if order_by == 'pokedex_number':
            all_pokemon = list(pokemon.find().sort('pokedex_number', 1))
        elif order_by == 'name':
            all_pokemon = list(pokemon.find().sort('name', 1))
        else:
            all_pokemon = list(pokemon.find())
    else:
        all_pokemon = list(pokemon.find())


    all_pokemon = all_pokemon[page_start:page_start + page_size]

    for pokemon_item in all_pokemon:
        pokemon_item['_id'] = str(pokemon_item['_id'])
        for ability in pokemon_item['abilities']:
            ability['_id'] = str(ability['_id'])
        for moves in pokemon_item['moves']:
            moves['_id'] = str(moves['_id'])
        # for stats in pokemon_item['stats']:
        #     stats['_id'] = str(stats['_id'])

    return make_response(jsonify(all_pokemon), 200)

@app.route('/api/v1.0/pokemon/<string:id>' , methods=['GET'])
def show_one_pokemon(id):
    pokemon_item = pokemon.find_one( { '_id' : ObjectId(id) } )
    if pokemon_item is not None:
        pokemon_item['_id'] = str(pokemon_item['_id'])
        for ability in pokemon_item['abilities']:
            ability['_id'] = str(ability['_id'])
        for moves in pokemon_item['moves']:
            moves['_id'] = str(moves['_id'])
        for stats in pokemon_item['stats']:
            stats['_id'] = str(stats['_id'])
        return make_response( jsonify( pokemon_item ) , 200 )
    else:
        return make_response( jsonify( { 'error' : 'Invalid Pokemon Id'}) , 404 )

        
@app.route('/api/v1.0/pokemon', methods=['POST'])
@jwt_required
@admin_required
def add_new_pokemon():
    if 'name' in request.form and 'type' in request.form and 'pokedex_order' in request.form:
        types = request.form['type'].split('/')
        
        new_pokemon = {
            'name': request.form['name'],
            'type': types,
            'pokedex_order': request.form['pokedex_order'],
            'abilities': [],
            'moves': [],
            'stats': []
        }

        new_pokemon_id = pokemon.insert_one(new_pokemon)
        new_pokemon_link = 'http://localhost:5000/api/v1.0/pokemon/' + str(new_pokemon_id.inserted_id)

        return make_response(jsonify({'url': new_pokemon_link}), 201)
    else:
        return make_response(jsonify({'error': 'Missing form data'}), 404)
        
@app.route('/api/v1.0/pokemon/<pokemon_id>', methods=['PUT'])
@jwt_required
@admin_required
def edit_pokemon(pokemon_id):
    if 'name' in request.form and 'type' in request.form and 'pokedex_order' in request.form:
        types = request.form['type'].split('/')
        
        updated_pokemon = {
            'name': request.form['name'],
            'type': types,
            'pokedex_order': request.form['pokedex_order']
        }

        result = pokemon.update_one({'_id': ObjectId(pokemon_id)}, {'$set': updated_pokemon})

        if result.modified_count > 0:
            return make_response(jsonify({'message': 'Pokemon updated successfully'}), 200)
        else:
            return make_response(jsonify({'error': 'Pokemon not found'}), 404)
    else:
        return make_response(jsonify({'error': 'Missing form data'}), 400)
    
@app.route('/api/v1.0/pokemon/<string:id>', methods=['DELETE'])
@jwt_required
@admin_required
def delete_pokemon(id):
    result = pokemon.delete_one( { '_id' : ObjectId(id) } )
    if result.deleted_count == 1:
        return make_response(jsonify( {} ) , 204)
    else:
        return make_response( jsonify( { 'error' : 'Invalid Pokemon Id'} ) , 404)

#endregion Pokemon Routes

#region Stat Routes
@app.route('/api/v1.0/pokemon/<string:id>/stats', methods=['GET'])
def fetch_all_stats(id):
    data_to_return = []
    pokemon_item = pokemon.find_one(
        {'_id': ObjectId(id)},
        {'stats': 1, '_id': 0}
    )
    if pokemon_item:
        for stat in pokemon_item.get('stats', []):
            stat['_id'] = str(stat.get('_id'))
            data_to_return.append(stat)
        return make_response(jsonify(data_to_return), 200)
    else:
        return make_response(jsonify({'error': 'Pokemon not found'}), 404)

@app.route('/api/v1.0/pokemon/<string:id>/stats/<stat_id>', methods=['GET'])
def fetch_one_stat(id, stat_id):
    pokemon_item = pokemon.find_one(
        {'stats._id': ObjectId(stat_id)},
        {'_id': 0, 'stats.$': 1}
    )
    if pokemon_item:
        stat = pokemon_item.get('stats', [])[0]
        stat['_id'] = str(stat.get('_id'))
        return make_response(jsonify(stat), 200)
    else:
        return make_response(jsonify({'error': 'Invalid Stat Id'}), 404)

@app.route('/api/v1.0/pokemon/<string:id>/stats', methods=['POST'])
def add_new_stat(id):
    new_stats = {
        "_id"       : ObjectId(),
        "hp"        : request.form.get('hp'),
        "attack"    : request.form.get('attack'),
        "defense"   : request.form.get('defense'),
        "speed"     : request.form.get('speed')
    }
    pokemon.update_one(
        {'_id': ObjectId(id)},
        {'$push': {'stats': new_stats}}
    )
    new_stats_link = "https://localhost:5000/api/v1.0/pokemon/" + id + "/stats/" + str(new_stats["_id"])
    return make_response(jsonify({'url': new_stats_link}), 201)



@app.route('/api/v1.0/pokemon/<string:id>/stats/<stat_id>', methods=['PUT'])
def edit_stat(id, stat_id):
    edited_stats = {
        'stats.$.hp': request.form.get('hp'),
        'stats.$.attack': request.form.get('attack'),
        'stats.$.defense': request.form.get('defense'),
        'stats.$.speed': request.form.get('speed')
    }
    pokemon.update_one(
        {'stats._id': ObjectId(stat_id)},
        {'$set': edited_stats}
    )
    edited_stats_link = "https://localhost:5000/api/v1.0/pokemon/" + id + "/stats/" + str(edited_stats["_id"])
    return make_response(jsonify({'url': edited_stats_link}), 200)

@app.route('/api/v1.0/pokemon/<string:id>/stats/<stat_id>', methods=['DELETE'])
def delete_stat(id, stat_id):
    pokemon.update_one(
        {'_id': ObjectId(id)},
        {'$pull': {'stats': {'_id': ObjectId(stat_id)}}}
    )
    return make_response(jsonify({}), 204)

#endregion Stat Routes

#region Move Routes

@app.route('/api/v1.0/moves', methods=["GET"])
def show_all_moves():
    page_num, page_size = 1,10
    if request.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = (page_size * (page_num - 1))

    order_by = request.args.get('order_by')
    if order_by:
        if order_by == 'power':
            all_moves = list(moves.find().sort('power' , 1))
    else:
        all_moves = list(moves.find())
    
    all_moves = all_moves[page_start: page_num + page_size]

    for move in all_moves:
        move['_id'] = str(move['_id'])

    return message_response( all_moves , 200)

@app.route('/api/v1.0/moves/<string:id>' , methods=['GET'])
def show_one_move(id):
    move = moves.find_one( { '_id' : ObjectId(id) } )
    if move is not None:
        move['_id'] = str(move['_id'])
        return message_response(move, 200)
    else:
        return error_response('Invalid Move Id' , 404)


@app.route('/api/v1.0/moves/' , methods=['POST'])
@jwt_required
@admin_required
def add_new_move():
    if 'name' in request.form and 'type' in request.form and 'power' in request.form and 'description' in request.form:
        new_move = {
            'name' : request.form['name'],
            'type' : request.form['type'],
            'power' : request.form['power'],
            'description' : request.form['description']
        }

        new_move_id = moves.insert_one(new_move)
        new_move_link = 'http://localhost:5000/api/v1.0/moves/' + str(new_move_id.inserted_id)

        return make_response(jsonify( { 'url' : new_move_link}) , 201)
    else:
        return error_response('Missing form data', 404)
        
@app.route('/api/v1.0/moves/<move_id>', methods=['PUT'])
@jwt_required
@admin_required
def edit_move(move_id):
    if 'name' in request.form and 'type' in request.form and 'power' in request.form and 'description' in request.form:
        updated_move = {
            'name' : request.form('name'),
            'type' : request.form['type'],
            'power' : request.form['power'],
            'description' : request.form['description']
        }

        result = moves.update_one( { '_id'  : ObjectId(move_id)} , {'$set' : updated_move})

        if result.modified_count > 0:
            return message_response('Move updated successfully.' , 200)
        else:
            return error_response('Pokemon not found' , 404)
    else:
        return error_response('Missing form data' , 400)
        



#endregion Move Routes

#region Authentication and Generic Site Routes

@app.route('/api/v1.0/login', methods=['GET'])
def login():
    auth = request.authorization
    if auth:
        user = users.find_one( { "username" : auth.username } )
        if user is not None:
            if bcrypt.checkpw(bytes( auth.password, 'UTF-8' ), user["password"] ):
                is_staff = user.get('is_staff', False)
                token = jwt.encode( {
                    'user' : auth.username,
                    'admin' : is_staff,
                    'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
                }, app.config['SECRET_KEY'])
                print(token)
                return make_response( jsonify( { 'token' : token } ) , 200)
            else:
                return message_response('Bad Password' , 401)
        else:
            return message_response('Bad Username' , 401)
    return message_response('Authentication Required' , 401)







@app.route('/api/v1.0.logout', methods=['GET'])
@jwt_required
def logout():
    token = request.headers['x-access-token']
    blacklist.insert_one( { 'token' : token })
    return make_response( jsonify( { 'message' : 'Logout Successful' } ) , 200)

    
#endregion Authentication and Generic Site Routes      

#region User Routes

#region User Routes - Generic  

@app.route('/api/v1.0/users/<user_id>', methods=['GET'])
def get_user(user_id):
    user = users.find_one({'_id': ObjectId(user_id)})

    if user:
        user['_id'] = str(user['_id'])
        return jsonify({'user': user})
    else:
        return make_response(jsonify({'error': 'User not found'}), 404)

@app.route('/api/v1.0/users', methods=['GET'])
@jwt_required
@admin_required
def get_all_users():
    all_users = users.find()
    users_list = []
    for user in all_users:
        user['_id'] = str(user['_id'])

        user_data = {
            'username': user['username'],
            'email': user['email'],
            'full_name': user['full_name'],
            'birth_date': user['birth_date'],
            'registration_date': user['registration_date'],
            'is_staff': user['is_staff']
        }

        users_list.append(user_data)

    return jsonify({'users': users_list})



@app.route('/api/v1.0/users', methods=['POST'])
def create_user():
    if 'username' in request.form and 'email' in request.form and 'password' in request.form:
        user_data = {
            'username': request.form['username'],
            'email': request.form['email'],
            'password': request.form['password'],
            'registration_date': str(datetime.date.today),
            'is_staff' : False 
        }

        user_id = users.insert_one(user_data).inserted_id
        user_url = f'http://localhost:5000/api/v1.0/users/{str(user_id)}'

        return make_response(jsonify({'url': user_url}), 201)
    else:
        return error_response('Missing Form Data', 400)

@app.route('/api/v1.0/users/<user_id>', methods=['PUT'])
def edit_user(user_id):
    user_data = request.json
    if not user_data:
        return make_response(jsonify({'error': 'Invalid request data'}), 400)

    existing_user = users.find_one({'_id': ObjectId(user_id)})
    if not existing_user:
        return make_response(jsonify({'error': 'User not found'}), 404)
    
    existing_user['email'] = user_data.get('email', existing_user['email'])
    existing_user['password'] = user_data.get('password', existing_user['password'])

    users.update_one({'_id': ObjectId(user_id)}, {'$set': existing_user})

    return make_response(jsonify({'message': 'User updated successfully'}), 200)

@app.route('/api/v1.0/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    existing_user = users.find_one({'_id': ObjectId(user_id)})
    if not existing_user:
        return make_response(jsonify({'error': 'User not found'}), 404)

    users.delete_one({'_id': ObjectId(user_id)})

    return make_response(jsonify({'message': 'User deleted successfully'}), 200)

@app.route('/api/v1.0/users/<user_id>' , methods=['PUT'])
@jwt_required
@admin_required
def set_staff(user_id):
    if 'is_staff' in request.form:
        user = users.find_one({ '_id' : ObjectId(user_id) } )

        if not user:
            return error_response('User not found' , 404)
        users.update_one(
            {'_id' : ObjectId(user_id)},
            {'$set': {'is_staff' : request.form['is_staff']}}
        )

        return message_response('Users staff status updated successfully.')
    return error_response('Missing form data' , 400)


#endregion User Routes - Generic

#region User - Team Routes

@app.route('/api/v1.0/users/<user_id>/teams', methods=['GET'])
def get_user_teams(user_id):
    user = users.get(user_id)
    if user is not None:
        teams = user.get('teams', [])
        return jsonify({'teams': teams}), 200
    else:
        return make_response(jsonify({'error': 'User not found'}), 404)
app.route('/api/v1.0/users/<user_id>/teams', methods=['GET'])
def get_user_teams(user_id):
    user = users.get(user_id)
    if user is not None:
        teams = user.get('teams', [])
        return jsonify({'teams': teams}), 200
    else:
        return make_response(jsonify({'error': 'User not found'}), 404)

@app.route('/api/v1.0/users/<user_id>/teams/<team_id>', methods=['PUT'])
@jwt_required
def edit_user_team(user_id, team_id):
    user = users.get(user_id)
    if user is not None:
        teams = user.get('teams', [])

        team_to_edit = next((team for team in teams if team['id'] == team_id), None)

        if team_to_edit:
            team_to_edit.update(request.json)
            return jsonify({'message': 'Team updated successfully'}), 200
        else:
            return make_response(jsonify({'error': 'Team not found'}), 404)
    else:
        return make_response(jsonify({'error': 'User not found'}), 404)

@app.route('/api/v1.0/users/<user_id>/teams', methods=['POST'])
@jwt_required
def add_user_team(user_id):
    if 'pokemon' in request.form:
        pokemon_ids = request.form['pokemon'].split(',') 
        
        current_user_id = get_jwt_identity() 
        
        if can_perform_operation(current_user_id, user_id, 'users', 'id', user_id):
            user = users.get(user_id)  
            if user:
                new_team = {
                    "_id": ObjectId(),
                    "pokemon": pokemon_ids,  
                    "user": user_id
                }
                
                new_team_id = teams.insert_one(new_team)
                new_team_link = 'http://localhost:5000/api/v1.0/teams/' + str(new_team_id.inserted_id)
    
                return make_response(jsonify({'url': new_team_link}), 201)
            else:
                return make_response(jsonify({'error': 'User not found'}), 404)
        else:
            return make_response(jsonify({'error': 'Unauthorized to add team for this user'}), 401)
    else:
        return make_response(jsonify({'error': 'Missing or invalid Pokemon data'}), 400)


@app.route('/api/v1.0/users/<user_id>/teams/<team_id>', methods=['DELETE'])
@jwt_required
def delete_user_team(user_id, team_id):
    user = users.get(user_id)
    if user is not None:
        teams = user.get('teams', [])

        team_to_delete = next((team for team in teams if team['id'] == team_id), None)

        if team_to_delete:
            teams.remove(team_to_delete)
            user['teams'] = teams
            return jsonify({'message': 'Team deleted successfully'}), 200
        else:
            return make_response(jsonify({'error': 'Team not found'}), 404)
    else:
        return make_response(jsonify({'error': 'User not found'}), 404)

#endregion User - Team Routes

#endregion User Routes

#endregion Flask Routes

if __name__ == '__main__':
    app.run(debug=True)


