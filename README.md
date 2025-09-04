# LinkedIn Scout 🕵️

An AI-powered LinkedIn contact discovery tool that uses local models and browser automation to find prospects based on your company lists and search criteria.

## Architecture

**Python + Local AI + Browser Automation:**
- **Local AI Models**: Uses Ollama for profile evaluation and connection justifications only
- **Browser Automation**: Playwright follows natural LinkedIn navigation (company → people → filter)
- **Local Storage**: SQLite for data persistence and privacy
- **CLI Interface**: Rich command-line interface with Typer
- **Efficient Design**: Minimal AI usage, maximum automation reliability

## Key Features

- 🎯 **Natural Navigation**: Mimics manual LinkedIn workflow (company → people → filter)
- 🤖 **Smart Evaluation**: AI evaluates profiles and generates connection justifications
- 🏢 **Company-Focused**: Search multiple companies with job title filtering
- 📊 **Export Options**: CSV, JSON, Excel with customizable fields
- 🔒 **Privacy First**: All data and AI processing stays local
- ⚡ **Efficient**: Minimal AI calls, maximum reliability

## Getting Started

```bash
# Install dependencies
pip install -e .

# Run search with your criteria (as per design doc)
linkedin-scout search \
    --companies "Anduril,Anthropic,Figma" \
    --job-titles "software engineer,engineering manager,recruiter" \
    --total-results 50 \
    --results-per-company 20 \
    --output contacts.csv

# The tool will:
# 1. Navigate to each company's LinkedIn page
# 2. Filter by job titles using LinkedIn's native filters
# 3. Extract profile data via Playwright
# 4. Use local AI to evaluate relevance and generate justifications
# 5. Export results with connection reasoning
```

## Architecture Components

### Core Modules
- **`browser/`**: CompanyNavigator for LinkedIn automation
- **`search/`**: CompanySearchController orchestrates searches
- **`agents/`**: ProfileEvaluator for AI-powered profile assessment
- **`database/`**: SQLite models and migrations (TODO)
- **`export/`**: Multiple export formats (TODO)
- **`cli/`**: Command-line interface (TODO)

### AI Integration (Minimal & Targeted)
- **ProfileEvaluator**: Scores profiles against search criteria
- **JustificationGenerator**: Creates connection reasoning
- **CompanyExpander**: Suggests similar companies (TODO)

### Search Flow
1. **Navigate**: Company page → People tab
2. **Filter**: Apply job title filters via LinkedIn UI
3. **Extract**: Scrape profile data with Playwright
4. **Evaluate**: AI scores relevance and generates justifications
5. **Export**: Output qualified contacts with reasoning

## Local AI Setup

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a compatible model (or use any model you have)
ollama pull llama3.2:3b

# Configure your model in the config (default works for most setups)
# AI is only used for profile evaluation and justification generation
```

## Current Status

✅ **Completed:**
- Architecture redesign (company-focused approach)
- ProfileEvaluator for AI-powered profile assessment
- CompanyNavigator for LinkedIn automation  
- CompanySearchController orchestration
- Data models and types

🚧 **In Progress:**
- CLI implementation
- Database models and migrations
- Export functionality

See `TODO.md` for detailed implementation status.