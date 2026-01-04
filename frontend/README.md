# RELIABASE Frontend

React + Vite + TypeScript single-page application for the RELIABASE reliability analytics platform.

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+**
- Backend API running at http://localhost:8000 (see [main README](../README.md))

### Installation & Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at **http://localhost:5173**

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env.local` file to customize settings:

```bash
# Backend API URL (default: http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── api/              # API client, endpoints, and TypeScript types
│   │   ├── client.ts     # Axios instance configuration
│   │   ├── endpoints.ts  # API function calls
│   │   └── types.ts      # TypeScript interfaces
│   ├── components/       # Reusable UI components
│   │   ├── charts/       # Chart.js visualizations
│   │   ├── Alert.tsx
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── ...
│   ├── layouts/          # Page layouts
│   │   └── Shell.tsx     # Main navigation shell
│   ├── pages/            # Route pages
│   │   ├── Dashboard.tsx # Overview & quick stats
│   │   ├── Analytics.tsx # MTBF/MTTR/Weibull charts
│   │   ├── Operations.tsx# Seeding, exports, health check
│   │   └── ...
│   ├── utils/            # Helper functions (CSV export, etc.)
│   ├── App.tsx           # Route definitions
│   ├── main.tsx          # Application entry point
│   └── index.css         # TailwindCSS styles
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 🎯 Features

### Pages

| Page | Description |
|------|-------------|
| **Dashboard** | KPI cards, recent events table, quick start guide |
| **Assets** | CRUD for tracked equipment |
| **Exposures** | Operating time/cycle logs |
| **Events** | Failures, maintenance, inspections |
| **Event Details** | Link failures to failure modes with root cause analysis |
| **Failure Modes** | Catalog of failure types |
| **Parts** | Spare parts inventory & installation tracking |
| **Analytics** | MTBF/MTTR metrics, failure mode Pareto charts |
| **Operations** | Seed demo data, API health check, CSV exports |

### Tech Stack

- **React 18** with TypeScript
- **TanStack Query** (React Query) for data fetching & caching
- **React Router** for client-side routing
- **React Hook Form + Zod** for form handling & validation
- **Axios** for HTTP requests
- **TailwindCSS** for styling
- **Chart.js** for visualizations
- **Vite** for fast development & builds

---

## 🛠️ Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint checks |

---

## 📝 Notes

- **Backend Required**: The frontend requires the FastAPI backend running. Start it with:
  ```bash
  uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload
  ```

- **Demo Data**: Seed the database via the Operations page or CLI:
  ```bash
  python -m reliabase.seed_demo
  ```

- **Reports**: PDF report generation is CLI-only:
  ```bash
  python -m reliabase.make_report --asset-id 1 --output-dir ./examples
  ```

---

## 📄 License

MIT — See [LICENSE](../LICENSE) for details.
