# API Key Acquisition Guide - Project Athena

**Last Updated:** 2025-11-11

---

## Priority Order

**Phase 1 (Required):**
1. ✅ **OpenWeatherMap** - Weather queries (FREE, instant)
2. ✅ **FlightAware** - Airport/flight data (FREE tier, may take 1-2 days)
3. ✅ **TheSportsDB** - Sports data (FREE, instant)

**Phase 2 (Future):**
4. NewsAPI - News queries
5. Spoonacular - Recipe queries
6. TMDB - Streaming availability
7. Yelp/Google Places - Dining recommendations

---

## Phase 1: Get These Keys This Week

### 1. OpenWeatherMap (Weather) - GET TODAY ⚡

**Free Tier:** 1,000 calls/day (more than enough)

**Steps:**
1. Go to: https://openweathermap.org/api
2. Click "Sign Up" (top right)
3. Fill out form:
   - Email
   - Username
   - Password
4. Verify email (check inbox)
5. Log in: https://home.openweathermap.org/
6. Go to "API keys" tab
7. Copy the default API key (or create new one)
8. **Test immediately:**
```bash
curl "https://api.openweathermap.org/data/2.5/weather?q=Baltimore&appid=YOUR_KEY&units=imperial"
```

**Expected Response:**
```json
{
  "name": "Baltimore",
  "main": {
    "temp": 72.5,
    "feels_like": 71.2
  },
  "weather": [{"description": "clear sky"}]
}
```

**Add to .env:**
```bash
OPENWEATHER_API_KEY=your_actual_key_here
```

---

### 2. FlightAware (Airports/Flights) - GET THIS WEEK 📅

**Free Tier:** 100 queries/month

**Steps:**
1. Go to: https://www.flightaware.com/commercial/flightxml/
2. Click "Sign Up" or "Get Started"
3. Choose **"FlightXML 3"** (not FlightXML 2)
4. Select **"Free Tier"** (no credit card required)
5. Fill out registration:
   - Name
   - Email
   - Company: "Personal Project" or "Athena Voice Assistant"
   - Use Case: "Personal smart home voice assistant"
6. Verify email
7. Log in to developer portal
8. Navigate to "API Keys" or "Credentials"
9. Copy your API key

**Test:**
```bash
curl "https://aeroapi.flightaware.com/aeroapi/airports/KBWI" \
  -H "x-apikey: YOUR_KEY"
```

**Expected Response:**
```json
{
  "airport_code": "KBWI",
  "name": "Baltimore Washington Intl",
  "city": "Baltimore"
}
```

**Add to .env:**
```bash
FLIGHTAWARE_API_KEY=your_actual_key_here
```

**Note:** API key may take 1-2 hours to activate after registration.

---

### 3. TheSportsDB (Sports) - GET THIS WEEK 📅

**Free Tier:** 100 calls/day (Patreon supporters get more)

**Steps:**
1. Go to: https://www.thesportsdb.com/api.php
2. Scroll to "API Key" section
3. Click "Support us on Patreon for £2/month"
   - OR use free tier with limited calls
4. **Free Option:**
   - API Key: `1` (public test key, rate-limited)
   - Works for testing, but should upgrade for production
5. **Patreon Option ($2/month):**
   - Support on Patreon
   - Get personal API key (higher limits)
   - More reliable for production

**Test (using public key):**
```bash
curl "https://www.thesportsdb.com/api/v1/json/1/searchteams.php?t=Baltimore_Ravens"
```

**Expected Response:**
```json
{
  "teams": [{
    "strTeam": "Baltimore Ravens",
    "strLeague": "NFL",
    "strStadium": "M&T Bank Stadium"
  }]
}
```

**Add to .env:**
```bash
# For testing:
THESPORTSDB_API_KEY=1

# For production (after Patreon):
THESPORTSDB_API_KEY=your_patreon_key
```

---

## Phase 2: Get These Later (Not Needed for Phase 1)

### 4. NewsAPI (News Queries)

**Free Tier:** 100 requests/day

**Steps:**
1. Go to: https://newsapi.org/
2. Click "Get API Key"
3. Sign up (email + password)
4. Copy API key from dashboard

**Add to .env:**
```bash
NEWSAPI_KEY=your_key_here
```

---

### 5. Spoonacular (Recipes)

**Free Tier:** 150 requests/day

**Steps:**
1. Go to: https://spoonacular.com/food-api
2. Click "Get Access"
3. Sign up for free tier
4. Copy API key

**Add to .env:**
```bash
SPOONACULAR_API_KEY=your_key_here
```

---

### 6. TMDB (Streaming/Movies)

**Free:** Unlimited (with rate limits)

