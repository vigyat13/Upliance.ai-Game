import json
import random
from google import genai
from google.genai import types

# ============================================
# CONFIGURATION
# ============================================

API_KEY = "your_api_key_here"

# Initialize the AI client
client = genai.Client(api_key=API_KEY)

# ============================================
# GAME STATE (The Scoreboard)
# ============================================

game_state = {
    "round": 0,
    "max_rounds": 3,
    "user_score": 0,
    "bot_score": 0,
    "user_bomb_used": False,
    "bot_bomb_used": False,
    "game_over": False,
    "history": []
}

# ============================================
# GAME LOGIC (Pure Python - No AI)
# ============================================

def validate_user_move(user_input):
    """Check if user input is valid and clean it up."""
    move = user_input.lower().strip()
    valid_moves = ["rock", "paper", "scissors", "bomb"]
    
    if move not in valid_moves:
        print(f"  [DEBUG] '{user_input}' is not a valid move")
        return (False, "invalid")
    
    if move == "bomb" and game_state["user_bomb_used"]:
        print(f"  [DEBUG] User tried to use bomb twice!")
        return (False, "invalid")
    
    print(f"  [DEBUG] Move '{move}' is valid ✓")
    return (True, move)


def determine_round_winner(move1, move2):
    """Figure out who wins the round."""
    if move1 == "invalid":
        return "bot"
    
    if move1 == move2:
        return "draw"
    
    if move1 == "bomb":
        return "user"
    if move2 == "bomb":
        return "bot"
    
    wins_against = {
        "rock": "scissors",
        "paper": "rock",
        "scissors": "paper"
    }
    
    if wins_against[move1] == move2:
        return "user"
    else:
        return "bot"


def choose_bot_move():
    """Bot decides what to play."""
    can_use_bomb = not game_state["bot_bomb_used"]
    
    if can_use_bomb and game_state["round"] == 2:
        if game_state["bot_score"] < game_state["user_score"]:
            print(f"  [DEBUG] Bot using bomb strategically!")
            return "bomb"
    
    moves = ["rock", "paper", "scissors"]
    
    if can_use_bomb and game_state["round"] == 1 and random.random() < 0.2:
        return "bomb"
    
    return random.choice(moves)


# ============================================
# TOOLS
# ============================================

def tool_update_game(user_move, bot_move):
    """Update game state after a round."""
    print(f"\n  [TOOL CALLED] update_game_state(user={user_move}, bot={bot_move})")
    
    game_state["round"] += 1
    
    if user_move == "bomb":
        game_state["user_bomb_used"] = True
    if bot_move == "bomb":
        game_state["bot_bomb_used"] = True
    
    winner = determine_round_winner(user_move, bot_move)
    
    if winner == "user":
        game_state["user_score"] += 1
    elif winner == "bot":
        game_state["bot_score"] += 1
    
    if game_state["round"] >= game_state["max_rounds"]:
        game_state["game_over"] = True
    
    round_record = {
        "round": game_state["round"],
        "user_move": user_move,
        "bot_move": bot_move,
        "winner": winner,
        "score_after": f"{game_state['user_score']}-{game_state['bot_score']}"
    }
    game_state["history"].append(round_record)
    
    result = {
        "success": True,
        "round_number": game_state["round"],
        "user_move": user_move,
        "bot_move": bot_move,
        "round_winner": winner,
        "user_score": game_state["user_score"],
        "bot_score": game_state["bot_score"],
        "game_over": game_state["game_over"]
    }
    
    print(f"  [TOOL RESULT] Round {result['round_number']}: {winner} wins!")
    return result


def tool_get_state():
    """Get current game state."""
    print(f"  [TOOL CALLED] get_game_state()")
    return {
        "round": game_state["round"],
        "max_rounds": game_state["max_rounds"],
        "user_score": game_state["user_score"],
        "bot_score": game_state["bot_score"],
        "user_bomb_used": game_state["user_bomb_used"],
        "game_over": game_state["game_over"]
    }


def execute_tool(function_call):
    """Execute tool requested by AI."""
    tool_name = function_call.name
    
    if tool_name == "update_game_state":
        args = function_call.args
        user_move = args.get("user_move", "invalid")
        bot_move = args.get("bot_move", "rock")
        result = tool_update_game(user_move, bot_move)
        return json.dumps(result)
    
    elif tool_name == "get_game_state":
        result = tool_get_state()
        return json.dumps(result)
    
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ============================================
# AI CONFIGURATION
# ============================================

TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="update_game_state",
            description="Updates game state after a round. Call this when user makes a move.",
            parameters={
                "type": "object",
                "properties": {
                    "user_move": {
                        "type": "string",
                        "description": "User's move: rock, paper, scissors, bomb, or invalid",
                        "enum": ["rock", "paper", "scissors", "bomb", "invalid"]
                    },
                    "bot_move": {
                        "type": "string",
                        "description": "Bot's move: rock, paper, scissors, or bomb",
                        "enum": ["rock", "paper", "scissors", "bomb"]
                    }
                },
                "required": ["user_move", "bot_move"]
            }
        ),
        types.FunctionDeclaration(
            name="get_game_state",
            description="Get current game state.",
            parameters={"type": "object", "properties": {}}
        )
    ]
)

