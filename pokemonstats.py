import requests
import json

##api call to hook in to pokeapi data to generate a custom dataset, utility file only delete from final submission.

def fetch_pokemon_data():
    pokemon_data = []
    for i in range(1, 101):
        url = f"https://pokeapi.co/api/v2/pokemon/{i}"
        response = requests.get(url)
        if response.status_code == 200:
            pokemon = response.json()
            data = {
                "name": pokemon['name'],
                "types": [t['type']['name'] for t in pokemon['types']],
                "pokedex_number": pokemon['id'],
                "abilities": [],
                "moves": [],
                "stats": {
                    "hp": next(stat['base_stat'] for stat in pokemon['stats'] if stat['stat']['name'] == 'hp'),
                    "attack": next(stat['base_stat'] for stat in pokemon['stats'] if stat['stat']['name'] == 'attack'),
                    "defense": next(stat['base_stat'] for stat in pokemon['stats'] if stat['stat']['name'] == 'defense'),
                    "speed": next(stat['base_stat'] for stat in pokemon['stats'] if stat['stat']['name'] == 'speed')
                }
            }
            pokemon_data.append(data)
        else:
            print(f"Failed to fetch data for Pokémon {i}")

    with open('pokemon_data.json', 'w') as file:
        json.dump(pokemon_data, file, indent=4)

    # Load the pokemon_data from the file
    with open('pokemon_data.json', 'r') as file:
        pokemon_data = json.load(file)

    # Capitalize the first letter of the "Name" value
    for pokemon in pokemon_data:
        pokemon["name"] = pokemon["name"].capitalize()

    # Save the modified pokemon_data back to the file
    with open('pokemon_data.json', 'w') as file:
        json.dump(pokemon_data, file, indent=4)
    

fetch_pokemon_data()
print("Done!")