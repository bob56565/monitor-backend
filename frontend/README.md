# Monitor Health Frontend

A comprehensive web interface for the Monitor Health Cascade Inference Engine.

## Features

- **Multi-Category Input:** Organized tabs for Lipid, Glycemic, Kidney, Liver, Inflammatory, Vitals, Body, and Thyroid biomarkers
- **Real-time Cascade:** Watch as your inputs cascade into 40+ derived values
- **Confidence Scores:** Every calculation shows confidence level
- **PMID Citations:** Direct links to PubMed for validation
- **Risk Interpretation:** Color-coded risk levels for key metrics
- **Smart Suggestions:** Recommendations for high-value next tests

## Deployment

### Option 1: Cloudflare Pages
```bash
cd frontend
npx wrangler pages publish . --project-name=monitor-health
```

### Option 2: Vercel
```bash
cd frontend
vercel
```

### Option 3: Local
```bash
cd frontend
python -m http.server 8080
# Open http://localhost:8080
```

### Option 4: Direct File
Just open `index.html` in your browser - it's a single-file app that calls the live API.

## API Connection

The frontend connects to:
```
https://monitor-api.abedelhamdan.workers.dev
```

All API calls are made client-side to the Cloudflare Worker backend.

## Demo

Click "Load Demo Data" to see the cascade in action with sample values that produce 53 total outputs from 12 inputs.

## Customization

The UI uses Tailwind CSS (via CDN) for styling. All code is in a single HTML file for simplicity.

To modify:
1. Edit `index.html`
2. Test locally
3. Deploy to your preferred hosting
