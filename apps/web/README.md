# Aegis AI Web MVP

## Run locally

```bash
cd apps/web
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`). The UI uses `VITE_API_BASE_URL`; it defaults to `http://localhost:18082/api/v1` for the repository's local backend workflow. Set `VITE_API_BASE_URL=http://localhost:8080/api/v1` when using the default Compose port.
