You can see how it behaves from here: https://drive.google.com/file/d/1iS7AG9VhlwajNpfckK5HbB1pR8K_Ng34/view?usp=sharing

---

## Running the Project

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL
- [Expo Go](https://expo.dev/go) app on your phone (or an iOS/Android simulator)

---

### Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (required for session management)
docker compose up -d

# Run the server
ENV=development uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

---

### Mobile

```bash
cd mobile

# Install dependencies
npm install

# Start Expo
npx expo start
```

Scan the QR code with the **Expo Go** app on your phone.

> To run on a simulator, you need to build a dev build first:
> ```bash
> npx expo run:ios    # iOS simulator
> npx expo run:android  # Android emulator
> ```

---

## Environment Variables

Create `backend/.env.development` with the following:

```env
# Environment
ENV=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/calendar_ai

# Security
SECRET_KEY=your-secret-key-here

# AI / LLM
OPENAI_API_KEY=sk-...

# Internet search (for leisure/event discovery)
TAVILY_API_KEY=tvly-...

# Email notifications
RESEND_API_KEY=re_...
NOTIFICATION_FROM_EMAIL=onboarding@resend.dev
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret (any long random string) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for all LLM agents |
| `TAVILY_API_KEY` | No | Enables leisure/event discovery search |
| `RESEND_API_KEY` | No | Enables email notifications after calendar actions |
| `NOTIFICATION_FROM_EMAIL` | No | Sender address (defaults to `onboarding@resend.dev`) |

> **Note:** `TAVILY_API_KEY` and `RESEND_API_KEY` are optional. The app works without them — leisure search and email notifications will simply be disabled.
