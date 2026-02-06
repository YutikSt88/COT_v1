# COT Client (Stage 1)

## Run

```powershell
# Terminal 1: API
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd client
npm install
npm run dev
```

Open: `http://localhost:5173`

## Stage 1 includes
- React + TypeScript + Vite scaffold
- Tailwind dark terminal base theme
- App shell (TopBar + SideNav)
- 3 placeholder pages:
  - Dashboard
  - Market Detail
  - Signals

## Next stage
- Integrate market detail and dashboard with API
- Replace placeholder charts with ECharts
