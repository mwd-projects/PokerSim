import os
import sys
import random
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

# ✅ Get the correct base directory where main.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Define paths for images
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CARDS_DIR = os.path.join(IMAGES_DIR, "PNG-cards-1.3")  # Folder containing card images

# ----- Poker Card Deck -----
SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"]



# ----- Poker Hand Ranges -----
POKER_RANGES = {
    "UTG": {  # 15% Opening Range
        "AA", "KK", "QQ", "JJ", "TT",
        "AKs", "AQs", "AJs", "KQs", "ATs",
        "AKo", "AQo"
    },
    "MP": {  # 20% Opening Range
        "AA", "KK", "QQ", "JJ", "TT", "99",
        "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs",
        "AKo", "AQo", "AJo", "KQo"
    },
    "CO": {  # 25% Opening Range
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
        "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs",
        "A5s", "A4s", "A3s", "A2s",
        "AKo", "AQo", "AJo", "KQo", "QJo", "JTo"
    },
    "BTN": {  # 30% Opening Range
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66",
        "AKs", "AQs", "AJs", "ATs", "A9s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s",
        "A5s", "A4s", "A3s", "A2s",
        "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo", "JTo"
    },
    "SB": {  # 35% Opening Range
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55",
        "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s", "87s",
        "A5s", "A4s", "A3s", "A2s",
        "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo", "JTo"
    },
    "BB": {  # General BB Opening Range (Very Wide)
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
        "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
        "KQs", "KJs", "KTs", "K9s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "T8s", "98s", "97s", "87s", "76s", "65s", "54s",
        "AKo", "AQo", "AJo", "ATo", "A9o", "KQo", "KJo", "KTo", "QJo", "JTo", "T9o"
    }
}

class PlayerStats:
    def __init__(self):
        self.total_attempts = 0
        self.correct_attempts = 0

    def update_stats(self, correct):
        """Updates the accuracy tracking."""
        self.total_attempts += 1
        if correct:
            self.correct_attempts += 1

    def get_accuracy(self):
        """Returns accuracy percentage."""
        if self.total_attempts == 0:
            return "0.0%"
        return f"{(self.correct_attempts / self.total_attempts) * 100:.1f}%"

    def reset_stats(self):
        """Resets the tracking stats."""
        self.total_attempts = 0
        self.correct_attempts = 0

# Global stats object
player_stats = PlayerStats()

