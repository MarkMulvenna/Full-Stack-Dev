#region Imports
import datetime
from functools import wraps
from bson import ObjectId
from pymongo import MongoClient
from flask import Flask, request, jsonify, make_response
import bcrypt
import jwt
#endregion Imports

app = Flask(__name__)

# region Database Information
client = MongoClient("mongodb://127.0.0.1:27017")
db = client.pokemonTeamBuilderDb
pokemon = db.Pokemon
users = db.users
# endregion Database Information

#region Helper Methods

def admin_required(func):
    @wraps(func)
    def admin_required_wrapper(*args, **kwargs):
        token = request.headers['x-access-token']
        data = jwt.decode( token, app.config['SECRET-KEY'] )
        if data["admin"]:
            return func(*args, **kwargs)
        else:
            return make_response( jsonify( { 'message' : 'Admin Access is required. '}), 401 )
    
    return admin_required_wrapper

def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify( { 'message' : 'Token is missing' } ), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify( { 'message' : 'Token is invalid' } ), 401
        return(func(*args, *kwargs))
    return jwt_required_wrapper
#endregion


#region Flask Routes
app = Flask(__name__)

@app.route("/api/v1.0/pokemon", methods=["GET"])
@jwt_required
def show_all_pokemon():
    page_num, page_size = 1, 10
    if request.args.get("pn"):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = (page_size * (page_num - 1))

    order_by = request.args.get("order_by")
    if order_by:
        if order_by == "pokedex_order":
            all_pokemon = list(pokemon.find().sort("pokedex_order", 1))
        elif order_by == "name":
            all_pokemon = list(pokemon.find().sort("name", 1))
        else:
            all_pokemon = list(pokemon.find())
    else:
        all_pokemon = list(pokemon.find())


    all_pokemon = all_pokemon[page_start:page_start + page_size]

    for pokemon_item in all_pokemon:
        pokemon_item["_id"] = str(pokemon_item["_id"])
        for ability in pokemon_item["abilities"]:
            ability["_id"] = str(ability["_id"])
        for moves in pokemon_item["moves"]:
            moves["_id"] = str(moves["_id"])
        for stats in pokemon_item["stats"]:
            stats["_id"] = str(stats["_id"])

    return make_response(jsonify(all_pokemon), 200)

@app.route("/api/v1.0/pokemon/<string:id>" , methods=["GET"])
def show_one_pokemon(id):
    pokemon_item = pokemon.find_one( { "_id" : ObjectId(id) } )
    if pokemon_item is not None:
        pokemon_item["_id"] = str(pokemon_item["_id"])
        for ability in pokemon_item["abilities"]:
            ability["_id"] = str(ability["_id"])
        for moves in pokemon_item["moves"]:
            moves["_id"] = str(moves["_id"])
        for stats in pokemon_item["stats"]:
            stats["_id"] = str(stats["_id"])
        return make_response( jsonify( pokemon_item ) , 200 )
    else:
        return make_response( jsonify( { "error" : "Invalid Pokemon Id"}) , 400 )

        
@app.route("/api/v1.0/pokemon", methods=["POST"])
def add_new_pokemon():
    if "name" in request.form and "type" in request.form and "pokedex_order" in request.form:
        new_pokemon = {
        "name" : request.form["name"],
        "type" : request.form["type"],
        "pokedex_order" : request.form["pokedex_order"],
        "abilities" : [],
        "moves" : [],
        "stats" : [] 
        }
        new_pokemon_id = pokemon.insert_one(new_pokemon)
        new_pokemon_link = "http://localhost:5000/api/v1.0/pokemon/" + str(new_pokemon_id.inserted_id)

        return make_response( jsonify({ "url" : new_pokemon_link} ), 201)
    else:
        return make_response( jsonify( { "error" : "Missing form data" } ), 404)
        
@app.route("/api/v1.0/pokemon/<string:id>", methods=["DELETE"])
def delete_pokemon(id):
    result = pokemon.delete_one( { "_id" : ObjectId(id) } )
    if result.deleted_count == 1:
        return make_response(jsonify( {} ) , 204)
    else:
        return make_response( jsonify( { "error" : "Invalid Pokemon Id"} ) , 404)

