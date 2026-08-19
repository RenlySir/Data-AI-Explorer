# Aegis AI Web MVP

## Run locally

```bash
cd apps/web
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`). The UI uses `VITE_API_BASE_URL`; it defaults to `http://localhost:18082/api/v1` for the repository's local backend workflow. Set `VITE_API_BASE_URL=http://localhost:8080/api/v1` when using the default Compose port.

## End-to-end tests

Install the Chromium runtime once, then run the desktop and mobile journeys:

```bash
npx playwright install chromium
npm run test:e2e
```

When system `python3` does not contain the backend dependencies, set
`PYTHON_BIN=/path/to/python-with-requirements` before `npm run test:e2e`.

Playwright starts isolated frontend and backend processes on ports `15173` and `18182`. Failed runs retain an HTML report, trace, screenshot, and video under ignored test-output directories.
