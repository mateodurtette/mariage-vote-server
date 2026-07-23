from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Données globales
music_state = {
    "current_track": {"title": "Chargement...", "artist": "", "remaining_seconds": 0},
    "next_track": {"title": "Chargement...", "artist": "", "cover": "", "track_id": ""},
    "suggested_track": None  # {"title": "", "artist": "", "suggested_by": "", "votes": 0}
}

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
    song_name: str

@app.post("/api/update-state")
def update_state(data: StateUpdate):
    global music_state, votes
    
    # Si la chanson suivante change, on réinitialise les votes
    if data.next_track_id != music_state["next_track"]["track_id"]:
        votes = {"upvotes": 0, "downvotes": 0, "voted_ips": set()}
        music_state["suggested_track"] = None  # Réinitialise la suggestion pour la nouvelle chanson
    
    music_state["current_track"] = {
        "title": data.current_title,
        "artist": data.current_artist,
        "remaining_seconds": data.current_remaining_seconds
    }
    music_state["next_track"] = {
        "title": data.next_title,
        "artist": data.next_artist,
        "cover": data.next_cover,
        "track_id": data.next_track_id
    }
    return {"status": "ok"}

@app.get("/api/get-state")
def get_state():
    return {
        "state": music_state,
        "votes": {"upvotes": votes["upvotes"], "downvotes": votes["downvotes"]}
    }

@app.post("/api/suggest-song")
def suggest_song(data: SuggestionRequest):
    if not music_state["suggested_track"]:
        music_state["suggested_track"] = {
            "title": data.song_name,
            "votes": 1
        }
    else:
        music_state["suggested_track"]["votes"] += 1
    return {"status": "ok"}

