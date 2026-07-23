from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_next_track = {
    "title": "Chargement...",
    "artist": "",
    "cover": "",
    "track_id": "",
    "remaining_seconds": 0
}

votes = {"upvotes": 0, "downvotes": 0, "voted_ips": set()}

class TrackUpdate(BaseModel):
    title: str
    artist: str
    cover: str
    track_id: str
    remaining_seconds: int

@app.post("/api/update-next-track")
def update_next_track(data: TrackUpdate):
    global current_next_track, votes
    
    # Si la chanson suivante change, on réinitialise les votes
    if data.track_id != current_next_track["track_id"]:
        votes = {"upvotes": 0, "downvotes": 0, "voted_ips": set()}
    
    current_next_track = {
        "title": data.title,
        "artist": data.artist,
        "cover": data.cover,
        "track_id": data.track_id,
        "remaining_seconds": data.remaining_seconds
    }
    return {"status": "ok"}

@app.get("/api/get-next-track")
def get_next_track():
    return current_next_track

@app.get("/api/get-votes")
def get_votes():
    return {"upvotes": votes["upvotes"], "downvotes": votes["downvotes"]}

@app.post("/api/vote/{vote_type}")
def vote(vote_type: str, request: Request):
    client_ip = request.client.host
    
    # 1. Vérification : Bloquer si le vote est clos (moins de 30s)
    if current_next_track["remaining_seconds"] <= 30:
        return {"status": "closed", "message": "Les votes sont clos pour cette chanson !"}

    # 2. Anti-spam par IP (1 seul vote par personne)
    if client_ip in votes["voted_ips"]:
        return {"status": "already_voted", "message": "Vous avez déjà voté !"}

    if vote_type == "up":
        votes["upvotes"] += 1
        votes["voted_ips"].add(client_ip)
    elif vote_type == "down":
        votes["downvotes"] += 1
        votes["voted_ips"].add(client_ip)
        
    return {"status": "ok", "upvotes": votes["upvotes"], "downvotes": votes["downvotes"]}

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>💍 Mariage DJ Vote</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #121212; color: white; text-align: center; padding: 20px; margin: 0; }
            .card { background: #1e1e1e; padding: 20px; border-radius: 16px; max-width: 350px; margin: 20px auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            .subtitle { font-size: 0.85rem; color: #1db954; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
            
            /* Style du Timer */
            .timer-box { background: #282828; padding: 8px 15px; border-radius: 20px; display: inline-block; margin-bottom: 15px; font-weight: bold; font-size: 0.9rem; color: #ffca28; }
            .timer-closed { color: #e91429; }

            img { width: 180px; height: 180px; border-radius: 12px; object-fit: cover; margin-bottom: 10px; }
            h2 { font-size: 1.2rem; margin: 5px 0; }
            p { color: #b3b3b3; margin: 0 0 15px; font-size: 0.9rem; }
            
            .btn-container { display: flex; justify-content: center; gap: 15px; }
            button { font-size: 1.4rem; padding: 12px 24px; border: none; border-radius: 30px; cursor: pointer; transition: all 0.2s; }
            button:active { transform: scale(0.95); }
            button:disabled { opacity: 0.3; cursor: not-allowed; filter: grayscale(100%); }
            .btn-up { background: #1db954; color: white; }
            .btn-down { background: #e91429; color: white; }
            
            .msg { margin-top: 15px; font-size: 0.85rem; font-weight: bold; }
            .msg-voted { color: #1db954; }
            .msg-closed { color: #e91429; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="subtitle">⏭️ À venir dans la soirée</div>
            
            <div id="timer-container" class="timer-box">
                ⏱️ Vote clos dans : <span id="timer">--</span>s
            </div>

            <br>
            <img id="cover" src="https://via.placeholder.com/180?text=Prochaine+Chanson" alt="Pochette">
            <h2 id="title">Chargement...</h2>
            <p id="artist"></p>
            
            <div class="btn-container">
                <button id="btn-up" class="btn-up" onclick="sendVote('up')">👍 <span id="up-count">0</span></button>
                <button id="btn-down" class="btn-down" onclick="sendVote('down')">👎 <span id="down-count">0</span></button>
            </div>
            
            <div id="status-msg" class="msg"></div>
        </div>

        <script>
            let currentTrackId = "";
            let isClosed = false;

            async function refreshData() {
                try {
                    const trackRes = await fetch('/api/get-next-track');
                    const track = await trackRes.json();
                    
                    // Si la chanson change : réinitialiser le statut
                    if (track.track_id && track.track_id !== currentTrackId) {
                        currentTrackId = track.track_id;
                        localStorage.removeItem('voted_' + currentTrackId);
                        enableButtons();
                    }

                    if (track.title) document.getElementById('title').innerText = track.title;
                    if (track.artist) document.getElementById('artist').innerText = track.artist;
                    if (track.cover) document.getElementById('cover').src = track.cover;

                    // Gestion du Compte à rebours
                    const remaining = track.remaining_seconds;
                    const votingTimeLeft = remaining - 30; // Temps avant fermeture à T-30s

                    if (votingTimeLeft > 0) {
                        isClosed = false;
                        document.getElementById('timer-container').className = "timer-box";
                        document.getElementById('timer-container').innerHTML = "⏱️ Fin du vote dans : <span>" + votingTimeLeft + "</span>s";
                        
                        // Si l'utilisateur n'a pas encore voté, on laisse les boutons actifs
                        if (!localStorage.getItem('voted_' + currentTrackId)) {
                            enableButtons();
                        }
                    } else {
                        // Vote clos à moins de 30 secondes de la fin
                        isClosed = true;
                        document.getElementById('timer-container').className = "timer-box timer-closed";
                        document.getElementById('timer-container').innerHTML = "🔒 VOTE CLOS (Tranché par le DJ !)";
                        disableButtons("🔒 Le vote est clos pour ce morceau !");
                    }

                    // Mise à jour des compteurs de votes
                    const voteRes = await fetch('/api/get-votes');
                    const votes = await voteRes.json();
                    document.getElementById('up-count').innerText = votes.upvotes;
                    document.getElementById('down-count').innerText = votes.downvotes;

                    // Si l'utilisateur a déjà voté
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
                } else if (data.status === 'already_voted') {
                    localStorage.setItem('voted_' + currentTrackId, 'true');
                    disableButtons("⚠️ Vous avez déjà voté pour cette chanson.");
                } else if (data.status === 'closed') {
                    disableButtons("🔒 Trop tard ! Les votes sont clos.");
                }
                refreshData();
            }

            function disableButtons(msg) {
                document.getElementById('btn-up').disabled = true;
                document.getElementById('btn-down').disabled = true;
                const msgEl = document.getElementById('status-msg');
                msgEl.innerText = msg;
                msgEl.className = isClosed ? "msg msg-closed" : "msg msg-voted";
            }

            function enableButtons() {
                document.getElementById('btn-up').disabled = false;
                document.getElementById('btn-down').disabled = false;
                document.getElementById('status-msg').innerText = "";
            }

            // Rafraîchissement toutes les secondes pour un timer fluide
            setInterval(refreshData, 1000);
            refreshData();
        </script>
    </body>
    </html>
    """
