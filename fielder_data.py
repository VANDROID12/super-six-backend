import threading
import time
import random
import json
import math
from websocket import create_connection # For the real implementation later

# --- THE CONTRACT ---
# Both the Mock and Real provider will trigger this callback
# whenever they have new data.
class FielderDataProvider:
    def __init__(self, on_data_callback):
        self.callback = on_data_callback
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True # Kills thread if main app closes
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run_loop(self):
        pass # To be implemented by children

# --- IMPLEMENTATION 1: THE MOCK (Random) ---
class RandomFielderMock(FielderDataProvider):
    def _run_loop(self):
        fielders = []
        # 1. Spawn them initially inside the circle
        for i in range(11):
            # Using polar coordinates for a random point in a circle
            angle = random.uniform(0, 2 * math.pi)
            # math.sqrt ensures they don't all cluster in the dead center
            radius = 0.25 * math.sqrt(random.random()) 
            
            fielders.append({
                "id": i, 
                "x": 0.5 + radius * math.cos(angle), 
                "y": 0.5 + radius * math.sin(angle)
            })
        
        while self.running:
            for f in fielders:
                # 2. Pick a random proposed movement
                new_x = f["x"] + random.uniform(-0.015, 0.015)
                new_y = f["y"] + random.uniform(-0.015, 0.015)
                
                # 3. Check distance from the center (0.5, 0.5)
                # Formula: dx^2 + dy^2 <= radius^2
                dx = new_x - 0.5
                dy = new_y - 0.5
                distance_squared = (dx * dx) + (dy * dy)
                
                # Max radius is 0.5, so radius squared is 0.25
                if distance_squared <= 0.25:
                    # It's inside the grass! Accept the move.
                    f["x"] = new_x
                    f["y"] = new_y
                else:
                    # They hit the boundary fence! 
                    # Nudge them gently back toward the center pitch (0.5, 0.5)
                    f["x"] += (0.5 - f["x"]) * 0.05
                    f["y"] += (0.5 - f["y"]) * 0.05
            
            self.callback(fielders)
            time.sleep(1.0)

# --- IMPLEMENTATION 2: THE REAL SOCKET (Future) ---
class ExternalSocketProvider(FielderDataProvider):
    def __init__(self, on_data_callback, socket_url):
        super().__init__(on_data_callback)
        self.url = socket_url

    def _run_loop(self):
        print(f"🔌 Connecting to Fielder Source: {self.url}...")
        while self.running:
            try:
                ws = create_connection(self.url)
                print("✅ Connected to Fielder Source!")
                
                while self.running:
                    result = ws.recv() # Blocks until data comes
                    data = json.loads(result)
                    
                    # Assuming data comes as list of {id, x, y}
                    self.callback(data)
                    
            except Exception as e:
                print(f"❌ External Source Error: {e}")
                time.sleep(2) # Retry delay