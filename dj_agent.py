import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

CLOUD_SERVER_URL = "https://mariage-dj-vote.onrender.com"

SPOTIPY_CLIENT_ID = "88e2ad60dd98415aab65d70f9deb9f81"
SPOTIPY_CLIENT_SECRET = "e6902111c57a46e5b8d2990208a0b0da"
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8000/callback"

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotify_token_cache"
))

print("🎧 Agent DJ - Prénom & Vote Négatif Alternatif Actifs !")

has_evaluated_track = False
last_search_query = None

while True:
    try:
        # 1. Recherche dynamique Spotify
        try:
            pending_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-pending-search").json()
            query = pending_res.get("query")
            
            if query and query != last_search_query:
                last_search_query = query
                results = sp.search(q=query, limit=4, type='track')
                tracks = []
                for item in results.get('tracks', {}).get('items', []):
                    tracks.append({
                        "title": item['name'],
                        "artist": item['artists'][0]['name'],
                        "uri": item['uri'],
                        "cover": item['album']['images'][0]['url'] if item['album']['images'] else ""
                    })
                requests.post(f"{CLOUD_SERVER_URL}/api/set-search-results", json={"results": tracks})
        except Exception:
            pass

        # 2. Lecture de l'état Spotify
        playback = sp.current_playback()
        queue_data = sp.queue()

        if playback and playback.get("item"):
            current_track = playback["item"]
            current_name = current_track["name"]
            remaining_seconds = max(0, int((current_track["duration_ms"] - playback["progress_ms"]) / 1000))

            queue_list = queue_data.get("queue", []) if queue_data else []

            if len(queue_list) > 0:
                next_track = queue_list[0]
                next_title = next_track["name"]
                next_artist = next_track["artists"][0]["name"]
                next_cover = next_track["album"]["images"][0]["url"] if next_track["album"]["images"] else ""
                next_id = next_track["id"]
            else:
                next_title = "Sélection Playlist"
                next_artist = "Spotify Auto"
                next_cover = "https://via.placeholder.com/160"
                next_id = "default_next"

            requests.post(
                f"{CLOUD_SERVER_URL}/api/update-state",
                json={
                    "current_title": current_name,
                    "current_artist": current_track["artists"][0]["name"],
                    "current_remaining_seconds": remaining_seconds,
                    "next_title": next_title,
                    "next_artist": next_artist,
                    "next_cover": next_cover,
                    "next_track_id": next_id
                }
            )

            if remaining_seconds > 45:
                has_evaluated_track = False

            # 3. ÉVALUATION À T-30s
            if remaining_seconds <= 30 and not has_evaluated_track:
                print(f"\n⏰ T-30s ! Arbitrage des votes...")
                
                state_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-state").json()
                votes = state_res.get("votes", {})
                upvotes = votes.get("upvotes", 0)
                downvotes = votes.get("downvotes", 0)
                
                suggestion = state_res.get("suggested_song")
                alt_score = suggestion.get("score", 0) if suggestion else 0
                alt_uri = suggestion.get("uri") if suggestion else None
                alt_title = suggestion.get("title") if suggestion else None
                proposer = suggestion.get("proposer") if suggestion else "Inconnu"

                net_planned_score = upvotes - downvotes

                # Si l'alternative a un meilleur score net que le morceau prévu
                if alt_uri and alt_score > net_planned_score and alt_score > 0:
                    print(f"🎉 L'ALTERNATIVE DE '{proposer}' GAGNE ({alt_score} pts) ! Ajout de '{alt_title}'...")
                    sp.add_to_queue(alt_uri)

                elif downvotes > upvotes:
                    print(f"⛔ VETO DE LA SALLE ! Morceau prévu annulé.")
                    sp.next_track()

                else:
                    print(f"✅ MORCEAU PRÉVU CONSERVÉ : '{next_title}'")

                has_evaluated_track = True

    except Exception as e:
        print(f"❌ Erreur : {e}")

    time.sleep(4)
