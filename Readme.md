# Rock-Paper-Scissors-PLUS Game Referee

## Overview
A minimal AI-powered game referee built with Google ADK that manages a Rock-Paper-Scissors variant with a strategic "bomb" mechanic.

## State Model

### State Structure
```python
game_state = {
    "round": int,              # Current round (0-3)
    "max_rounds": 3,           # Fixed game length
    "user_score": int,         # User's wins
    "bot_score": int,          # Bot's wins
    "user_bomb_used": bool,    # Bomb usage tracking
    "bot_bomb_used": bool,     # Bomb usage tracking
    "game_over": bool,         # Terminal flag
    "history": []              # Round records
}
```

### Design Rationale
State is stored in a **module-level dictionary** rather than in the AI's conversation context. This design ensures:
- **Deterministic behavior**: Game logic cannot be influenced by AI hallucinations
- **Persistent state**: Data survives across multiple AI interactions
- **Easy debugging**: State can be inspected and validated independently
- **Separation of concerns**: Game state is decoupled from conversation flow

## Agent/Tool Design

### Architecture Overview

```
┌─────────────┐
│    USER     │ ← Natural language input
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         AI AGENT (Gemini)           │
│  • Understands user intent          │
│  • Decides when to call tools       │
│  • Generates natural responses      │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│           TOOLS (Python)            │
│  • update_game_state()              │
│  • get_game_state()                 │
│  • validate_user_move()             │
│  • determine_round_winner()         │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│        GAME STATE (Dict)            │
│  Persistent storage of game data    │
└─────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Why This Layer |
|-----------|---------------|----------------|
| **AI Agent** | Intent understanding, conversation generation | Good at: Natural language, context. Bad at: Exact calculations |
| **Tools** | State mutation, rule enforcement | Good at: Deterministic logic. Bad at: Understanding messy input |
| **Game Logic Functions** | Calculate winners, validate moves | Pure functions, easily testable |
| **State Dictionary** | Persist data | AI has no memory; we need external storage |

### Tool Definitions

#### 1. `update_game_state(user_move, bot_move)`
**Purpose**: Main state mutation tool
- Increments round counter
- Tracks bomb usage
- Calculates round winner via `determine_round_winner()`
- Updates scores
- Checks terminal conditions
- Returns structured result to AI

**Why it's a tool**: The AI needs to trigger state changes but shouldn't implement the logic itself.

#### 2. `get_game_state()`
**Purpose**: Read-only state access
- Provides current game status without side effects
- Allows AI to make context-aware decisions

**Why it's a tool**: Gives AI visibility into state without allowing mutations.

## Tradeoffs Made

### 1. Global State vs. Class-Based Design
**Chosen**: Module-level `game_state` dictionary  
**Alternative**: Game class with encapsulated state  
**Rationale**: For a single-user CLI game, global state is simpler and meets requirements. In production, I'd use a class for better encapsulation and to support multiple concurrent games.

### 2. Bot Strategy Complexity
**Chosen**: Simple random strategy with basic bomb timing  
**Alternative**: Pattern recognition, counter-strategy AI  
**Rationale**: Assignment focuses on architecture, not game AI. A sophisticated bot would add complexity without demonstrating ADK understanding.

### 3. Validation Location
**Chosen**: Validation in Python before tool call  
**Alternative**: Let AI validate through a separate tool  
**Rationale**: Input validation is deterministic - Python guarantees correctness. This prevents the AI from occasionally accepting invalid inputs.

### 4. Error Handling
**Chosen**: Try-catch at top level, graceful degradation  
**Alternative**: Comprehensive error handling at every API call  
**Rationale**: For a demonstration, basic error handling suffices. Production code would add retry logic, rate limiting, and fallback responses.

### 5. Conversation History Management
**Chosen**: Maintain full conversation history  
**Alternative**: Summarize/truncate after N messages  
**Rationale**: With only 3 rounds, history stays small. For longer games, I'd implement sliding window or summarization to manage context length.

## What I Would Improve With More Time

### 1. **State Management**
- **Refactor to class-based design**:
  ```python
  class GameSession:
      def __init__(self):
          self.state = {...}
      
      def play_round(self, user_move, bot_move):
          # Immutable state updates
          return new_state
  ```
- **Benefits**: Better encapsulation, testability, support for multiple games

### 2. **Testing**
- **Unit tests** for all game logic functions:
  - `test_determine_winner()` covering all move combinations
  - `test_validate_move()` with edge cases
  - `test_bomb_usage_enforcement()`
- **Integration tests** for tool execution flow
- **Mock AI responses** for deterministic testing

### 3. **Bot Intelligence**
- **Pattern analysis**: Track user's move frequency
- **Counter-strategy**: If user plays rock 3 times, play paper
- **Adaptive bomb timing**: Use bomb when it maximizes expected value

### 4. **Error Handling & Resilience**
- **Retry logic** for transient API failures
- **Rate limiting** awareness with exponential backoff
- **Graceful degradation**: Fall back to rule-based responses if AI unavailable
- **Input sanitization**: Handle Unicode, special characters

### 5. **Observability**
- **Structured logging** (JSON format):
  ```python
  logger.info("round_complete", round=3, winner="user", moves={...})
  ```
- **Metrics tracking**: API latency, tool call frequency, win rates
- **Debug mode toggle**: Enable/disable verbose output via CLI flag

### 6. **User Experience**
- **Move suggestions**: "Available moves: rock, paper, scissors" + bomb indicator
- **Visual feedback**: Emojis (✊📄✌️💣), color-coded output
- **Undo last move**: Allow fixing accidental inputs (would require state history)
- **Replay option**: "Play again? (y/n)" at game end

### 7. **Advanced ADK Features**
- **Structured outputs** with JSON schema validation:
  ```python
  response_schema = {
      "type": "object",
      "properties": {
          "explanation": {"type": "string"},
          "score_update": {"type": "string"}
      }
  }
  ```
- **Multi-turn planning**: AI decides strategy across rounds
- **Function calling enforcement**: Use `tool_choice` parameter to guarantee tool usage

## Key Design Decisions

### Why Tools Over Prompt-Based State?
**Decision**: Store state in Python, not in AI conversation  
**Reasoning**: 
- AI can hallucinate or misinterpret state from prompts
- Python guarantees correctness of critical game logic
- State is queryable and debuggable outside AI context

### Why Separate Validation and Winner Determination?
**Decision**: Two separate functions instead of one monolithic tool  
**Reasoning**:
- **Single Responsibility Principle**: Each function has one job
- **Testability**: Can unit test `validate_user_move()` independently
- **Reusability**: Functions can be called from different contexts

### Why Bot Move Generated in Python?
**Decision**: `choose_bot_move()` in Python, not AI-generated  
**Reasoning**:
- Ensures bot never cheats (doesn't see user's move first)
- Deterministic for debugging
- Can implement provably fair strategies

## Technical Notes

### Google ADK Usage
- **Model**: `gemini-1.5-flash` (higher free tier limits than 2.0-flash-exp)
- **Function Calling**: Used ADK's native function declaration syntax
- **Conversation History**: Maintained full history for context
- **System Instructions**: Defined referee behavior upfront

### Dependencies
```bash
pip install google-genai
```

### Running the Game
```bash
python game.py
```

## Architecture Validation

This design successfully separates:
1. ✅ **Intent Understanding**: AI interprets "rooock" → "rock"
2. ✅ **Game Logic**: Python enforces rules deterministically  
3. ✅ **Response Generation**: AI creates engaging, context-aware messages

The clean separation means each layer can be tested, modified, or replaced independently.

---

**Total Development Time**: ~3 hours  
**Lines of Code**: ~300 (excluding comments)  
**Test Coverage**: Manual testing of all edge cases (see test scenarios below)

## Test Scenarios Verified

- ✅ Normal game (3 rounds, no bombs)
- ✅ User bomb usage (once allowed, twice rejected)
- ✅ Bot bomb usage (strategic timing)
- ✅ Invalid inputs (handled gracefully)
- ✅ Bomb vs. bomb (draw)
- ✅ All win conditions (rock/paper/scissors combos)
- ✅ Game auto-ends after round 3
- ✅ Final winner declared correctly