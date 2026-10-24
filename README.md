# UK Wind Forecast Analytics

A web-based dashboard for comparing day-ahead wind generation forecasts with actual generation data for January 2026. The application visualizes forecast performance and provides error metrics to help evaluate forecasting accuracy.

## Features

- Forecast vs. actual wind generation visualization
- Forecast generation and actual generation KPI cards
- Mean Absolute Error (MAE) and Root Mean Square Error (RMSE)
- Delivery-period details and forecast error analysis
- Interactive charts and time-period filters
- Responsive dashboard interface

## Tech Stack

**Frontend**
- React
- Vite
- JavaScript
- Tailwind CSS
- Recharts
- Fetch API

**Backend**
- Python
- FastAPI
- Pandas

## Live Demo

- **Frontend:** https://wind-forecast-analytics-zeta.vercel.app
- **Backend API:** https://wind-forecast-analytics-yq4i.onrender.com
- **API Documentation:** https://wind-forecast-analytics-yq4i.onrender.com/docs

## Local Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd wind-forecast-analytics
```

### 2. Run the backend

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend should be available at `http://localhost:8000`.

### 3. Run the frontend

Open another terminal:

```bash
cd Frontend
npm install
```

Create a `.env` file inside `Frontend`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

Vite will display the local frontend URL in the terminal.

## Accuracy Metrics

- **MAE:** Average absolute difference between forecast and actual generation.
- **RMSE:** Square root of the average squared difference between forecast and actual generation.

Lower values generally indicate smaller forecasting errors.

## Deployment

The frontend is deployed on Vercel, and the backend is deployed on Render. The frontend uses `VITE_API_BASE_URL` to connect to the backend.

## License

Created as a software engineering assignment.
