from fastapi import FastAPI
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
    "title": "Chargement de la prochaine chanson...",
    "artist": "",
    "cover": "",
    "track_id": ""
}

votes = {"upvotes": 0, "downvotes": 0}

class TrackUpdate(BaseModel):
    title: str
    artist: str
    cover: str
    track_id: str

@app.post("/api/update-next-track")
def update_next_track(data: TrackUpdate):
    global current_next_track, votes
    # Si le morceau à venir a changé, on réinitialise les votes pour la nouvelle chanson
    if data.track_id != current_next_track["track_id"]:
        votes = {"upvotes": 0, "downvotes": 0}
    
    current_next_track = {
        "title": data.title,
        "artist": data.artist,
        "cover": data.cover,
        "track_id": data.track_id
    }
    return {"status": "ok"}

@app.get("/api/get-next-track")
def get_next_track():
    return current_next_track

@app.get("/api/get-votes")
def get_votes():
    return votes

@app.post("/api/vote/{vote_type}")
def vote(vote_type: str):
    if vote_type == "up":
        votes["upvotes"] += 1
    elif vote_type == "down":
        votes["downvotes"] += 1
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
            .subtitle { font-size: 0.9rem; color: #1db954; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
            img { width: 200px; height: 200px; border-radius: 12px; object-fit: cover; margin-bottom: 15px; }
            h1 { font-size: 1.2rem; color: #ffffff; margin-bottom: 5px; }
            h2 { font-size: 1.3rem; margin: 10px 0 5px; }
            p { color: #b3b3b3; margin: 0 0 20px; }
            .btn-container { display: flex; justify-content: center; gap: 15px; }
            button { font-size: 1.5rem; padding: 12px 24px; border: none; border-radius: 30px; cursor: pointer; transition: transform 0.1s; }
            button:active { transform: scale(0.95); }
            .btn-up { background: #1db954; color: white; }
            .btn-down { background: #e91429; color: white; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="subtitle">⏭️ À venir dans la soirée</div>
            <img id="cover" src="https://via.placeholder.com/200?text=Prochaine+Chanson" alt="Pochette">
            <h2 id="title">Chargement...</h2>
            <p id="artist"></p>
            <div class="btn-container">
                <button class="btn-up" onclick="sendVote('up')">👍 <span id="up-count">0</span></button>
                <button class="btn-down" onclick="sendVote('down')">👎 <span id="down-count">0</span></button>
            </div>
        </div>

        <script>
            async function refreshData() {
                try {
                    const trackRes = await fetch('/api/get-next-track');
                    const track = await trackRes.json();
                    
                    if (track.title) document.getElementById('title').innerText = track.title;
                    if (track.artist) document.getElementById('artist').innerText = track.artist;
                    if (track.cover) document.getElementById('cover').src = track.cover;

                    const voteRes = await fetch('/api/get-votes');
                    const votes = await voteRes.json();
                    document.getElementById('up-count').innerText = votes.upvotes;
                    document.getElementById('down-count').innerText = votes.downvotes;
                } catch(e) { console.error(e); }
            }

            async function sendVote(type) {
                await fetch('/api/vote/' + type, { method: 'POST' });
                refreshData();
            }

            setInterval(refreshData, 2000);
            refreshData();
        </script>
    </body>
    </html>
    """
