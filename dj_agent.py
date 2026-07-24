import time
import requests

CLOUD_SERVER_URL = "https://mariage-dj-vote.onrender.com"

# 🔑 COLLE ICI LE TOKEN OBTENU AVEC GET_FRESH_TOKEN.PY
ACCESS_TOKEN = "PASTE_TON_TOKEN_ICI"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

print("🎧 Agent DJ - Connecté et Cadencé (Sécurité Rate Limit) !")

has_evaluated_track = False
last_search_query = None

while True:
    try:
        # 1. TRAITEMENT DES RECHERCHES UTILISATEURS
        try:
            pending_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-pending-search", timeout=3).json()
            query = pending_res.get("query")
            
            if query and query != last_search_query and len(query.strip()) >= 2:
                last_search_query = query
                search_url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=4"
                s_res = requests.get(search_url, headers=headers, timeout=3).json()
                
                tracks = []
                for item in s_res.get('tracks', {}).get('items', []):
                    tracks.append({
                        "title": item['name'],
                        "artist": item['artists'][0]['name'],
                        "uri": item['uri'],
                        "cover": item['album']['images'][0]['url'] if item['album']['images'] else ""
                    })
                requests.post(f"{CLOUD_SERVER_URL}/api/set-search-results", json={"results": tracks}, timeout=3)
        except Exception:
            pass

        # 2. LECTURE ET SYNCHRONISATION DE LA MUSIQUE SPOTIFY
        pb_res = requests.get("https://api.spotify.com/v1/me/player", headers=headers, timeout=3)
        
        if pb_res.status_code == 200 and pb_res.text:
            playback = pb_res.json()
            
            if playback.get("item") and playback.get("is_playing"):
                current_track = playback["item"]
                current_name = current_track["name"]
                remaining_seconds = max(0, int((current_track["duration_ms"] - playback["progress_ms"]) / 1000))

                # Récupération de la file d'attente
                q_res = requests.get("https://api.spotify.com/v1/me/player/queue", headers=headers, timeout=3)
                queue_list = q_res.json().get("queue", []) if q_res.status_code == 200 else []

                if len(queue_list) > 0:
                    next_track = queue_list[0]
                    next_title = next_track["name"]
                    next_artist = next_track["artists"][0]["name"]
                    next_cover = next_track["album"]["images"][0]["url"] if next_track["album"]["images"] else ""
                    next_id = next_track["id"]
                else:
                    next_title = "Sélection Playlist"
                    next_artist = "Spotify Auto"
                    next_cover = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300"
                    next_id = "default_next"

                # Mise à jour de l'état sur le serveur web Render
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
                    },
                    timeout=3
                )

                print(f"🎵 En cours : {current_name} ({remaining_seconds}s restantes) | Suivant : {next_title}")

                if remaining_seconds > 45:
                    has_evaluated_track = False

                # 3. ARBITRAGE ET DECISION DES VOTES À T-30 SECONDES
                if remaining_seconds <= 30 and not has_evaluated_track:
                    print(f"\n⏰ T-30s ! Annalyse des votes du public...")
                    state_res = requests.get(f"{CLOUD_SERVER_URL}/api/get-state", timeout=3).json()
                    votes = state_res.get("votes", {})
                    upvotes = votes.get("upvotes", 0)
                    downvotes = votes.get("downvotes", 0)
                    
                    suggestion = state_res.get("suggested_song")
                    alt_score = suggestion.get("score", 0) if suggestion else 0
                    alt_uri = suggestion.get("uri") if suggestion else None
                    alt_title = suggestion.get("title") if suggestion else None

                    net_planned_score = upvotes - downvotes

                    if alt_uri and alt_score > net_planned_score and alt_score > 0:
                        print(f"🎉 ALTERNATIVE POPULAIRE ADOPTÉE : '{alt_title}' !")
                        requests.post(f"https://api.spotify.com/v1/me/player/queue?uri={alt_uri}", headers=headers)

                    elif downvotes > upvotes:
                        print(f"⛔ VETO POPULAIRE ! Passage à la chanson suivante...")
                        requests.post("https://api.spotify.com/v1/me/player/next", headers=headers)

                    has_evaluated_track = True

            else:
                print("⏸️ Spotify est en pause ou aucune chanson en cours de lecture...")
                requests.post(
                    f"{CLOUD_SERVER_URL}/api/update-state",
                    json={
                        "current_title": "Musique en pause",
                        "current_artist": "En attente du DJ",
                        "current_remaining_seconds": 999,
                        "next_title": "Prochaine chanson",
                        "next_artist": "Lancer Spotify",
                        "next_cover": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300",
                        "next_track_id": "paused"
                    },
                    timeout=3
                )

        elif pb_res.status_code == 429:
            print("⚠️ Rate Limit détecté ! Pause de sécurité de 15s...")
            time.sleep(15)
        elif pb_res.status_code == 401:
            print("❌ Token expiré ! Régénérez-le avec get_fresh_token.py")

    except Exception as e:
        print(f"⚠️ Erreur de connexion : {e}")

    # Pause de 5s pour préserver le quota Spotify
    time.sleep(5)
