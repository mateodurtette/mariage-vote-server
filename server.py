from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Identifiants pour la recherche d'alternatives
SPOTIPY_CLIENT_ID = "a0a55f8c047f44f9a58dbd4e0715553a"
SPOTIPY_CLIENT_SECRET = "32de8e9ad70f43e0bdf409ee6be52532"
sp_search = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET
))

music_state = {
    "current_title": "Chargement...",
    "current_artist": "",
    "current_remaining_seconds": 0,
    "next_title": "Chargement...",
    "next_artist": "",
    "next_cover": "",
    "next_track_id": ""
}

suggested_song = None  # {"title": "", "artist": "", "uri": "", "cover": "", "votes": 0}
votes = {"upvotes": 0, "downvotes": 0, "voted_ips": set()}

class StateUpdate(BaseModel):
    current_title: str
    current_artist: str
    current_remaining_seconds: int
    next_title: str
    next_artist: str
    next_cover: str
    next_track_id: str

class SuggestionRequest(BaseModel):
    title: str
    artist: str
    uri: str
    cover: str

@app.post("/api/update-state")
def update_state(data: StateUpdate):
    global music_state, votes, suggested_song
    
    if data.next_track_id != music_state["next_track_id"]:
        votes = {"upvotes": 0, "downvotes": 0, "voted_ips": set()}
        suggested_song = None
    
    music_state = {
        "current_title": data.current_title,
        "current_artist": data.current_artist,
        "current_remaining_seconds": data.current_remaining_seconds,
        "next_title": data.next_title,
        "next_artist": data.next_artist,
        "next_cover": data.next_cover,
        "next_track_id": data.next_track_id
    }
    return {"status": "ok"}

@app.get("/api/search-spotify")
def search_spotify(q: str):
    if not q or len(q) < 2:
        return {"results": []}
    results = sp_search.search(q=q, limit=3, type='track')
    tracks = []
    for item in results.get('tracks', {}).get('items', []):
        tracks.append({
            "title": item['name'],
            "artist": item['artists'][0]['name'],
            "uri": item['uri'],
            "cover": item['album']['images'][0]['url'] if item['album']['images'] else ""
        })
    return {"results": tracks}

@app.get("/api/get-state")
def get_state():
    return {
        "state": music_state,
        "suggested_song": suggested_song,
        "votes": {"upvotes": votes["upvotes"], "downvotes": votes["downvotes"]}
    }

@app.post("/api/suggest-song")
def suggest_song(data: SuggestionRequest):
    global suggested_song
    if not suggested_song:
        suggested_song = {
            "title": data.title,
            "artist": data.artist,
            "uri": data.uri,
            "cover": data.cover,
            "votes": 1
        }
    return {"status": "ok"}

@app.post("/api/vote-suggestion")
def vote_suggestion():
    global suggested_song
    if suggested_song:
        suggested_song["votes"] += 1
    return {"status": "ok"}

