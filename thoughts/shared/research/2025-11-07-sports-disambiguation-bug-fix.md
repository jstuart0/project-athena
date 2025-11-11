# Sports Team Disambiguation Bug - CRITICAL FIX NEEDED

**Date:** November 7, 2025
**Priority:** HIGH
**Impact:** User gets wrong sport's scores for 4 major teams

---

## Problem Statement

The `sports_client.py` team aliases dictionary has **duplicate keys** that cause incorrect sports scores to be returned. When a user asks for "Giants score" (meaning NFL football), they get San Francisco Giants baseball score instead.

### Root Cause

Python dictionaries silently overwrite duplicate keys with the last value. The `team_aliases` dictionary defines the same key multiple times for different sports:

```python
team_aliases = {
    # NFL (Line 49)
    'giants': 'New York Giants',

    # ... 100+ other teams ...

    # MLB (Line 161) ← THIS OVERWRITES LINE 49
    'giants': 'San Francisco Giants',
}
```

**Result:** `team_aliases['giants']` always returns `'San Francisco Giants'` (MLB), never `'New York Giants'` (NFL).

---

## Affected Teams (4 Total)

| Ambiguous Key | Sport 1 (Lost) | Sport 2 (Wins) |
|---------------|----------------|----------------|
| `giants` | NFL New York Giants | **MLB San Francisco Giants** |
| `cardinals` | NFL Arizona Cardinals | **MLB St. Louis Cardinals** |
| `panthers` | NFL Carolina Panthers | **NHL Florida Panthers** |
| `spurs` | NBA San Antonio Spurs | **EPL Tottenham Spurs** |

**User Impact:**
- Asking for "Giants score" during NFL season → Gets baseball score ❌
- Asking for "Cardinals game" → Gets baseball, not football ❌
- Asking for "Panthers score" → Gets hockey, not football ❌
- Asking for "Spurs game" → Gets English soccer, not NBA ❌

---

## Real-World Example (User Report)

**User Query:** "What was the score of the Giants game?" (meaning NFL football)

**Expected:** New York Giants 24, Dallas Cowboys 17 (NFL)

**Actual Response:** "The San Francisco Giants won 4 to 0 against the Colorado Rockies" (MLB)

**Follow-up Query:** "I mean football Giants"

**Actual Response:** Still gives baseball score because "football giants" contains "giants" key, which maps to MLB.

---

## Solution Options

### Option 1: Remove Ambiguous Keys (Quick Fix)

**Change:**
```python
# BEFORE
'giants': 'New York Giants',     # Line 49 (overwritten)
'giants': 'San Francisco Giants', # Line 161 (wins)

# AFTER - Remove generic keys, force specific aliases
# 'giants': ...  ← DELETE both entries
'ny giants': 'New York Giants',
'new york giants': 'New York Giants',
'football giants': 'New York Giants',
'sf giants': 'San Francisco Giants',
'san francisco giants': 'San Francisco Giants',
'baseball giants': 'San Francisco Giants',
```

**Pros:**
- Simple fix, no code logic changes
- Forces users to be specific

**Cons:**
- Breaks existing queries using just "giants"
- User has to learn new phrasing

---

### Option 2: Sport Context Detection (Recommended)

**Implementation:**

