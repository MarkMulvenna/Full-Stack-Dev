from datetime import datetime
from faker import Faker
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://127.0.0.1:27017")
db = client.pokemonTeamBuilderDb
users = db.users

fake = Faker()

dummy_users = []

for _ in range(10):
    user = {
        "username": fake.user_name(),
        "email": fake.email(),
        "full_name": fake.name(),
        "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=65).isoformat(),
        "registration_date": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
        "is_staff": fake.boolean(),
    }
    dummy_users.append(user)

result = users.insert_many(dummy_users)

print(f"Inserted {len(result.inserted_ids)} dummy users into the database.")