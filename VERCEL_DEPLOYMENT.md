# Vercel Deployment Guide

## Prerequisites
1. Install Vercel CLI: `npm i -g vercel`
2. Create a Vercel account at https://vercel.com

## Environment Variables
Set these in your Vercel dashboard under Project Settings > Environment Variables:

```
SECRET_KEY=your-secret-key-change-in-production
GOOGLE_CLIENT_ID=your-google-client-id (optional)
GOOGLE_CLIENT_SECRET=your-google-client-secret (optional)
GEMINI_API_KEY=your-gemini-api-key (optional)
GEMINI_MODEL=gemini-2.0-flash (optional)
```

## Deployment Steps

### Method 1: Using Vercel CLI
1. Run `vercel` in the project root
2. Follow the prompts to link your project
3. Run `vercel --prod` to deploy to production

### Method 2: Using Vercel Dashboard
1. Connect your GitHub repository to Vercel
2. Import the project
3. Set environment variables
4. Deploy

## Project Structure
```
├── api/
│   └── index.py          # Vercel entry point
├── backend/
│   └── app.py           # Flask application
├── frontend/
│   ├── templates/       # HTML templates
│   └── static/          # CSS, JS, images
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies
└── .vercelignore       # Files to ignore
```

## Notes
- The Flask app is configured to work with Vercel's serverless environment
- Static files are served from the `frontend/static` directory
- Database is SQLite (consider upgrading to PostgreSQL for production)
- All routes are handled by the Flask app through the API entry point