@app.post("/api/vote/{vote_type}")
def vote(vote_type: str, request: Request):
    client_ip = request.client.host
    if music_state["current_remaining_seconds"] <= 30:
        return {"status": "closed"}
    if client_ip in votes["voted_ips"]:
        return {"status": "already_voted"}
    if vote_type == "up":
        votes["upvotes"] += 1
    elif vote_type == "down":
        votes["downvotes"] += 1
    votes["voted_ips"].add(client_ip)
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>💒 Mariage Lauriane & Matéo - Jukebox Auto</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #121212; color: white; text-align: center; padding: 15px; margin: 0; }
            .card { background: #1e1e1e; padding: 20px; border-radius: 16px; max-width: 380px; margin: 10px auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            .now-playing { background: #2a2a2a; border-left: 4px solid #1db954; padding: 10px; border-radius: 10px; font-size: 0.85rem; text-align: left; margin-bottom: 15px; }
            .now-playing-title { font-weight: bold; color: #1db954; }
            .timer-box { background: #282828; padding: 6px 12px; border-radius: 20px; display: inline-block; margin-bottom: 12px; font-weight: bold; font-size: 0.85rem; color: #ffca28; }
            .timer-closed { color: #e91429; }
            img.cover { width: 160px; height: 160px; border-radius: 12px; object-fit: cover; margin-bottom: 10px; }
            .btn-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 15px; }
            button { font-size: 1.3rem; padding: 10px 20px; border: none; border-radius: 30px; cursor: pointer; }
            button:disabled { opacity: 0.3; filter: grayscale(100%); }
            .btn-up { background: #1db954; color: white; }
            .btn-down { background: #e91429; color: white; }
            .suggest-box { background: #252525; padding: 12px; border-radius: 12px; margin-top: 15px; font-size: 0.85rem; }
            .suggest-input { width: 80%; padding: 8px; border-radius: 20px; border: none; outline: none; text-align: center; }
            .search-results { text-align: left; margin-top: 10px; background: #121212; border-radius: 8px; overflow: hidden; }
            .search-item { display: flex; align-items: center; padding: 8px; border-bottom: 1px solid #222; cursor: pointer; }
            .search-item img { width: 40px; height: 40px; border-radius: 4px; margin-right: 10px; }
            .search-item-info { font-size: 0.8rem; flex-grow: 1; }
            .search-item-info b { color: white; display: block; }
            .search-item-info span { color: #b3b3b3; }
            .suggestion-card { background: #2d2a1e; border: 1px solid #ffca28; padding: 10px; border-radius: 10px; margin-top: 10px; }
            .vote-alt-btn { background: #ffca28; color: #121212; font-size: 0.85rem; padding: 8px 16px; border-radius: 15px; font-weight: bold; border: none; cursor: pointer; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="now-playing">
                🔊 <b>DANS LA SALLE :</b> <span id="current-title" class="now-playing-title">...</span><br>
                <small>Fin dans : <span id="current-timer" style="color:#ffca28;">--:--</span></small>
            </div>

            <div style="font-size:0.9rem; color:#ffca28; font-weight:bold;">💒 MARIAGE LAURIANE & MATÉO</div>
            <div style="font-size:0.8rem; color:#b3b3b3; margin-bottom:10px;">Prochaine chanson prévue :</div>

            <div id="timer-container" class="timer-box">⏱️ Vote clos dans : <span id="timer">--</span></div><br>

            <img id="cover" class="cover" src="https://via.placeholder.com/160" alt="Pochette">
            <h2 id="title" style="font-size:1.1rem; margin:5px 0;">Chargement...</h2>
            <p id="artist" style="color:#b3b3b3; font-size:0.85rem; margin-bottom:15px;"></p>

            <div class="btn-container">
                <button id="btn-up" class="btn-up" onclick="sendVote('up')">👍 <span id="up-count">0</span></button>
                <button id="btn-down" class="btn-down" onclick="sendVote('down')">👎 <span id="down-count">0</span></button>
            </div>

            <!-- Recherche & Alternative Spotify -->
            <div class="suggest-box">
                💡 <b>Proposer une alternative Spotify :</b>
                <div id="suggest-form" style="margin-top: 8px;">
                    <input type="text" id="song-input" class="suggest-input" placeholder="Chercher sur Spotify..." oninput="searchSpotify(this.value)">
                    <div id="search-results" class="search-results"></div>
                </div>

                <div id="suggestion-area" style="display:none;" class="suggestion-card">
                    <div style="font-size:0.75rem; color:#ffca28; font-weight:bold;">🔥 ALTERNATIVE EN COMPÉTITION :</div>
                    <div style="display:flex; align-items:center; margin: 8px 0; text-align:left;">
                        <img id="alt-cover" src="" style="width:45px; height:45px; border-radius:6px; margin-right:10px;">
                        <div>
                            <b id="alt-title" style="font-size:0.85rem;"></b><br>
                            <span id="alt-artist" style="font-size:0.75rem; color:#b3b3b3;"></span>
                        </div>
                    </div>
                    <button class="vote-alt-btn" onclick="voteSuggestion()">👍 Voter pour ce titre (<span id="alt-votes">0</span>)</button>
                </div>
            </div>
        </div>

        <script>
            let currentTrackId = "";
            let isClosed = false;
            let currentRemainingSec = 0;
            let searchTimeout = null;

            function formatTime(sec) {
                if (sec <= 0) return "0:00";
                const m = Math.floor(sec / 60); const s = sec % 60;
                return m + ":" + (s < 10 ? "0" : "") + s;
            }

            async function searchSpotify(query) {
                clearTimeout(searchTimeout);
                const resContainer = document.getElementById('search-results');
                if (query.length < 2) { resContainer.innerHTML = ""; return; }

                searchTimeout = setTimeout(async () => {
                    const res = await fetch('/api/search-spotify?q=' + encodeURIComponent(query));
                    const data = await res.json();
                    resContainer.innerHTML = "";
                    data.results.forEach(track => {
                        const item = document.createElement('div');
                        item.className = 'search-item';
                        item.innerHTML = `
                            <img src="${track.cover}">
                            <div class="search-item-info">
                                <b>${track.title}</b>
                                <span>${track.artist}</span>
                            </div>
                        `;
                        item.onclick = () => selectTrack(track);
                        resContainer.appendChild(item);
                    });
                }, 300);
            }

            async function selectTrack(track) {
                document.getElementById('search-results').innerHTML = "";
                document.getElementById('song-input').value = "";
                await fetch('/api/suggest-song', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(track)
                });
                refreshData();
            }

            async function refreshData() {
                try {
                    const res = await fetch('/api/get-state');
                    const data = await res.json();
                    const state = data.state;
                    const votes = data.votes;
                    const suggestion = data.suggested_song;

                    document.getElementById('current-title').innerText = state.current_title + " - " + state.current_artist;
                    currentRemainingSec = state.current_remaining_seconds;
                    document.getElementById('current-timer').innerText = formatTime(currentRemainingSec);

                    if (state.next_track_id && state.next_track_id !== currentTrackId) {
                        currentTrackId = state.next_track_id;
                        localStorage.removeItem('voted_' + currentTrackId);
                        enableButtons();
                    }

                    document.getElementById('title').innerText = state.next_title;
                    document.getElementById('artist').innerText = state.next_artist;
                    if (state.next_cover) document.getElementById('cover').src = state.next_cover;

                    const votingTimeLeft = currentRemainingSec - 30;
                    if (votingTimeLeft > 0) {
                        isClosed = false;
                        document.getElementById('timer-container').className = "timer-box";
                        document.getElementById('timer-container').innerHTML = "⏱️ Fin du vote dans : <span>" + formatTime(votingTimeLeft) + "</span>";
                    } else {
                        isClosed = true;
                        document.getElementById('timer-container').className = "timer-box timer-closed";
                        document.getElementById('timer-container').innerHTML = "🔒 VOTE CLOS (Sélection finale !)";
                        disableButtons();
                    }

                    document.getElementById('up-count').innerText = votes.upvotes;
                    document.getElementById('down-count').innerText = votes.downvotes;

                    if (suggestion) {
                        document.getElementById('suggest-form').style.display = 'none';
                        document.getElementById('suggestion-area').style.display = 'block';
                        document.getElementById('alt-title').innerText = suggestion.title;
                        document.getElementById('alt-artist').innerText = suggestion.artist;
                        document.getElementById('alt-cover').src = suggestion.cover;
                        document.getElementById('alt-votes').innerText = suggestion.votes;
                    } else {
                        document.getElementById('suggest-form').style.display = 'block';
                        document.getElementById('suggestion-area').style.display = 'none';
                    }

                } catch(e) { console.error(e); }
            }

            async function sendVote(type) {
                if (isClosed) return;
                await fetch('/api/vote/' + type, { method: 'POST' });
                localStorage.setItem('voted_' + currentTrackId, 'true');
                disableButtons();
                refreshData();
            }

            async function voteSuggestion() {
                await fetch('/api/vote-suggestion', { method: 'POST' });
                refreshData();
            }

            function disableButtons() {
                document.getElementById('btn-up').disabled = true;
                document.getElementById('btn-down').disabled = true;
            }

            function enableButtons() {
                document.getElementById('btn-up').disabled = false;
                document.getElementById('btn-down').disabled = false;
            }

            setInterval(() => {
                if (currentRemainingSec > 0) {
                    currentRemainingSec--;
                    document.getElementById('current-timer').innerText = formatTime(currentRemainingSec);
                }
            }, 1000);

            setInterval(refreshData, 1500);
            refreshData();
        </script>
    </body>
    </html>
    """
