from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Serveur Cloud - Vote Mariage")

# Données partagées en mémoire
current_song_info = {
    "title": "En attente du début de soirée...",
    "artist": "",
    "cover": "",
    "track_id": None
}

votes_data = {
    "upvotes": 0,
    "downvotes": 0,
    "voted_ips": set()
}

class SongUpdate(BaseModel):
    title: str
    artist: str
    cover: Optional[str] = ""
    track_id: str

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user_ip = request.client.host
    has_voted = user_ip in votes_data["voted_ips"]

    cover_html = f'<img src="{current_song_info["cover"]}" width="160" style="border-radius:12px; margin-bottom:15px;">' if current_song_info["cover"] else ''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mariage - Vote Musique</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, sans-serif; background-color: #121212; color: white; margin: 0; padding: 20px; text-align: center; }}
            .card {{ background: #181818; border-radius: 16px; padding: 20px; max-width: 400px; margin: 0 auto; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
            .btn {{ border: none; padding: 15px 25px; border-radius: 30px; font-size: 18px; font-weight: bold; cursor: pointer; margin: 10px 0; width: 90%; }}
            .btn-up {{ background-color: #1DB954; color: white; }}
            .btn-down {{ background-color: #E74C3C; color: white; }}
            .btn-disabled {{ background-color: #444; color: #888; cursor: not-allowed; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h3 style="color:#1DB954; margin-top:0;">💍 Mariage - Prochaine Chanson</h3>
            {cover_html}
            <h2 style="margin: 5px 0;">{current_song_info['title']}</h2>
            <p style="color: #aaa; margin-top: 0;">{current_song_info['artist']}</p>
            
            <hr style="border-color: #282828; margin: 20px 0;">

            {'<p style="color:#1DB954; font-weight:bold;">✅ Votre vote a été pris en compte !</p>' if has_voted else '<h3>Voulez-vous écouter ce titre ?</h3>'}

            <button class="btn btn-up {'btn-disabled' if has_voted else ''}" onclick="vote('up')" {'disabled' if has_voted else ''}>
                👍 Garder ({votes_data['upvotes']})
            </button>
            <button class="btn btn-down {'btn-disabled' if has_voted else ''}" onclick="vote('down')" {'disabled' if has_voted else ''}>
                👎 Passer à la suivante ({votes_data['downvotes']})
            </button>
        </div>

        <script>
            function vote(type) {{
                fetch('/vote/' + type, {{ method: 'POST' }}).then(() => location.reload());
            }}
            setInterval(() => location.reload(), 8000);
        </script>
    </body>
    </html>
    """

@app.post("/vote/{vote_type}")
def vote(vote_type: str, request: Request):
    user_ip = request.client.host
    if user_ip in votes_data["voted_ips"]:
        raise HTTPException(status_code=400, detail="Déjà voté")

    if vote_type == "up":
        votes_data["upvotes"] += 1
    elif vote_type == "down":
        votes_data["downvotes"] += 1

    votes_data["voted_ips"].add(user_ip)
    return {"status": "ok"}

# Endpoints pour la communication avec l'ordinateur DJ
@app.post("/api/update-track")
def update_track(data: SongUpdate):
    if current_song_info["track_id"] != data.track_id:
        current_song_info["title"] = data.title
        current_song_info["artist"] = data.artist
        current_song_info["cover"] = data.cover
        current_song_info["track_id"] = data.track_id
        # Réinitialisation des votes pour la nouvelle chanson
        votes_data["upvotes"] = 0
        votes_data["downvotes"] = 0
        votes_data["voted_ips"].clear()
    return {"status": "updated"}

@app.get("/api/get-votes")
def get_votes():
    return {
        "upvotes": votes_data["upvotes"],
        "downvotes": votes_data["downvotes"],
        "track_id": current_song_info["track_id"]
    }