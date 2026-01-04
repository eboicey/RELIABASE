# RELIABASE Frontend

React + Vite + TypeScript single-page UI for the RELIABASE FastAPI backend.

## Quick start
1. Install deps (Node 18+):
   ```bash
   npm install
   npm run dev
   ```
   The app starts at http://localhost:5173 by default.

2. Point to backend (defaults to http://localhost:8000):
   ```bash
   echo "VITE_API_URL=http://localhost:8000" > .env.local
   ```

## Features
- Navigation: dashboard, assets, exposures, events, event failure details, failure modes, parts/installs.
- Data fetching via TanStack Query; Axios client in `src/api`.
- Forms with React Hook Form + Zod; Tailwind-based layout.

## Notes
- Backend expects the database initialized; seed via `python -m reliabase.seed_demo`.
- Report generation remains CLI-driven (`python -m reliabase.make_report`).
