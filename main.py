from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from fielder_data import RandomFielderMock, ExternalSocketProvider

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# --- NEW: DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket_tactics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- NEW: DATABASE MODEL ---
class SavedShot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(50), nullable=False)      
    innings_number = db.Column(db.Integer, nullable=False)   
    ball_number = db.Column(db.String(10), nullable=False, default="0.0") # NEW
    angle = db.Column(db.Float, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, default=0.0)
    text = db.Column(db.String(200), default="")

# Create the database file if it doesn't exist yet
with app.app_context():
    db.create_all()

socketio = SocketIO(app, cors_allowed_origins='*')

USE_REAL_DATA = False 
EXTERNAL_WS_URL = "ws://gay:9000"

def on_new_fielder_data(data):
    pass

if USE_REAL_DATA:
    provider = ExternalSocketProvider(on_new_fielder_data, EXTERNAL_WS_URL)
else:
    provider = RandomFielderMock(on_new_fielder_data)

#provider.start()

@app.route('/')
def index():
    return render_template('panel.html')

@socketio.on('send_command')
def handle_command(json_data):
    print(f"Received command: {json_data}")
    emit('unity_control', json_data, broadcast=True)

# --- NEW: DATABASE SOCKET LISTENERS ---

def emit_filtered_shots(match_id, innings_number):
    shots = SavedShot.query.filter_by(match_id=match_id, innings_number=innings_number).all()
    shots_data = [
        {
            "id": s.id, 
            "ball_number": s.ball_number, # NEW
            "angle": s.angle, 
            "distance": s.distance, 
            "height": s.height, 
            "text": s.text
        } 
        for s in shots
    ]
    emit('update_saved_shots', shots_data, broadcast=True)

def emit_all_shots():
    """Helper function to fetch all shots from SQLite and send to web clients."""
    shots = SavedShot.query.all()
    shots_data = [{"id": s.id, "angle": s.angle, "distance": s.distance, "height": s.height, "text": s.text} for s in shots]
    emit('update_saved_shots', shots_data, broadcast=True)

@socketio.on('request_shots')
def handle_request_shots():
    # Sent by the frontend when the page loads
    emit_all_shots()

@socketio.on('save_shot')
def handle_save_shot(data):
    new_shot = SavedShot(
        match_id=data['match_id'],
        innings_number=data['innings_number'],
        ball_number=data.get('ball_number', '0.0'), # NEW
        angle=data['angle'],
        distance=data['distance'],
        height=data.get('height', 0.0),
        text=data.get('text', '')
    )
    db.session.add(new_shot)
    db.session.commit()
    emit_filtered_shots(data['match_id'], data['innings_number'])

@socketio.on('delete_shot')
def handle_delete_shot(shot_id):
    # Delete the trajectory from SQLite
    shot = SavedShot.query.get(shot_id)
    if shot:
        db.session.delete(shot)
        db.session.commit()
    emit_all_shots() # Broadcast updated list

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)