```python
def extract_team_name(self, query: str) -> Optional[str]:
    """
    Extract team name from user query with sport context disambiguation
    """
    query_lower = query.lower()

    # Detect sport/league keywords
    sport_context = self._detect_sport_context(query_lower)

    # Check for ambiguous team names
    ambiguous_teams = {
        'giants': {
            'nfl': 'ny giants',
            'mlb': 'sf giants',
            'default_season': 'nfl'  # Sept-Feb = NFL, Mar-Aug = MLB
        },
        'cardinals': {
            'nfl': 'az cardinals',
            'mlb': 'stl cardinals',
            'default_season': 'nfl'
        },
        'panthers': {
            'nfl': 'carolina panthers',
            'nhl': 'florida panthers',
            'default_season': 'nfl'
        },
        'spurs': {
            'nba': 'san antonio spurs',
            'epl': 'tottenham',
            'default_season': 'nba'
        }
    }

    # Extract base team name
    for team_name in ambiguous_teams.keys():
        if team_name in query_lower:
            team_config = ambiguous_teams[team_name]

            # Use sport context if detected
            if sport_context and sport_context in team_config:
                return team_config[sport_context]

            # Use seasonal default
            return self._get_seasonal_default(team_name, team_config)

    # ... rest of extraction logic

def _detect_sport_context(self, query: str) -> Optional[str]:
    """Detect sport/league from query keywords"""
    sport_keywords = {
        'nfl': ['football', 'nfl', 'touchdown', 'quarterback'],
        'mlb': ['baseball', 'mlb', 'innings', 'pitcher', 'home run'],
        'nba': ['basketball', 'nba', 'points', 'rebounds'],
        'nhl': ['hockey', 'nhl', 'puck', 'ice'],
        'epl': ['soccer', 'football', 'premier league', 'epl', 'goal']
    }

    for sport, keywords in sport_keywords.items():
        if any(kw in query for kw in keywords):
            return sport

    return None

def _get_seasonal_default(self, team_name: str, config: dict) -> str:
    """Return appropriate team based on current season"""
    month = datetime.now().month

    if team_name == 'giants':
        # NFL season: Sept-Feb (months 9-12, 1-2)
        if month >= 9 or month <= 2:
            return config['nfl']  # 'ny giants'
        else:
            return config['mlb']  # 'sf giants'

    elif team_name == 'cardinals':
        if month >= 9 or month <= 2:
            return config['nfl']
        else:
            return config['mlb']

    elif team_name == 'panthers':
        if month >= 9 or month <= 2:
            return config['nfl']
        else:
            return config['nhl']

    elif team_name == 'spurs':
        # NBA year-round, EPL Aug-May
        if month >= 8 or month <= 5:
            return config['epl']  # European season
        else:
            return config['nba']

    return config.get('default_season', team_name)
```

**Update team_aliases dictionary:**
```python
team_aliases = {
    # NFL
    'ny giants': 'New York Giants',
    'new york giants': 'New York Giants',
    'az cardinals': 'Arizona Cardinals',
    'arizona cardinals': 'Arizona Cardinals',
    'carolina panthers': 'Carolina Panthers',

    # MLB
    'sf giants': 'San Francisco Giants',
    'san francisco giants': 'San Francisco Giants',
    'stl cardinals': 'St Louis Cardinals',
    'st louis cardinals': 'St Louis Cardinals',

    # NBA
    'san antonio spurs': 'San Antonio Spurs',
    'sa spurs': 'San Antonio Spurs',

    # NHL
    'florida panthers': 'Florida Panthers',

    # EPL
    'tottenham': 'Tottenham',
    'tottenham spurs': 'Tottenham',

    # ... keep all other existing entries
}
```

**Pros:**
- Handles ambiguous queries intelligently
- Seasonal defaults provide good UX
- Keyword detection adds precision

**Cons:**
- More complex implementation
- Requires testing edge cases

---

### Option 3: User Confirmation (Best UX, More Complex)

**Implementation:**

When ambiguous team detected and no sport context:

```python
def get_latest_score(self, team_name: str, sport_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Get latest score with disambiguation support
    """
    team_name_lower = team_name.lower()

    # Check if team is ambiguous
    if team_name_lower in ['giants', 'cardinals', 'panthers', 'spurs']:
        if not sport_hint:
            # Return disambiguation options
            return {
                "needs_clarification": True,
                "team": team_name_lower,
                "options": self._get_team_options(team_name_lower),
                "message": self._get_clarification_message(team_name_lower)
            }

    # ... normal processing

def _get_clarification_message(self, team: str) -> str:
    """Generate clarification question"""
    messages = {
        'giants': "Did you mean the New York Giants (NFL) or San Francisco Giants (MLB)?",
        'cardinals': "Did you mean the Arizona Cardinals (NFL) or St. Louis Cardinals (MLB)?",
        'panthers': "Did you mean the Carolina Panthers (NFL) or Florida Panthers (NHL)?",
        'spurs': "Did you mean the San Antonio Spurs (NBA) or Tottenham Spurs (soccer)?"
    }
    return messages.get(team, "Which team did you mean?")
```

**Update intent classifier to handle clarification:**

```python
def execute_intent(ha_client, intent: str, parameters: Optional[Dict[str, Any]]) -> str:
    """Execute intent with disambiguation support"""

    if intent == Intent.GET_SPORTS_SCORE:
        team_name = parameters.get('team_name') if parameters else None

        result = sports_client.get_latest_score(team_name)

        # Handle disambiguation
        if result.get('needs_clarification'):
            return result['message']  # Ask user to clarify

        # Format normal response
        return sports_client.format_score_response(result)
```

