# Timeweb Cloud Deployment

## 🚀 Deployed Applications

### Backend API
- **URL**: https://wemdio-parser-0daf.twc1.net
- **Health Check**: https://wemdio-parser-0daf.twc1.net/health
- **API Endpoint**: https://wemdio-parser-0daf.twc1.net/api
- **Type**: Backend (FastAPI + Python)
- **Framework**: Docker
- **Status**: ✅ DEPLOYED

### Frontend
- **URL**: https://wemdio-parser-828c.twc1.net  
- **Type**: Frontend (React)
- **Framework**: React
- **Status**: 🔄 DEPLOYING

## ⚙️ Configuration

### Backend Environment Variables
The backend is already configured with the necessary environment variables from your local `.env` file:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `API_ID`
- `API_HASH`

### Frontend Environment Variables
The frontend needs to know where the backend is located. You have two options:

#### Option 1: Set environment variable in Timeweb (Recommended)
1. Go to Timeweb Cloud dashboard
2. Select your frontend app "Parser Frontend"
3. Go to Settings → Environment Variables
4. Add: `REACT_APP_API_URL=https://wemdio-parser-0daf.twc1.net`
5. Restart the app

#### Option 2: Hardcode in config (Quick fix)
Update `frontend/src/config.js`:
```javascript
const API_BASE = 'https://wemdio-parser-0daf.twc1.net';
export default API_BASE + '/api';
```

## 📁 Repository Structure Issue

⚠️ **IMPORTANT**: The current deployment might fail because the frontend code is in the `frontend/` subdirectory, but Timeweb expects it at the repository root for React apps.

### Solutions:

#### Solution 1: Use Docker Framework (Recommended)
Delete the current frontend app and recreate it with `framework: docker`. This will use our custom `frontend/Dockerfile` which handles the subdirectory correctly.

#### Solution 2: Restructure Repository
Move frontend files to root (not recommended as it breaks local development).

#### Solution 3: Wait for Build Logs
Check if Timeweb can handle the subdirectory automatically. Monitor the build logs.

## 🔍 Checking Deployment Status

### Backend
```bash
curl https://wemdio-parser-0daf.twc1.net/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "version": "1.0.0"
}
```

### Frontend
```bash
curl https://wemdio-parser-828c.twc1.net
```

Should return HTML content.

## 🐛 Troubleshooting

### Frontend Build Failing

**Problem**: "No package.json found"

**Cause**: Timeweb is looking for `package.json` at repository root, but it's in `frontend/` subdirectory.

**Solution**:
1. Delete the current frontend app from Timeweb dashboard
2. Create a new app with `framework: docker` instead of `framework: react`
3. This will use the custom Dockerfile that handles the subdirectory structure

**Alternative**: Create a `package.json` at the repository root that delegates to the frontend:
```json
{
  "name": "parser-root",
  "scripts": {
    "build": "cd frontend && npm install && npm run build",
    "start": "cd frontend && npm start"
  }
}
```

### Frontend Can't Connect to Backend

**Problem**: CORS errors or connection refused

**Solution**:
1. Check backend CORS settings in `backend/main.py`
2. Verify `REACT_APP_API_URL` environment variable is set
3. Check frontend console for actual API URL being used

### Backend Session Issues

**Problem**: Telegram sessions not persisting

**Cause**: Docker container restarts lose session files

**Solution**:
1. Configure persistent volume in Timeweb for `/app/sessions` directory
2. Or use database-based session storage (requires code changes)

## 📊 Monitoring

### View Logs

#### Backend Logs
1. Go to Timeweb dashboard
2. Select backend app
3. Click "Logs" tab
4. Look for startup messages and any errors

#### Frontend Logs  
1. Go to Timeweb dashboard
2. Select frontend app
3. Click "Build Logs" to see build process
4. Click "Logs" to see nginx access logs

### Common Log Messages

**Backend Success**:
```
>>> BACKEND STARTED <<<
Supabase client initialized successfully
Starting scheduler...
Application startup complete.
```

**Frontend Success**:
```
Successfully built
Serving static files from /build
```

## 🔄 Redeploying

### Automatic Deployment
Currently set to manual deployment (`is_auto_deploy: false`).

To enable automatic deployment on git push:
1. Update app settings in Timeweb
2. Enable auto-deploy from `main` branch

### Manual Deployment
1. Push changes to GitHub
2. Go to Timeweb dashboard
3. Select the app
4. Click "Redeploy" button
5. Or create a new deployment via MCP tools

## 💰 Costs

- **Backend**: 1₽/month (preset 1629 - 1 CPU, 2GB RAM, 30GB disk)
- **Frontend**: 1₽/month (preset 1451 - 50MB disk)
- **Total**: 2₽/month (~$0.02 USD/month)

## 🔐 Security Notes

1. **API Keys**: Stored as environment variables in Timeweb (secure)
2. **Supabase**: Uses service role key (be careful with RLS policies)
3. **Telegram**: Sessions are stored in container (consider persistent storage)
4. **HTTPS**: All Timeweb apps use HTTPS by default ✅

## 📝 Next Steps

1. ✅ Backend deployed and working
2. ⏳ Wait for frontend build to complete
3. 🔧 If frontend build fails, recreate with Docker framework
4. 🔗 Test frontend-backend connection
5. 🎯 Test full Telegram parsing workflow
6. 📊 Monitor logs for any issues
7. 💾 Set up persistent storage for sessions (if needed)

## 🆘 Support

If you encounter issues:
1. Check build logs in Timeweb dashboard
2. Verify environment variables are set correctly  
3. Test backend health endpoint
4. Check CORS configuration
5. Review this troubleshooting guide

---

**Deployment Date**: 2025-11-04  
**Repository**: https://github.com/wemdio/Parser.git  
**Latest Commit**: 224d59839b203c71486d4a85771225ff6988790a
