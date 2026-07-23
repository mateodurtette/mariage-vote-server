import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

CLOUD_SERVER_URL = "https://mariage-dj-vote.onrender.com"  # L'URL de ton serveur en ligne

SPOTIPY_CLIENT_ID = "a0a55f8c047f44f9a58dbd4e0715553a"
SPOTIPY_CLIENT_SECRET = "32de8e9ad70f43e0bdf409ee6be52532"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8000/callback"

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotify_token_cache"
))

print("🎧 Agent DJ Démarré et connecté à Spotify !")

last_track_id = None

while True:
    try:
        playback = sp.current_playback()
        if playback and playback.get("item"):
            item = playback["item"]
            track_id = item["id"]
            title = item["name"]
            artist = item["artists"][0]["name"]
            cover = item["album"]["images"][0]["url"] if item["album"]["images"] else ""

            # 1. Envoyer le morceau en cours au serveur Cloud s'il a changé
            if track_id != last_track_id:
                requests.post(f"{CLOUD_SERVER_URL}/api/update-track", json={
                    "title": title,
                    "artist": artist,
                    "cover": cover,
                    "track_id": track_id
                })
                last_track_id = track_id
                print(f"🎵 Morceau actuel synchronisé : {title} - {artist}")

            # 2. Récupérer les votes depuis le serveur Cloud
            res = requests.get(f"{CLOUD_SERVER_URL}/api/get-votes").json()
            upvotes = res["upvotes"]
            downvotes = res["downvotes"]

            # RÈGLE DU SKIP : Si (Contre - Pour) >= 5, on passe au morceau suivant
            if (downvotes - upvotes) >= 5:
                print(f"⛔ Seuil de rejet atteint ({downvotes} contre / {upvotes} pour). Passage au titre suivant !")
                sp.next_track()
                time.sleep(2) # Pause de sécurité

    except Exception as e:
        print(f"Attention : {e}")

    time.sleep(3) # Vérification toutes les 3 secondes