**Follow-up conversation:**
```
User: "What was the Giants score?"
Assistant: "Did you mean the New York Giants (NFL) or San Francisco Giants (MLB)?"
User: "NFL" or "Football" or "New York"
Assistant: [Fetch correct score]
```

**Pros:**
- Best user experience
- Clear disambiguation
- No guessing

**Cons:**
- Requires conversation state management
- Two-turn conversation (slower)
- More complex implementation

---

## Recommended Implementation Plan

### Phase 1: Immediate Fix (Option 1 + Seasonal Defaults)

**Steps:**
1. Remove all 4 duplicate keys from `team_aliases`
2. Add specific aliases for each team/sport combination
3. Implement seasonal defaults in `extract_team_name()`

**Time:** 30 minutes
**Risk:** Low
**Impact:** Fixes 90% of cases

### Phase 2: Smart Context Detection (Option 2)

**Steps:**
1. Implement `_detect_sport_context()` function
2. Update `extract_team_name()` to use sport hints
3. Add sport keyword detection
4. Test edge cases

**Time:** 2 hours
**Risk:** Medium
**Impact:** Fixes 99% of cases

### Phase 3: User Confirmation (Option 3) - Future Enhancement

**Steps:**
1. Implement conversation state management
2. Add clarification response format
3. Handle follow-up queries
4. Update voice pipeline to support multi-turn

**Time:** 4-6 hours
**Risk:** High (requires conversation state)
**Impact:** Perfect UX, but complex

---

## Testing Checklist

After implementing fixes, test these queries:

**Giants (NFL vs MLB):**
- [ ] "What was the Giants score?" → Seasonal default (NFL Sept-Feb, MLB Mar-Aug)
- [ ] "Giants football score?" → New York Giants (NFL)
- [ ] "Giants baseball score?" → San Francisco Giants (MLB)
- [ ] "NY Giants score?" → New York Giants (NFL)
- [ ] "SF Giants score?" → San Francisco Giants (MLB)

**Cardinals (NFL vs MLB):**
- [ ] "Cardinals score?" → Seasonal default
- [ ] "Cardinals football?" → Arizona Cardinals (NFL)
- [ ] "Cardinals baseball?" → St. Louis Cardinals (MLB)

**Panthers (NFL vs NHL):**
- [ ] "Panthers score?" → Seasonal default
- [ ] "Panthers hockey?" → Florida Panthers (NHL)
- [ ] "Panthers NFL?" → Carolina Panthers (NFL)

**Spurs (NBA vs EPL):**
- [ ] "Spurs score?" → Seasonal default
- [ ] "Spurs basketball?" → San Antonio Spurs (NBA)
- [ ] "Tottenham score?" → Tottenham (EPL)

---

## Code Locations

**Files to Modify:**
1. `/Users/jaystuart/dev/project-athena/src/jetson/sports_client.py`
   - Lines 26-289: `team_aliases` dictionary
   - Lines 481-501: `extract_team_name()` method
   - New methods: `_detect_sport_context()`, `_get_seasonal_default()`

2. `/Users/jaystuart/dev/project-athena/src/jetson/intent_classifier.py`
   - Lines 84-107: Sports intent classification
   - May need updates to pass sport context

**Files on Jetson (Deployed):**
1. `/mnt/nvme/athena-lite/sports_client.py`
2. `/mnt/nvme/athena-lite/intent_classifier.py`

**Deployment:**
- Copy fixed files to Jetson
- Restart ollama-proxy service: `sudo systemctl restart ollama-proxy`

---

## Priority Justification

**Why This is HIGH Priority:**

1. **Breaks Core Functionality:** Sports scores are a primary use case
2. **User Frustration:** Wrong answers erode trust in the system
3. **Simple Fix:** Option 1 can be fixed in 30 minutes
4. **Affects Popular Teams:** Giants, Cardinals are major US teams

**Impact on User Trust:**
- User asks reasonable question → Gets wrong answer → Loses confidence
- "It doesn't work" perception spreads beyond this single bug
- Wrong sport during big games (playoffs, World Series) = terrible UX

---

## Next Steps

1. **Immediate:** Implement Phase 1 (remove duplicates, add specific aliases)
2. **This Week:** Implement Phase 2 (sport context detection)
3. **Future:** Consider Phase 3 (user confirmation) for v2.0

---

## Implementation Completed

**Date:** November 7, 2025
**Status:** ✅ IMPLEMENTED - Ready for testing

### Changes Made

#### 1. sports_client.py - Disambiguation Logic Added

