import os
from app.data.hotels import get_firestore_client

def inspect_hotel_cache():
    """Prints all documents in the hotel-cache collection."""
    db = get_firestore_client()
    if not db:
        print("Error: Could not connect to Firestore. Ensure GOOGLE_APPLICATION_CREDENTIALS is set.")
        return

    collection_name = "hotel-cache"
    print(f"--- Fetching documents from '{collection_name}' in {db.project} ---\n")

    docs = db.collection(collection_name).stream()
    count = 0
    for doc in docs:
        count += 1
        print(f"Key: {doc.id}")
        print(f"Data: {doc.to_dict()}\n")
    
    print(f"Total documents found: {count}")

if __name__ == "__main__":
    inspect_hotel_cache()