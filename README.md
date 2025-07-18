# Project Name

## Description
This project consists of a frontend built with modern web tools and a backend powered by FastAPI.

## Folder Structure
- **frontend/**: Contains the web application.
- **backend/**: Contains the FastAPI application.

## Setup Instructions

### Frontend
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

### Backend
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

## Notes
- Ensure you configure the `.env` file with the required environment variables.
- Logs and cache files are excluded from the repository.

## License
Specify your license here.