**New Methods:**
- `extract_team_name()` - Now detects ambiguous teams and sport context
  - Returns "AMBIGUOUS:{team}" if team is ambiguous and no context detected
  - Returns specific team alias if sport context provides disambiguation
- `_detect_sport_context()` - Keyword matching for sports (football, baseball, hockey, basketball, soccer)
- `_resolve_with_context()` - Maps ambiguous team + sport → specific team alias
- `get_clarification_message()` - Generates "Did you mean..." questions
- `resolve_from_clarification()` - Handles user's clarification response (for future enhancement)

**Team Aliases Updated:**
All 4 ambiguous teams now have specific aliases and context-aware resolution:

**NFL:**
- 'ny giants': 'New York Giants'
- 'new york giants': 'New York Giants'
- 'giants': 'New York Giants'  # Checked with context
- 'az cardinals': 'Arizona Cardinals'
- 'arizona cardinals': 'Arizona Cardinals'
- 'cardinals': 'Arizona Cardinals'  # Checked with context
- 'carolina panthers': 'Carolina Panthers'
- 'panthers': 'Carolina Panthers'  # Checked with context

**MLB:**
- 'sf giants': 'San Francisco Giants'
- 'san francisco giants': 'San Francisco Giants'
- 'giants': 'San Francisco Giants'  # Checked with context
- 'stl cardinals': 'St Louis Cardinals'
- 'st louis cardinals': 'St Louis Cardinals'
- 'cardinals': 'St Louis Cardinals'  # Checked with context

**NHL:**
- 'florida panthers': 'Florida Panthers'
- 'panthers': 'Florida Panthers'  # Checked with context

**NBA:**
- 'sa spurs': 'San Antonio Spurs'
- 'san antonio spurs': 'San Antonio Spurs'
- 'spurs': 'San Antonio Spurs'  # Checked with context

**Soccer (EPL):**
- 'tottenham': 'Tottenham'
- 'tottenham spurs': 'Tottenham'
- 'spurs': 'Tottenham'  # Checked with context

#### 2. intent_classifier.py - Clarification Handling

**Updated execute_intent():**
- Added check for `team_name.startswith('AMBIGUOUS:')`
- Extracts ambiguous team name
- Returns clarification question via `sports_client.get_clarification_message()`

### User Experience Flow

**Scenario 1: Ambiguous Query**
```
User: "What was the Giants score?"
System: "Did you mean the New York Giants in football or the San Francisco Giants in baseball?"
User: "Giants football score" [rephrases with context]
System: [Returns NY Giants score]
```

**Scenario 2: Query with Sport Context**
```
User: "What was the Giants football score?"
System: [Detects "football" keyword → resolves to NY Giants → returns score]
```

**Scenario 3: Query with Specific Alias**
```
User: "What was the NY Giants score?"
System: [Matches specific alias → returns NY Giants score]
```

### Deployment Required

**Files Modified:**
1. `/Users/jaystuart/dev/project-athena/src/jetson/sports_client.py`
2. `/Users/jaystuart/dev/project-athena/src/jetson/intent_classifier.py`

**Deployment Steps:**
1. Copy updated files to Jetson: `/mnt/nvme/athena-lite/`
2. Restart ollama-proxy service: `sudo systemctl restart ollama-proxy`
3. Test with voice commands

**Testing Checklist:**
- [ ] "Giants score" → Asks clarification
- [ ] "Giants football score" → NY Giants score (NFL)
- [ ] "Giants baseball score" → SF Giants score (MLB)
- [ ] "NY Giants score" → NY Giants score (NFL)
- [ ] "SF Giants score" → SF Giants score (MLB)
- [ ] "Cardinals score" → Asks clarification
- [ ] "Cardinals football" → Arizona Cardinals (NFL)
- [ ] "Cardinals baseball" → St Louis Cardinals (MLB)
- [ ] "Panthers score" → Asks clarification
- [ ] "Spurs score" → Asks clarification

### Future Enhancements

**Stateful Clarification (Phase 2):**
- Add conversation state management
- Handle single-word clarification responses ("football", "baseball")
- Maintain context across multiple turns
- Track pending clarifications

For now, the system requires users to rephrase with more context, which is a reasonable UX without complex state management.

---

**Bug Discovered:** November 7, 2025
**Reporter:** User (actual incorrect response observed)
**Status:** ✅ FIXED - Ready for deployment
**Implementation Time:** 2 hours (Phase 2 with sport context detection)
