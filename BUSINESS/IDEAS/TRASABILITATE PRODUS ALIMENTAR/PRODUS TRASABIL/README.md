# Trasabilitate MVP — 7-Day Sprint

## Project Structure

```
.
├── backend/               # Flask API
│   ├── app.py            # Main application
│   ├── init_db.py        # Database initialization
│   └── __init__.py
├── frontend/             # React dashboard
│   ├── src/
│   │   ├── App.js        # Main React component
│   │   ├── App.css       # Styles
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   └── package.json
├── cli/                  # Command-line tools
│   └── trasabilitate.py  # CLI interface
├── docker/               # Docker configuration
│   ├── Dockerfile.backend    # ARM-compatible (Raspberry Pi)
│   └── Dockerfile.frontend   # ARM-compatible
├── scripts/              # Utility scripts
│   ├── seed_demo.py      # Demo data
│   └── deploy.sh         # Deployment script
├── tests/                # Tests
│   └── test_api.py       # API tests
├── .env.example          # Environment template
├── docker-compose.yml    # Docker orchestration
├── requirements.txt      # Python dependencies
├── .gitignore
└── README.md
```

## Quick Start

### Local Development (Linux/Mac)

```bash
# 1. Install dependencies
pip install -r requirements.txt
npm install --prefix frontend

# 2. Start PostgreSQL
docker run -d \
  --name trasabilitate_db \
  -e POSTGRES_DB=trasabilitate_produce \
  -e POSTGRES_USER=tudor \
  -e POSTGRES_PASSWORD=tudor \
  -p 5432:5432 \
  postgres:13

# 3. Initialize database
python backend/init_db.py

# 4. Seed demo data
python scripts/seed_demo.py

# 5. Start backend (Terminal 1)
python backend/app.py

# 6. Start frontend (Terminal 2)
cd frontend && npm start

# 7. CLI tools
python cli/trasabilitate.py --help
```

### Docker (Linux/Mac/RPi)

```bash
# Build and start
docker-compose up --build

# Initialize database
docker-compose exec backend python backend/init_db.py

# Seed demo data
docker-compose exec backend python scripts/seed_demo.py

# Access
Frontend: http://localhost:3000
API: http://localhost:5000/health
```

### Raspberry Pi (ARM)

```bash
# Dockerfiles are ARM-compatible
# Just run docker-compose as normal
docker-compose up --build

# On first run:
docker-compose exec backend python backend/init_db.py
docker-compose exec backend python scripts/seed_demo.py
```

## API Endpoints

### Producer Management
- `POST /api/producer/register` — Register new producer

### Harvest Management
- `POST /api/harvest/create` — Create new harvest
- `GET /api/harvest/<harvest_id>` — Get harvest details
- `GET /api/harvest/<harvest_id>/trace` — Get full traceability (1-step back + forward)

### Sales Tracking
- `POST /api/harvest/<harvest_id>/sell` — Record sale/delivery

### QR Codes
- `GET /api/qr/<harvest_id>` — Get QR code as PNG

### Utility
- `GET /health` — Health check

## CLI Commands

```bash
# Register producer
python cli/trasabilitate.py register \
  --name "Ion Popescu" \
  --type vegetable_farmer \
  --location "Manastiresti, Vrancea" \
  --contact "ion@example.com"

# Create harvest
python cli/trasabilitate.py create \
  --producer 1 \
  --product "Tomato" \
  --qty 500

# Record sale
python cli/trasabilitate.py sell \
  --id 260308-TOMATO-500KG \
  --buyer-type hypermarket \
  --buyer "Kaufland Baneasa" \
  --qty 250 \
  --price 1.50 \
  --location "Kaufland warehouse, Sector 1"

# Trace harvest
python cli/trasabilitate.py trace --id 260308-TOMATO-500KG
```

## Technology Stack

- **Backend**: Flask 2.3 + PostgreSQL 13
- **Frontend**: React 18 + Axios
- **CLI**: Python argparse
- **DevOps**: Docker (ARM-compatible) + Docker Compose
- **Database**: PostgreSQL with 4 tables (producers, harvests, sales, audit_log)

## Performance (Raspberry Pi)

- Backend: ~50MB RAM
- Frontend: Static React build (~2MB)
- Database: PostgreSQL with indexes (lazy loading)
- Total: ~300-500MB RAM when running

## Compliance

- **EU 178/2002**: 1-step-back/forward traceability
- **QR codes**: Public-facing proof of origin
- **Audit log**: Immutable transaction history

## Development Roadmap

- **Day 1-2**: ✓ Database schema + Flask setup
- **Day 2-3**: ✓ REST API endpoints
- **Day 3-4**: ✓ QR codes + React dashboard
- **Day 4-5**: ✓ CLI tools
- **Day 5-6**: ✓ Testing + Docker
- **Day 7**: → Validation calls

## Testing

```bash
# Run tests
pytest tests/ -v

# API test with curl
curl http://localhost:5000/health
curl -X POST http://localhost:5000/api/harvest/create \
  -H "Content-Type: application/json" \
  -d '{"producer_id": 1, "product_name": "Tomato", "quantity_kg": 500, "harvest_date": "2026-03-08"}'
```

## Next Steps (Post-MVP)

1. Validate with Kaufland (Week 1, Day 7)
2. Sign first 5 producers (Week 2-3)
3. Deploy to production VPS (Week 3)
4. Build mobile app (Week 4-6)
5. Cooperative billing integration (Week 7-8)

## Support

- Issues: GitHub issues
- Docs: See README.md
- CLI Help: `python cli/trasabilitate.py --help`
