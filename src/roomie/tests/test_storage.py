
from app import create_app
from app import storage


app = create_app()

with app.app_context():
    # Read the initial users list
    users = storage.read_json("users.json")
    print("Initial users:", users)

    # Write sample data
    sample_users = [
        {
            "id": "user-001",
            "username": "testuser",
            "email": "test@example.com"
        }
    ]

    storage.write_json("users.json", sample_users)

    # Read the data back
    saved_users = storage.read_json("users.json")
    print("Saved users:", saved_users)
