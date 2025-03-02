import sqlite3
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Database setup
DB_NAME = "poker.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Ensure All Tables Are Created
cursor.executescript("""
CREATE TABLE IF NOT EXISTS hands (
    hand_id INTEGER PRIMARY KEY,
    variant TEXT,
    venue TEXT,
    table_name TEXT,
    day INTEGER,
    month INTEGER,
    year INTEGER
);

CREATE TABLE IF NOT EXISTS players (
    hand_id INTEGER,
    player_id TEXT,
    seat INTEGER,
    starting_stack REAL,
    winnings REAL,
    FOREIGN KEY(hand_id) REFERENCES hands(hand_id)
);

CREATE TABLE IF NOT EXISTS actions (
    hand_id INTEGER,
    action TEXT,
    FOREIGN KEY(hand_id) REFERENCES hands(hand_id)
);
""")

# Clear Existing Data Before Insert
cursor.executescript("""
DELETE FROM hands;
DELETE FROM players;
DELETE FROM actions;
""")
conn.commit()

# Directory where .phhs files are stored
DATA_DIR = "data"
phhs_files = glob.glob(os.path.join(DATA_DIR, "*.phhs"))

# Function to parse a single file
def parse_poker_file(file_path):
    with open(file_path, "r") as file:
        hand_data = []
        current_hand = {}

        for line in file:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            if line.startswith("["):  # Start of a new hand
                if current_hand:
                    hand_data.append(current_hand)  # Store previous hand
                current_hand = {}  # Reset for new hand
            else:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key in ["variant", "venue", "table", "day", "month", "year", "hand"]:
                    current_hand[key] = value
                elif key == "players":
                    current_hand["players"] = value.strip("[]").split(", ")
                elif key == "starting_stacks":
                    current_hand["starting_stacks"] = list(map(float, value.strip("[]").split(", ")))
                elif key == "winnings":
                    current_hand["winnings"] = list(map(float, value.strip("[]").split(", ")))
                elif key == "actions":
                    current_hand["actions"] = value.strip("[]").split(", ")

        if current_hand:
            hand_data.append(current_hand)  # Add last hand

        return hand_data

# Process Each File and Insert Data
for file in phhs_files:
    hands = parse_poker_file(file)
    
    for hand in hands:
        # Insert into hands table
        cursor.execute("INSERT OR IGNORE INTO hands VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (hand["hand"], hand["variant"], hand["venue"], hand["table"], hand["day"], hand["month"], hand["year"]))

        # Ensure "winnings" exists
        winnings_list = hand.get("winnings", [0] * len(hand["players"]))

        # Insert into players table
        for i, player in enumerate(hand["players"]):
            cursor.execute("INSERT OR IGNORE INTO players VALUES (?, ?, ?, ?, ?)",
                           (hand["hand"], player.strip("'"), i+1, hand["starting_stacks"][i], winnings_list[i]))

        # Insert into actions table
        for action in hand["actions"]:
            cursor.execute("INSERT INTO actions (hand_id, action) VALUES (?, ?)", (int(hand["hand"]), action))


# Commit and close
conn.commit()
conn.close()

print(f"✅ Successfully refreshed database with {len(phhs_files)} files.")

# Connect to database
DB_NAME = "poker.db"
conn = sqlite3.connect(DB_NAME)

# Fetch VPIP, PFR, Aggression Factor, and Showdown Win %
query = """
SELECT p.player_id, 
       COUNT(DISTINCT p.hand_id) AS total_hands,
       
       -- VPIP Calculation
       COUNT(DISTINCT CASE WHEN a.action LIKE '% cc%'  
                            OR a.action LIKE '% limp%' 
                            OR a.action LIKE '% cbr%' 
                            OR a.action LIKE '% all-in%' 
                            THEN p.hand_id END) AS vpip_hands,
       
       -- PFR Calculation
       COUNT(DISTINCT CASE WHEN a.action LIKE '% all-in%' 
                            OR a.action LIKE '% raise%' 
                            OR a.action LIKE '% bet%' 
                            THEN p.hand_id END) AS pfr_hands,

       -- Aggressive Actions (Bets, Raises, All-ins)
       COALESCE(COUNT(CASE WHEN a.action LIKE '% cbr%' 
                            OR a.action LIKE '% bet%' 
                            OR a.action LIKE '% raise%' 
                            OR a.action LIKE '% all-in%' THEN 1 END), 0) AS aggressive_actions,
       
       -- Passive Actions (Calls, Folds)
       COALESCE(COUNT(CASE WHEN a.action LIKE '% f%'
                            OR a.action LIKE '% limp%'
                            OR a.action LIKE '% cc%' THEN 1 END), 0) AS passive_actions,


       -- Showdown Win Percentage
       (COUNT(DISTINCT CASE WHEN p.winnings > 0 THEN p.hand_id END) * 100.0 / 
        NULLIF(COUNT(DISTINCT p.hand_id), 0)) AS showdown_win_percent

FROM players p
LEFT JOIN actions a ON p.hand_id = a.hand_id
WHERE a.action IS NOT NULL
GROUP BY p.player_id
HAVING COUNT(DISTINCT p.hand_id) > 10
ORDER BY vpip_hands DESC;
"""

# Load data
conn = sqlite3.connect("poker.db")
df = pd.read_sql_query(query, conn)

conn.close()


df["vpip_percent"] = (df["vpip_hands"] / df["total_hands"]) * 100
df["total_actions"] = (df["passive_actions"]) + (df["aggressive_actions"])
df["pfr_percent"] = (df["passive_actions"] / df["total_actions"]) * 100

# 📌 Drop unnecessary columns
df = df.drop(columns=["vpip_hands", "pfr_hands", "total_hands"]).dropna()

# 📌 Standardize features for clustering
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df.iloc[:, 1:])  # Exclude player_id

# 📌 Apply K-Means Clustering
kmeans = KMeans(n_clusters=4, random_state=42)
df["cluster"] = kmeans.fit_predict(X_scaled)

# 📌 Define cluster labels
cluster_labels = {
    0: "Tight Aggressive (TAG)", 
    1: "Tight Passive (NIT)", 
    2: "Loose Aggressive (LAG)", 
    3: "Loose Passive (Calling Station)"
}
df["player_type"] = df["cluster"].map(cluster_labels)

# 📌 Scatter Plot (VPIP vs. PFR)
plt.figure(figsize=(10, 6))
scatter = plt.scatter(df["vpip_percent"], df["pfr_percent"], c=df["cluster"], cmap="viridis", alpha=0.7, edgecolors="k")

# 📌 Create a legend with text labels on the side
legend_labels = [f"Cluster {i}: {label}" for i, label in cluster_labels.items()]
legend_colors = [plt.cm.viridis(i / 3) for i in range(4)]  # Adjust colors to match colormap

# 📌 Add legend manually
for i, (color, label) in enumerate(zip(legend_colors, legend_labels)):
    plt.scatter([], [], c=[color], label=label)  # Invisible points for legend

plt.legend(title="Cluster Labels", loc="upper left", fontsize=10, frameon=False)

plt.xlabel("VPIP %")
plt.ylabel("Aggression %")
plt.title("Poker Player Clustering (VPIP vs Aggression)")

plt.colorbar(scatter, label="Cluster")  # Keep colorbar for reference

plt.show()