@app.post("/api/vote/{vote_type}")
def vote(vote_type: str, request: Request):
    client_ip = request.client.host
    
    if music_state["current_track"]["remaining_seconds"] <= 30:
        return {"status": "closed", "message": "Les votes sont clos !"}

    if client_ip in votes["voted_ips"]:
        return {"status": "already_voted", "message": "Vous avez déjà voté !"}

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
        <title>💒 Mariage de Lauriane & Matéo</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #121212; color: white; text-align: center; padding: 15px; margin: 0; }
            .card { background: #1e1e1e; padding: 20px; border-radius: 16px; max-width: 380px; margin: 10px auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            
            /* Bannière Musique En Cours */
            .now-playing { background: #2a2a2a; border-left: 4px solid #1db954; padding: 10px; border-radius: 8px; font-size: 0.85rem; text-align: left; margin-bottom: 15px; }
            .now-playing-title { font-weight: bold; color: #1db954; }
            
            .header-title { font-size: 0.95rem; color: #ffca28; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
            .header-subtitle { font-size: 0.8rem; color: #b3b3b3; margin-bottom: 15px; }

            .timer-box { background: #282828; padding: 6px 12px; border-radius: 20px; display: inline-block; margin-bottom: 12px; font-weight: bold; font-size: 0.85rem; color: #ffca28; }
            .timer-closed { color: #e91429; }

            img { width: 170px; height: 170px; border-radius: 12px; object-fit: cover; margin-bottom: 10px; }
            h2 { font-size: 1.2rem; margin: 5px 0; }
            p { color: #b3b3b3; margin: 0 0 15px; font-size: 0.85rem; }
            
            .btn-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 15px; }
            button { font-size: 1.3rem; padding: 10px 20px; border: none; border-radius: 30px; cursor: pointer; transition: all 0.2s; }
            button:disabled { opacity: 0.3; cursor: not-allowed; filter: grayscale(100%); }
            .btn-up { background: #1db954; color: white; }
            .btn-down { background: #e91429; color: white; }
            
            /* Section Suggestion */
            .suggest-box { background: #252525; padding: 12px; border-radius: 12px; margin-top: 15px; font-size: 0.85rem; }
            .suggest-input { width: 70%; padding: 8px; border-radius: 20px; border: none; outline: none; text-align: center; }
            .suggest-btn { padding: 8px 12px; border-radius: 20px; border: none; background: #1db954; color: white; font-weight: bold; cursor: pointer; margin-left: 5px; }
            .suggestion-display { background: #333; padding: 8px; border-radius: 8px; margin-top: 8px; color: #ffca28; }

            .msg { font-size: 0.8rem; font-weight: bold; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="card">
            <!-- 1. Musique actuelle -->
            <div class="now-playing">
                🔊 <b>EN CE MOMENT DANS LA SALLE :</b><br>
                <span id="current-title" class="now-playing-title">Chargement...</span> - <span id="current-artist"></span><br>
                <small>⏱️ Temps restant : <b id="current-timer">--</b>s</small>
            </div>

            <!-- 2. Titre Personnalisé -->
            <div class="header-title">💒 MARIAGE DE LAURIANE ET MATEO</div>
            <div class="header-subtitle">prochaine chanson prévue :</div>

            <!-- Timer du vote -->
            <div id="timer-container" class="timer-box">⏱️ Vote clos dans : <span id="timer">--</span>s</div><br>

            <img id="cover" src="https://via.placeholder.com/170?text=Prochaine+Chanson" alt="Pochette">
            <h2 id="title">Chargement...</h2>
            <p id="artist"></p>
            
            <!-- Boutons de Vote -->
            <div class="btn-container">
                <button id="btn-up" class="btn-up" onclick="sendVote('up')">👍 <span id="up-count">0</span></button>
                <button id="btn-down" class="btn-down" onclick="sendVote('down')">👎 <span id="down-count">0</span></button>
            </div>
            <div id="status-msg" class="msg"></div>

            <!-- 3. Section Suggestion d'une chanson -->
            <div class="suggest-box">
                💡 <b>Proposer une alternative :</b>
                <div style="margin-top: 8px;">
                    <input type="text" id="song-input" class="suggest-input" placeholder="Titre - Artiste...">
                    <button onclick="submitSuggestion()" class="suggest-btn">Envoyer</button>
                </div>
                <div id="suggestion-area" style="display:none;" class="suggestion-display">
                    <b>Choix optionnel proposé par un invité :</b><br>
                    <span id="suggested-song-name"></span>
                </div>
            </div>
        </div>

        <script>
            let currentTrackId = "";
            let isClosed = false;

            async function refreshData() {
                try {
                    const res = await fetch('/api/get-state');
                    const data = await res.json();
                    
                    const current = data.state.current_track;
                    const next = data.state.next_track;
                    const votes = data.votes;
                    const suggestion = data.state.suggested_track;

                    // Mettre à jour la musique actuelle
                    document.getElementById('current-title').innerText = current.title;
                    document.getElementById('current-artist').innerText = current.artist;
                    document.getElementById('current-timer').innerText = current.remaining_seconds;

                    // Prochaine chanson
                    if (next.track_id && next.track_id !== currentTrackId) {
                        currentTrackId = next.track_id;
                        localStorage.removeItem('voted_' + currentTrackId);
                        enableButtons();
                    }

                    document.getElementById('title').innerText = next.title;
                    document.getElementById('artist').innerText = next.artist;
                    if (next.cover) document.getElementById('cover').src = next.cover;

                    // Timer du vote
                    const remaining = current.remaining_seconds;
                    const votingTimeLeft = remaining - 30;

                    if (votingTimeLeft > 0) {
                        isClosed = false;
                        document.getElementById('timer-container').className = "timer-box";
                        document.getElementById('timer-container').innerHTML = "⏱️ Fin du vote dans : <span>" + votingTimeLeft + "</span>s";
                        if (!localStorage.getItem('voted_' + currentTrackId)) enableButtons();
                    } else {
                        isClosed = true;
                        document.getElementById('timer-container').className = "timer-box timer-closed";
                        document.getElementById('timer-container').innerHTML = "🔒 VOTE CLOS";
                        disableButtons("🔒 Décision en cours d'application...");
                    }

                    document.getElementById('up-count').innerText = votes.upvotes;
                    document.getElementById('down-count').innerText = votes.downvotes;

                    // Afficher la suggestion si présente
                    if (suggestion) {
                        document.getElementById('suggestion-area').style.display = 'block';
                        document.getElementById('suggested-song-name').innerText = suggestion.title;
                    } else {
                        document.getElementById('suggestion-area').style.display = 'none';
                    }

                    if (localStorage.getItem('voted_' + currentTrackId) && !isClosed) {
                        disableButtons("✅ Vote enregistré !");
                    }

                } catch(e) { console.error(e); }
            }

            async function sendVote(type) {
                if (isClosed) return;
                const res = await fetch('/api/vote/' + type, { method: 'POST' });
                const data = await res.json();
                if (data.status === 'ok') {
                    localStorage.setItem('voted_' + currentTrackId, 'true');
                    disableButtons("✅ Vote enregistré !");
                }
                refreshData();
            }

            async function submitSuggestion() {
                const input = document.getElementById('song-input');
                if (!input.value) return;
                await fetch('/api/suggest-song', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ song_name: input.value })
                });
                input.value = "";
                refreshData();
            }

            function disableButtons(msg) {
                document.getElementById('btn-up').disabled = true;
                document.getElementById('btn-down').disabled = true;
                document.getElementById('status-msg').innerText = msg;
            }

            function enableButtons() {
                document.getElementById('btn-up').disabled = false;
                document.getElementById('btn-down').disabled = false;
                document.getElementById('status-msg').innerText = "";
            }

            setInterval(refreshData, 1000);
            refreshData();
        </script>
    </body>
    </html>
    """