@app.route('/api/v1.0/pokemon/<string:id>', methods=['PATCH'])
def edit_pokemon(id):
    if "name" in request.form and "type" in request.form and "pokedex_order" in request.form:
        result = pokemon.update_one(
            { "_id" : ObjectId(id) },
            {
                "$set" : {
                    "name" : request.form["name"],
                    "type" : request.form["type"],
                    "pokedex_order" : request.form["pokedex_order"]
                }
            }
        )
        if result.modified_count == 1:
            edited_pokemon_link = "http://localhost:5000/api/v1.0/pokemon/" + id
            return make_response(jsonify( { "url" : edited_pokemon_link }), 201)
        else: 
            return make_response( jsonify( { "error" : "Invalid Pokemon ID" } ), 404)
    else:
        return make_response( jsonify( { "error" : "Missing form data" } ), 404)


@app.route("/api/v1.0/pokemon/<string:id>/stats", methods=["POST"])
def add_new_stat(id):
    new_stats = {
        "_id": ObjectId(),
        "hp": request.form.get("hp"),
        "attack": request.form.get("attack"),
        "defense": request.form.get("defense"),
        "speed": request.form.get("speed")
    }
    pokemon.update_one(
        {"_id": ObjectId(id)},
        {"$push": {"stats": new_stats}}
    )
    new_stats_link = url_for('fetch_one_stat', id=id, stat_id=str(new_stats["_id"]), _external=True)
    return make_response(jsonify({"url": new_stats_link}), 201)

@app.route("/api/v1.0/pokemon/<string:id>/stats", methods=["GET"])
def fetch_all_stats(id):
    data_to_return = []
    pokemon_item = pokemon.find_one(
        {"_id": ObjectId(id)},
        {"stats": 1, "_id": 0}
    )
    if pokemon_item:
        for stat in pokemon_item.get("stats", []):
            stat["_id"] = str(stat.get("_id"))
            data_to_return.append(stat)
        return make_response(jsonify(data_to_return), 200)
    else:
        return make_response(jsonify({"error": "Pokemon not found"}), 404)

@app.route("/api/v1.0/pokemon/<string:id>/stats/<stat_id>", methods=["GET"])
def fetch_one_stat(id, stat_id):
    pokemon_item = pokemon.find_one(
        {"stats._id": ObjectId(stat_id)},
        {"_id": 0, "stats.$": 1}
    )
    if pokemon_item:
        stat = pokemon_item.get("stats", [])[0]
        stat["_id"] = str(stat.get("_id"))
        return make_response(jsonify(stat), 200)
    else:
        return make_response(jsonify({"error": "Invalid Stat Id"}), 404)

@app.route("/api/v1.0/pokemon/<string:id>/stats/<stat_id>", methods=["PUT"])
def edit_stat(id, stat_id):
    edited_stats = {
        "stats.$.hp": request.form.get("hp"),
        "stats.$.attack": request.form.get("attack"),
        "stats.$.defense": request.form.get("defense"),
        "stats.$.speed": request.form.get("speed")
    }
    pokemon.update_one(
        {"stats._id": ObjectId(stat_id)},
        {"$set": edited_stats}
    )
    edit_stats_url = url_for('fetch_one_stat', id=id, stat_id=stat_id, _external=True)
    return make_response(jsonify({"url": edit_stats_url}), 200)

@app.route("/api/v1.0/pokemon/<string:id>/stats/<stat_id>", methods=["DELETE"])
def delete_stat(id, stat_id):
    pokemon.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"stats": {"_id": ObjectId(stat_id)}}}
    )
    return make_response(jsonify({}), 204)


@app.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if auth:
        user = user.find_one( { "username" : auth.username })
        if user is not None:
            if bcrypt.checkpw( bytes(auth.password, 'UTF-8'), user["password"] ):
                token = jwt.encode( {
                    'user' : auth.username, 
                    'admin' : user["is_staff"],
                    'exp' : datetime.datetime.utcnow() + datetime.timedelta( minutes = 60 )
                }, app.config['SECRET_KEY'])
                return jsonify( { 'token' : token.decode('UTF-8') }, 200 )
            else:
                return make_response( jsonify( { 'message' : 'Bad password' } ) , 401 )
        else:
            return make_response( jsonify ( { 'message' : 'Bad Username' } ) , 401)
    return make_response( jsonify ( { 'message' : 'Authentication Required' } ) , 401)
    

        
if __name__ == "__main__":
    app.run(debug=True)

#endregion Flask Routes


