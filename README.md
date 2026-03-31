# 🚀 Resume Analyzer AI

An intelligent, AI-powered tool designed to analyze resumes, provide detailed ATS (Applicant Tracking System) scoring, and automatically improve your resume's content using advanced language models.

## ✨ Features

- **Deep AI Analysis:** Leverages the Groq API (Llama 3 / Mixtral) to analyze your resume against industry standards, extracting strengths, weaknesses, and calculating an ATS score.
- **Auto-Fix DOCX Resumes:** Upload a `.docx` resume, and the system can **automatically patch it** with AI-improved bullet points—perfectly preserving your original formatting, fonts, and table structures!
- **Multi-Format Support:** Accurately parses `.docx` and `.pdf` files.
- **Built-in OCR:** Integrates with OCR.Space to extract text even from flattened or scanned PDF resumes.
- **Detailed Score Breakdown:** Get weighted scores for:
  - Keyword Match
  - Skill Relevance
  - Experience Alignment
  - Resume Formatting
  - Education Fit
  - Grammar & Readability
  - Project Quality
- **Export & Download:** Download your results as a structured JSON file or a beautifully formatted DOCX report.
- **History Management:** (Optional) Integrates with MongoDB to save your past analyses, letting you review your progress over time.
- **Premium UI:** A responsive, dark-mode, glassmorphic frontend built natively without heavy JS frameworks to ensure blazing fast speeds.

---

## 🛠️ Technology Stack

- **Backend:** Python 3, Flask
- **Frontend:** Vanilla JavaScript, HTML5, Vanilla CSS
- **AI / LLM:** Groq API
- **Document Processing:** `python-docx`, `PyMuPDF` (fitz)
- **OCR:** OCR.Space API
- **Database:** MongoDB (for history management)

---

## ⚙️ Prerequisites & Setup

### 1. Clone the repository
```bash
git clone https://github.com/LokeshDevel/resume_analyzer.git
cd resume_analyzer
```

### 2. Set up a Python Virtual Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add your API keys:

```ini
# Required: Get your ultra-fast LLM API key from https://console.groq.com/
GROQ_API_KEY=your_groq_api_key_here

# Required for PDF processing: Get your free key from https://ocr.space/OCRAPI
OCR_SPACE_API_KEY=your_ocr_space_api_key_here

# Optional: For saving/loading analysis history
MONGODB_URI=your_mongodb_connection_string
```

---

## 🚀 Running the Application

Start the Flask server:
```bash
python app.py
```

Open your browser and navigate to: **`http://localhost:5000`**

---

## 📂 Project Structure

```text
resume_analyzer/
├── app.py                     # Main Flask application and API routing
├── requirements.txt           # Python dependencies
├── .env                       # API keys and environment variables
├── frontend/                  # Static web assets
│   ├── index.html             # Main UI layout
│   ├── style.css              # Glassmorphic design system
│   └── app.js                 # UI interactions, API fetches, File downloads
├── tools/                     # Core backend logic modules
│   ├── parse_resume.py        # Extracts text from DOCX and PDFs
│   ├── extract_entities.py    # Interfaces with Groq to structure the AI analysis
│   ├── score_resume.py        # Weights and computes the final ATS scores
│   ├── resume_updater.py      # Core logic for Auto-Fix (patches .docx files)
│   ├── docx_generator.py      # Generates downloading DOCX reports
│   └── history_manager.py     # MongoDB integration for saving analyses
├── uploads/                   # Temporary storage for uploaded raw files
├── .tmp/                      # Temporary storage for intermediate processing
└── outputs/                   # Safe storage for generated reports
```

## 📝 License

This project is free to use and modify for personal and educational purposes.
