import os
import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Nettoyage automatique des anciens tokens au démarrage
for file in os.listdir('.'):
    if file.startswith('.cache') or file.startswith('.spotify_token'):
        try:
            os.remove(file)
            print(f"🧹 Fichier cache supprimé : {file}")
        except Exception:
            pass

CLOUD_SERVER_URL = "https://mariage-dj-vote.onrender.com"

# ⚠️ INSERE TES NOUVEAUX IDENTIFIANTS DU DASHBOARD SPOTIFY ICI
SPOTIPY_CLIENT_ID = "88e2ad60dd98415aab65d70f9deb9f81"
SPOTIPY_CLIENT_SECRET = "e6902111c57a46e5b8d2990208a0b0da"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8000/callback"

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotify_token_cache_v2"
))

print("🎧 Agent DJ - Version Optimisée Anti-Rate-Limit Active !")

has_evaluated_track = False
last_search_query = None
last_sent_state = {}

while True:
    try:
        # 1. Traitement des recherches uniquement à la demande
        try:
            pending_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-pending-search", timeout=2).json()
            query = pending_res.get("query")
            
            if query and query != last_search_query and len(query.strip()) >= 2:
                last_search_query = query
                print(f"🔍 Recherche demandée : '{query}'")
                results = sp.search(q=query, limit=4, type='track')
                tracks = []
                for item in results.get('tracks', {}).get('items', []):
                    tracks.append({
                        "title": item['name'],
                        "artist": item['artists'][0]['name'],
                        "uri": item['uri'],
                        "cover": item['album']['images'][0]['url'] if item['album']['images'] else ""
                    })
                requests.post(f"{CLOUD_SERVER_URL}/api/set-search-results", json={"results": tracks}, timeout=2)
        except Exception:
            pass

        # 2. Lecture de l'état Spotify
        playback = sp.current_playback()

        if playback and playback.get("item") and playback.get("is_playing"):
            current_track = playback["item"]
            current_name = current_track["name"]
            duration_ms = current_track["duration_ms"]
            progress_ms = playback["progress_ms"]
            remaining_seconds = max(0, int((duration_ms - progress_ms) / 1000))

            # Lecture de la file d'attente
            queue_data = sp.queue()
            queue_list = queue_data.get("queue", []) if queue_data else []

            if len(queue_list) > 0:
                next_track = queue_list[0]
                next_title = next_track["name"]
                next_artist = next_track["artists"][0]["name"]
                next_cover = next_track["album"]["images"][0]["url"] if next_track["album"]["images"] else ""
                next_id = next_track["id"]
            else:
                next_title = "Playlist Spotify"
                next_artist = "Sélection Auto"
                next_cover = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300"
                next_id = "default_next"

            # Envoi au serveur Web
            payload = {
                "current_title": current_name,
                "current_artist": current_track["artists"][0]["name"],
                "current_remaining_seconds": remaining_seconds,
                "next_title": next_title,
                "next_artist": next_artist,
                "next_cover": next_cover,
                "next_track_id": next_id
            }

            requests.post(f"{CLOUD_SERVER_URL}/api/update-state", json=payload, timeout=2)

            if remaining_seconds > 45:
                has_evaluated_track = False

            # Évaluation à T-30s
            if remaining_seconds <= 30 and not has_evaluated_track:
                print(f"\n⏰ T-30s ! Arbitrage des votes...")
                state_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-state", timeout=2).json()
                votes = state_res.get("votes", {})
                upvotes = votes.get("upvotes", 0)
                downvotes = votes.get("downvotes", 0)
                
                suggestion = state_res.get("suggested_song")
                alt_score = suggestion.get("votes", 0) if suggestion else 0
                alt_uri = suggestion.get("uri") if suggestion else None
                alt_title = suggestion.get("title") if suggestion else None

                net_planned_score = upvotes - downvotes

                if alt_uri and alt_score > net_planned_score and alt_score > 0:
                    print(f"🎉 L'alternative l'emporte : '{alt_title}' !")
                    sp.add_to_queue(alt_uri)
                elif downvotes > upvotes:
                    print(f"⛔ VETO ! Passage au morceau suivant...")
                    sp.next_track()
                else:
                    print(f"✅ Morceau prévu conservé : '{next_title}'")

                has_evaluated_track = True

        else:
            # Mode pause
            requests.post(
                f"{CLOUD_SERVER_URL}/api/update-state",
                json={
                    "current_title": "Musique en pause",
                    "current_artist": "Lancez une playlist sur Spotify",
                    "current_remaining_seconds": 999,
                    "next_title": "En attente...",
                    "next_artist": "",
                    "next_cover": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300",
                    "next_track_id": "paused"
                },
                timeout=2
            )

    except Exception as e:
        print(f"⚠️ Information : {e}")

    # Pause de 4 secondes pour préserver l'API Spotify
    time.sleep(4)