class PokerGame(QWidget):
    def __init__(self):
        super().__init__()
        self.correct_decision = None
        self.total_attempts = 0
        self.correct_attempts = 0
        self.RANK_ORDER = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10,
            "J": 11, "Q": 12, "K": 13, "A": 14
        }  # 🃏 Ace is highest
        self.initUI()

    def combine_hand(self, card1, card2):
        """Takes two formatted card strings (e.g., 'Js', 'Ad') and returns proper poker hand notation (e.g., 'AJo')."""
        rank1, suit1 = card1[:-1], card1[-1]  # Extract rank and suit
        rank2, suit2 = card2[:-1], card2[-1]

        # ✅ Sort by RANK_ORDER instead of using `max()`
        if self.RANK_ORDER[rank1] > self.RANK_ORDER[rank2]:  # rank1 is higher
            high_rank, low_rank = rank1, rank2
        else:
            high_rank, low_rank = rank2, rank1

        # ✅ Handle Pocket Pairs (e.g., AA, QQ, 99)
        if high_rank == low_rank:
            return high_rank + low_rank  # No 's' or 'o' for pocket pairs

        # Determine suited or offsuit
        return f"{high_rank}{low_rank}s" if suit1 == suit2 else f"{high_rank}{low_rank}o"


    def normalize_hand(self, hand):
        """Ensures the hand notation is always in the correct order (high card first)."""
        if hand[-1] in {"s", "o"}:  # Suited or offsuit hands
            ranks = [hand[0], hand[1]]  # Extract the two ranks
            suit = hand[-1]  # Get suit indicator ("s" or "o")

            # ✅ Sort using `self.RANK_ORDER`
            sorted_ranks = sorted(ranks, key=lambda r: self.RANK_ORDER[r], reverse=True)
            return f"{sorted_ranks[0]}{sorted_ranks[1]}{suit}"
        else:  # Pocket pairs (e.g., "JJ")
            return hand



    def format_card_name(self, card_filename):
        """Converts filenames (e.g., 'jack_of_hearts.png') to poker notation (e.g., 'Js')."""
        rank_map = {
            "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "T",
            "jack": "J", "queen": "Q", "king": "K", "ace": "A"
        }

        parts = card_filename.replace(".png", "").split("_of_")
        rank = rank_map[parts[0]]  # Convert to shorthand notation (J, Q, K, A, T)
        suit = parts[1][0].upper()  # Convert first letter of suit (H, D, C, S)
        
        return f"{rank}{suit}"


    def poker_ai_decision(self, position, player_hand):
        """Determines whether to Raise, Call, or Fold based on position and hand range."""
        normalized_hand = self.normalize_hand(player_hand)  # Ensure hand is formatted correctly

        print(f"🃏 DEBUG: AI Decision Check - Position: {position}, Hand: {player_hand}, Normalized: {normalized_hand}")

        if position not in POKER_RANGES:
            return "Fold"  # Default action if position is invalid
        
        return "Raise" if normalized_hand in POKER_RANGES[position] else "Fold"

    def initUI(self):
        self.setWindowTitle("Poker Table")
        self.setGeometry(100, 100, 1000, 700)  # Window size

        # ----- Load Table Image (Background) -----
        self.table_label = QLabel(self)
        table_path = os.path.join(IMAGES_DIR, "table.png")

        if os.path.exists(table_path):
            table_pixmap = QPixmap(table_path).scaled(1000, 600, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            self.table_label.setPixmap(table_pixmap)
            self.table_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            print(f"Error: Table image not found at {table_path}")

        self.table_label.setGeometry(0, 0, 1000, 600)  # Set table image to cover the top part of the window

        # ----- Player Cards (Positioned on Table) -----
        self.card1_label = QLabel(self)
        self.card2_label = QLabel(self)

        self.card1_label.setFixedSize(80, 120)
        self.card2_label.setFixedSize(80, 120)

        # Initial placeholder positions (will be updated on deal)
        self.card1_label.move(415, 450)  # Move onto the table
        self.card2_label.move(505, 450)  # Next to the first card

        # ----- Deal Button -----
        self.deal_button = QPushButton("Deal Cards", self)
        self.deal_button.setFixedSize(150, 40)
        self.deal_button.move(425, 620)
        self.deal_button.clicked.connect(self.deal_cards)
        self.deal_button.setStyleSheet("font-size: 16px;")

        # ----- AI Decision Label -----
        self.info_label = QLabel("AI Decision: Waiting...", self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 18px; color: white;")
        self.info_label.setGeometry(300, 570, 400, 30)

        # ----- Accuracy Label -----
        self.accuracy_label = QLabel("Accuracy: 0.0%", self)
        self.accuracy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accuracy_label.setStyleSheet("font-size: 16px; color: yellow;")
        self.accuracy_label.setGeometry(750, 570, 200, 30)

        # ----- Player Action Buttons -----
        self.fold_button = QPushButton("Fold", self)
        self.call_button = QPushButton("Call", self)
        self.raise_button = QPushButton("Raise", self)
        self.reset_button = QPushButton("Reset", self)

        self.fold_button.setGeometry(300, 660, 100, 40)
        self.call_button.setGeometry(425, 660, 100, 40)
        self.raise_button.setGeometry(550, 660, 100, 40)
        self.reset_button.setGeometry(675, 660, 100, 40)

        self.fold_button.clicked.connect(lambda: self.player_action("Fold"))
        self.call_button.clicked.connect(lambda: self.player_action("Call"))
        self.raise_button.clicked.connect(lambda: self.player_action("Raise"))
        self.reset_button.clicked.connect(self.reset_stats)

    def deal_cards(self):
        """Randomly assigns two cards to the player and suggests an action based on poker ranges."""
        deck = [f"{rank}_of_{suit}.png" for suit in SUITS for rank in RANKS]
        player_cards = random.sample(deck, 2)  # Pick two unique cards

        # Convert filenames to poker notation (e.g., "ace_of_hearts.png" → "Ah")
        card1 = self.format_card_name(player_cards[0])  # "Js"
        card2 = self.format_card_name(player_cards[1])  # "Ad"
        
        # ✅ Combine cards into a proper poker hand format ("AJo" or "AJs")
        formatted_hand = self.combine_hand(card1, card2)

        # Determine position (For now, assign randomly)
        position = random.choice(list(POKER_RANGES.keys()))

        # Get AI Decision
        self.correct_decision = self.poker_ai_decision(position, formatted_hand)

        # Construct relative paths for card images
        card1_path = os.path.join(CARDS_DIR, player_cards[0])
        card2_path = os.path.join(CARDS_DIR, player_cards[1])

        if os.path.exists(card1_path) and os.path.exists(card2_path):
            self.card1_label.setPixmap(QPixmap(card1_path).scaled(80, 120))
            self.card2_label.setPixmap(QPixmap(card2_path).scaled(80, 120))
            self.card1_label.show()
            self.card2_label.show()

            # Display the decision on the screen
            self.info_label.setText(f"Position: {position} | Hand: {formatted_hand} | AI Suggests: ???")
        else:
            print(f"Error: One or both card images not found: {card1_path}, {card2_path}")

    def update_accuracy(self, correct):
        """Updates and displays the accuracy percentage."""
        self.total_attempts += 1
        if correct:
            self.correct_attempts += 1

    def player_action(self, action):
        """Handles player's action and checks if they made the correct choice."""
        if self.correct_decision:
            correct = action == self.correct_decision
            self.total_attempts += 1
            self.correct_attempts += int(correct)

            # Calculate accuracy
            accuracy = (self.correct_attempts / self.total_attempts) * 100

                # Update GUI labels
            if correct:
                self.info_label.setText(f"✅ Correct! AI also suggested: {self.correct_decision}")
            else:
                self.info_label.setText(f"❌ Wrong! AI suggested: {self.correct_decision}")

            self.accuracy_label.setText(f"Accuracy: {accuracy:.01f}%")

        else:
            self.info_label.setText("⚠ No hand dealt yet!")

    def reset_stats(self):
        """Resets accuracy tracking and updates display."""
        self.total_attempts = 0
        self.correct_attempts = 0
        print("🔄 Accuracy reset!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    poker_game = PokerGame()
    poker_game.show()
    sys.exit(app.exec())