SYSTEM_INSTRUCTION = """You are a friendly game referee for Rock-Paper-Scissors-PLUS.

RULES (explain in ≤5 lines at start):
• Best of 3 rounds. Valid moves: rock, paper, scissors, bomb
• Standard RPS rules. Bomb beats all except bomb (draw with bomb)
• Each player can use bomb ONCE per game
• Invalid input wastes the round

YOUR JOB:
1. When user inputs a move, call update_game_state with user's move and your chosen move
2. Clearly explain each round: "Round X: You played Y, I played Z. [winner] wins!"
3. Show score after each round: "Score: You X - Me Y"
4. After round 3, declare final winner and end game
5. Be friendly and encouraging!

IMPORTANT:
- Always call update_game_state for each user move
- Game MUST end after round 3 automatically
- Be concise but friendly"""


# ============================================
# MAIN GAME LOOP
# ============================================

def play_game():
    """Main function that runs the game."""
    print("=" * 60)
    print("🎮  ROCK-PAPER-SCISSORS-PLUS GAME REFEREE")
    print("=" * 60)
    print("Using: Gemini 1.5 Flash (Higher free tier limits)")
    print("Debug mode: ON\n")
    
    conversation = []
    
    # === STEP 1: Initial greeting ===
    print("🤖 Starting game...\n")
    
    initial_prompt = "Start the game! Greet the player and explain the rules in 5 lines or less."
    conversation.append({
        "role": "user",
        "parts": [{"text": initial_prompt}]
    })
    

    response = client.models.generate_content(
        model="gemini-1.5-flash",  
        contents=conversation,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[TOOLS],
            temperature=0.7
        )
    )
    
    print(f"REFEREE: {response.text}\n")
    conversation.append({
        "role": "model",
        "parts": [{"text": response.text}]
    })
    
    # === STEP 2: Game loop ===
    while not game_state["game_over"]:
        print("-" * 60)
        user_input = input(f"Round {game_state['round'] + 1} - Your move: ").strip()
        print()
        
        if not user_input:
            user_input = "invalid"
        
        is_valid, clean_move = validate_user_move(user_input)
        bot_move = choose_bot_move()
        print(f"  [DEBUG] Bot chose: {bot_move}")
        
        user_message = f"My move: {user_input}"
        conversation.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })
        
       
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=conversation,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[TOOLS],
                temperature=0.7
            )
        )
        
        tool_calls = []
        response_text = ""
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                
                if fc.name == "update_game_state":
                    fc.args["bot_move"] = bot_move
                    fc.args["user_move"] = clean_move
                
                tool_result = execute_tool(fc)
                
                tool_calls.append({
                    "function_call": fc,
                    "result": tool_result
                })
            
            if hasattr(part, 'text') and part.text:
                response_text += part.text
        
        if tool_calls:
            conversation.append({
                "role": "model",
                "parts": response.candidates[0].content.parts
            })
            
            tool_response_parts = []
            for tc in tool_calls:
                tool_response_parts.append({
                    "function_response": {
                        "name": tc["function_call"].name,
                        "response": {"result": tc["result"]}
                    }
                })
            
            conversation.append({
                "role": "user",
                "parts": tool_response_parts
            })
            
            
            final_response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=conversation,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[TOOLS],
                    temperature=0.7
                )
            )
            
            print(f"REFEREE: {final_response.text}\n")
            conversation.append({
                "role": "model",
                "parts": [{"text": final_response.text}]
            })
        else:
            print(f"REFEREE: {response_text}\n")
            conversation.append({
                "role": "model",
                "parts": [{"text": response_text}]
            })
    
    # === STEP 3: Game over ===
    print("=" * 60)
    print("🏁 GAME OVER")
    print("=" * 60)
    print(f"\nFinal Score: You {game_state['user_score']} - Bot {game_state['bot_score']}")
    
    if game_state['user_score'] > game_state['bot_score']:
        print("🎉 YOU WIN! Congratulations!")
    elif game_state['bot_score'] > game_state['user_score']:
        print("🤖 BOT WINS! Better luck next time!")
    else:
        print("🤝 IT'S A DRAW! Well played!")
    
    print("\nGame History:")
    for record in game_state['history']:
        print(f"  Round {record['round']}: You {record['user_move']} vs Bot {record['bot_move']} → {record['winner']} wins")


# ============================================
# RUN THE GAME
# ============================================

if __name__ == "__main__":
    if API_KEY == "your_api_key_here" or not API_KEY:
        print("❌ ERROR: Please set your Google API key!")
        print("Get one from: https://aistudio.google.com/app/apikey")
    else:
        try:
            play_game()
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("\nIf you see quota errors:")
            print("1. Wait 30 seconds and try again")
            print("2. Check usage at: https://ai.dev/usage")
            print("3. Try creating a new API key")