**Steps:**
1. Go to: https://www.themoviedb.org/signup
2. Sign up for account
3. Go to Settings → API
4. Request API key (select "Developer")
5. Fill out application (describe home assistant use)
6. Get API key

**Add to .env:**
```bash
TMDB_API_KEY=your_key_here
```

---

### 7. Yelp (Dining)

**Free Tier:** 5,000 calls/day

**Steps:**
1. Go to: https://www.yelp.com/developers
2. Click "Get Started"
3. Create app:
   - App Name: "Athena Voice Assistant"
   - Description: "Personal smart home assistant"
4. Get API key

**Add to .env:**
```bash
YELP_API_KEY=your_key_here
```

---

### 8. Google Places (Dining Alternative)

**Free Tier:** $200 credit/month (covers ~10,000 requests)

**Steps:**
1. Go to: https://console.cloud.google.com/
2. Create new project: "Athena"
3. Enable "Places API"
4. Create credentials (API key)
5. Restrict key to Places API only

**Add to .env:**
```bash
GOOGLE_PLACES_API_KEY=your_key_here
```

---

## Testing All Keys

Once you have keys, test them all:

```bash
# Load environment
source config/env/.env

# Test OpenWeatherMap
echo "Testing OpenWeatherMap..."
curl -s "https://api.openweathermap.org/data/2.5/weather?q=Baltimore&appid=${OPENWEATHER_API_KEY}&units=imperial" | jq '.main.temp'

# Test FlightAware
echo "Testing FlightAware..."
curl -s "https://aeroapi.flightaware.com/aeroapi/airports/KBWI" \
  -H "x-apikey: ${FLIGHTAWARE_API_KEY}" | jq '.name'

# Test TheSportsDB
echo "Testing TheSportsDB..."
curl -s "https://www.thesportsdb.com/api/v1/json/${THESPORTSDB_API_KEY}/searchteams.php?t=Baltimore_Ravens" | jq '.teams[0].strTeam'

echo "✅ All API keys working!"
```

---

## Security Notes

**DO NOT commit API keys to git!**

The `.env` file should be in `.gitignore`:

```bash
# Verify .env is ignored
git status
# Should NOT show config/env/.env

# If it shows up, add to .gitignore:
echo "config/env/.env" >> .gitignore
git add .gitignore
git commit -m "Ignore environment files"
```

**Key Rotation:**
- Rotate keys every 6-12 months
- If key is leaked, regenerate immediately
- Use separate keys for dev/prod if possible

---

## Rate Limits & Caching

**Our caching strategy handles rate limits:**

| Service | Free Limit | Cache TTL | Calls/Day Estimate |
|---------|-----------|-----------|-------------------|
| OpenWeatherMap | 1,000/day | 48 hours | ~50 (20 unique queries) |
| FlightAware | 100/month | 1 hour | ~30/day (10 airports × 3 checks/day) |
| TheSportsDB | 100/day | 15 min live, 24h past | ~30 (10 teams checked) |

**With caching, you'll stay well within free tiers!**

---

## Cost Estimate (If You Upgrade)

**Month 1 (Phase 1):**
- OpenWeatherMap: FREE
- FlightAware: FREE (may upgrade to $20/month for more calls)
- TheSportsDB: $2/month (Patreon)
- **Total: $0-22/month**

**Month 2+ (Phase 2):**
- Add NewsAPI: FREE
- Add Spoonacular: FREE
- Add TMDB: FREE
- Add Yelp: FREE
- Add Twilio (SMS): ~$1/month (if used)
- Add SendGrid (Email): FREE
- **Total: $1-23/month**

**Very affordable for a production voice assistant!**

---

## Quick Reference

**Phase 1 Minimum (Start Today):**
```bash
OPENWEATHER_API_KEY=get_this_today
FLIGHTAWARE_API_KEY=get_this_week
THESPORTSDB_API_KEY=1  # free public key, upgrade to $2/month later
```

**Phase 2 (Later):**
```bash
NEWSAPI_KEY=defer_to_phase2
SPOONACULAR_API_KEY=defer_to_phase2
TMDB_API_KEY=defer_to_phase2
YELP_API_KEY=defer_to_phase2
```

---

## Help & Support

**If you have issues:**
- Check API documentation for your specific service
- Look for "quota exceeded" or "invalid key" errors
- Some keys take 1-2 hours to activate
- Test keys immediately after getting them

**Common Issues:**
- **"Invalid API key"** - Check for typos, extra spaces
- **"Quota exceeded"** - Upgrade tier or wait 24 hours
- **"Not found"** - Check endpoint URL is correct
- **"Unauthorized"** - Key not activated yet, wait 1-2 hours

---

**You only need 1 key (OpenWeatherMap) to start testing today! Get the others this week. 🚀**
