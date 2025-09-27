# 🚀 Web-Inter-Prep Deployment Guide

## 📋 Overview
This guide covers deploying the Web-Inter-Prep application with Google OAuth and Gemini AI integration on Render.

## 🔧 Environment Variables Required

### **Required for Google OAuth:**
```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### **Required for Gemini AI:**
```
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
```

### **Required for Flask:**
```
SECRET_KEY=your_secret_key_here
FLASK_ENV=production
```

## 🛠️ Setup Instructions

### 1. **Google OAuth Setup**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Set authorized redirect URIs:
   - Development: `http://localhost:5000/login/google/callback`
   - Production: `https://your-app.onrender.com/login/google/callback`

### 2. **Gemini AI Setup**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the API key for `GEMINI_API_KEY`

### 3. **Render Deployment**
1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy using the provided `render.yaml`

## 📁 File Structure
```
web-inter-prep/
├── app.py                    # Main Flask application
├── render.yaml              # Render deployment config
├── requirements.txt         # Python dependencies
├── frontend/
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, images
└── backend/
    └── data/
        └── questions.json   # Sample questions
```

## 🔑 Key Features

### **Authentication:**
- ✅ Regular email/password login
- ✅ Google OAuth integration
- ✅ Session management
- ✅ User registration

### **AI Features:**
- ✅ Gemini AI-powered interview questions
- ✅ Real-time AI feedback
- ✅ Customizable interview parameters
- ✅ JSON response parsing

### **Database:**
- ✅ SQLite with persistent storage
- ✅ User management
- ✅ Interview tracking
- ✅ Statistics dashboard

## 🚀 Deployment Commands

### **Local Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
export GEMINI_API_KEY="your_gemini_key"
export SECRET_KEY="your_secret_key"

# Run application
python app.py
```

### **Render Deployment:**
```bash
# Push to GitHub
git add .
git commit -m "Deploy with Google OAuth and Gemini AI"
git push origin main

# Render will automatically deploy
```

## 🔍 Testing Checklist

### **Authentication:**
- [ ] Regular login works
- [ ] Registration works
- [ ] Google OAuth login works
- [ ] Session persistence works
- [ ] Logout works

### **AI Features:**
- [ ] Gemini API key configured
- [ ] AI interview questions generate
- [ ] AI feedback works
- [ ] JSON parsing works
- [ ] Fallback responses work

### **Database:**
- [ ] Database initializes
- [ ] User data persists
- [ ] Interview data tracks
- [ ] Statistics calculate

## 🐛 Troubleshooting

### **Common Issues:**

1. **Google OAuth not working:**
   - Check redirect URIs in Google Console
   - Verify environment variables
   - Check OAuth scope configuration

2. **Gemini AI not responding:**
   - Verify API key is correct
   - Check API quota limits
   - Test with fallback responses

3. **Database errors:**
   - Check database path configuration
   - Verify file permissions
   - Check SQLite initialization

## 📊 Monitoring

### **Render Dashboard:**
- Check deployment logs
- Monitor environment variables
- View application metrics

### **Application Logs:**
- Database initialization status
- API call responses
- Error messages and stack traces

## 🎯 Success Criteria

✅ **All systems operational:**
- Authentication: Working
- Database: Working  
- API: Working
- Google OAuth: Working
- Gemini AI: Working

## 📞 Support

If you encounter issues:
1. Check the deployment logs in Render
2. Verify all environment variables are set
3. Test locally first
4. Check API quotas and limits