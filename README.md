# AI Trading Assistant

An AI-powered market analysis and educational insights platform for NSE markets (NIFTY, BANKNIFTY, FINNIFTY, F&O).

> **Disclaimer**: This application provides AI-driven market analysis and educational insights only. No auto-trading or guaranteed advice is provided. Trading involves risk - always do your own research.

## 🎯 Features

### Market Data
- **Live Market Dashboard** - Real-time tracking of NIFTY, BANKNIFTY, FINNIFTY, SENSEX, INDIA VIX
- **Option Chain Analytics** - PCR, Max Pain, OI changes, Call/Put analysis
- **Technical Indicators** - EMA, VWAP, RSI, MACD, Supertrend, Bollinger Bands, ATR, ADX

### AI Features
- **AI Market Engine** - Educational insights with confidence scores
- **Chart Analysis** - Pattern detection, entry/SL/target levels
- **AI Chat Assistant** - Market-related Q&A (educational only)
- **AI Trade Review** - Analyze completed trades for improvements

### Trading Tools
- **Trade Journal** - Log trades, track performance metrics
- **Market Scanner** - Breakout, EMA cross, volume, OI buildup detection
- **Strategy Builder** - ORB, VWAP, EMA Crossover, Momentum strategies
- **Backtesting** - Historical strategy testing with metrics

### Risk Management
- Position sizing calculator
- Daily/weekly loss limits
- Risk percentage calculator
- Capital allocation

### Alerts & Notifications
- **Telegram Alerts** - EMA/VWAP crosses, breakouts, OI spikes
- Custom price alerts
- Real-time notifications

## 🛠 Tech Stack

### Frontend
- **Framework**: Next.js 16 with React 19
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand + TanStack Query
- **Charts**: Recharts, Lightweight Charts (TradingView)
- **Forms**: React Hook Form + Zod

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: Firestore
- **Cache**: Redis
- **Task Queue**: Celery
- **AI**: OpenAI GPT-4

### Infrastructure
- **Frontend**: Vercel
- **Backend**: Railway/Render
- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry, Prometheus

## 📁 Project Structure

```
ai-trading-assistant/
├── frontend/                    # Next.js application
│   ├── app/                     # App router pages
│   ├── components/              # React components
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── dashboard/           # Dashboard-specific components
│   │   └── layout/              # Layout components
│   ├── lib/                     # Utilities and helpers
│   ├── hooks/                   # Custom React hooks
│   └── types/                   # TypeScript type definitions
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── api/                 # API routes
│   │   │   ├── market.py        # Market data endpoints
│   │   │   ├── options.py       # Option chain endpoints
│   │   │   ├── indicators.py    # Technical indicators
│   │   │   ├── scanner.py       # Market scanner
│   │   │   ├── journal.py       # Trade journal
│   │   │   ├── strategies.py     # Strategy builder
│   │   │   ├── ai.py            # AI endpoints
│   │   │   ├── risk.py          # Risk management
│   │   │   ├── alerts.py        # Alerts
│   │   │   └── auth.py          # Authentication
│   │   ├── core/                # Core configuration
│   │   ├── schemas/             # Pydantic models
│   │   └── services/            # Business logic
│   └── requirements.txt         # Python dependencies
│
├── .github/
│   └── workflows/               # GitHub Actions
│       ├── ci.yml              # Continuous integration
│       ├── scheduler.yml       # Scheduled tasks
│       └── deploy.yml          # Deployment
│
└── docs/                        # Documentation
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Redis (for caching)
- Firebase account (for Firestore)

### Installation

#### Frontend

```bash
cd frontend
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your values

# Run development server
npm run dev
```

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Firebase Setup

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Firestore Database
3. Create a service account and download the JSON key
4. Set `GOOGLE_APPLICATION_CREDENTIALS` in your backend `.env`

### Running with Docker

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## 📝 API Documentation

Once the backend is running, access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/market/indices` | Get all market indices |
| `GET /api/v1/market/quote/{symbol}` | Get quote for symbol |
| `GET /api/v1/options/chain/{symbol}` | Get option chain |
| `GET /api/v1/indicators/{symbol}` | Get technical indicators |
| `GET /api/v1/scanner/` | Scan market opportunities |
| `GET /api/v1/journal/` | Get trade journal |
| `POST /api/v1/ai/insights/{symbol}` | Get AI market insight |
| `POST /api/v1/risk/position-size` | Calculate position size |

## ⚙️ Environment Variables

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-secret
NEXT_PUBLIC_FIREBASE_API_KEY=...
```

### Backend (.env)

```env
ENVIRONMENT=development
OPENAI_API_KEY=sk-...
FIRESTORE_PROJECT_ID=your-project
JWT_SECRET=your-jwt-secret
```

See `.env.example` files for all available options.

## 🧪 Testing

### Frontend

```bash
cd frontend
npm run test        # Run tests
npm run test:cov    # With coverage
```

### Backend

```bash
cd backend
pytest               # Run tests
pytest --cov=app     # With coverage
```

## 🚢 Deployment

### Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

### Backend (Railway)

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy

### Backend (Render)

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)

## 🔒 Security

- JWT-based authentication
- Role-based access control
- Input validation with Pydantic/Zod
- Rate limiting
- CORS configuration

## 📈 Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Mobile app (React Native)
- [ ] Additional technical indicators
- [ ] Portfolio management
- [ ] Multi-exchange support
- [ ] Paper trading mode

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Disclaimer

This software is for educational purposes only. It provides AI-generated market analysis which should not be considered as financial advice. Trading in financial markets involves substantial risk of loss. Always conduct your own research and consult with a licensed financial advisor before making investment decisions.

---

Built with ❤️ for traders