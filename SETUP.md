# StillAliveGhost v2 — Setup & Deployment Guide

## Prerequisites

- Node.js 18+ (npm)
- Python 3.11+
- Expo CLI: `npm install -g expo-cli eas-cli`
- Groq API Key (https://console.groq.com/)

---

## Local Development

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your keys
GROQ_API_KEY=your_key_here
API_URL=http://localhost:8000
```

### 2. Start Backend

```bash
# Option A: Using startup script
./start_backend.sh

# Option B: Manual start
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

Server runs on `http://localhost:8000`

### 3. Frontend Setup

```bash
# Install Node dependencies
npm install

# Start Expo dev client
npm start

# On Android emulator
npm run android

# Via tunnel (for phone testing)
npm run start:tunnel
```

---

## Mobile APK Build (GitHub Actions)

### Prerequisites

1. **Expo Account & Project**
   ```bash
   expo login
   expo init (or use existing project)
   ```

2. **GitHub Secrets Setup**
   - Go to repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `GROQ_API_KEY` — Your Groq API key
     - `EXPO_TOKEN` — Expo authentication token
     - `EAS_PROJECT_ID` — EAS project ID (found in eas.json or expo.dev dashboard)

3. **Create eas.json** (if not present)
   ```json
   {
     "cli": {
       "version": ">= 5.0.0"
     },
     "build": {
       "production": {
         "android": {
           "buildType": "apk"
         }
       }
     }
   }
   ```

### Automatic Build on Push

```bash
# Push to main branch
git push origin main

# Build workflow auto-triggers
# Monitor in GitHub Actions tab
# Download APK from artifacts
```

### Manual Build (Local)

```bash
# Requires EAS credentials
eas login

# Build APK
eas build --platform android --local

# Build AAB (for Play Store)
eas build --platform android --type app-bundle
```

---

## API Configuration

### For Android Testing

**Option 1: Emulator (localhost works)**
```javascript
const API_BASE = 'http://10.0.2.2:8000'; // Android emulator localhost redirect
```

**Option 2: Phone on LAN**
```bash
# Get your PC/Mac IP
ifconfig | grep "inet "  # macOS/Linux
ipconfig                  # Windows

# Use that IP in your app config or environment
const API_BASE = 'http://192.168.1.100:8000';
```

**Option 3: Ngrok Tunnel (production)**
```bash
# Install ngrok
brew install ngrok  # or download

# Start tunnel
ngrok http 8000

# Use provided HTTPS URL
const API_BASE = 'https://xxxx-xx-xx-xx-xx.ngrok.io';
```

---

## Deployment Options

### Heroku / Railway

1. **Connect GitHub repo**
2. **Set environment variables**
   - `GROQ_API_KEY`
   - `API_URL` (auto-filled as app URL)

3. **Deploy**
   ```bash
   git push heroku main
   # or use Heroku dashboard
   ```

### Android Play Store

1. **Generate signed APK/AAB**
   ```bash
   eas build --platform android --type app-bundle --auto-submit
   ```

2. **Create Play Store listing**
3. **Upload AAB to Google Play Console**

---

## Troubleshooting

### WebSocket Connection Failed
- Check if backend is running
- Verify firewall allows port 8000
- On Android: use correct IP (not localhost)

### "GROQ_API_KEY not set"
- Verify .env file exists
- Check key is not empty
- Restart server after changing .env

### APK Build Fails
- Update all dependencies: `npm install`
- Clear cache: `npm start -- --clear`
- Check Node/npm versions: `node -v`, `npm -v`

### Python Import Errors
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
- Reinstall deps: `pip install -r requirements.txt --force-reinstall`

---

## Project Structure

```
.
├── App.js                 # React Native main app
├── app.json              # Expo configuration
├── package.json          # Node dependencies
├── requirements.txt      # Python dependencies
├── src/
│   ├── server.py        # FastAPI backend
│   └── services/        # TikTok, Groq, distortion services
├── .github/workflows/   # GitHub Actions CI/CD
└── Procfile            # Cloud deployment config
```

---

## Running in Termux (Android)

```bash
# Install Node/Python
pkg install nodejs python

# Clone repo
git clone <repo>
cd StillAliveGhost-v2

# Setup
npm install
pip install -r requirements.txt

# Start backend
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000

# In separate Termux session
npm start
```

---

## Security Notes

- Never commit .env with real keys
- Use HTTPS in production
- Rotate API keys regularly
- Keep dependencies updated

---

## Support

Check `README.md` for feature overview or submit issues to GitHub.
