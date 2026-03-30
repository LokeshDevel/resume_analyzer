# Resume Pipeline Architecture

## Overview

The resume analysis pipeline is a sequential 6-stage process. Each stage is a standalone Python module in `tools/` that accepts JSON input and produces JSON output.

## Pipeline Stages

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────┐    ┌─────────────┐
│ parse_resume │───►│ extract_     │───►│ compare_with_ │───►│ score_resume │───►│ generate_   │
│    .py       │    │ entities.py  │    │ job_desc.py   │    │    .py       │    │ feedback.py │
└─────────────┘    └──────────────┘    └───────────────┘    └──────────────┘    └─────────────┘
  File → Text       Text → JSON        Resume + JD →        Match Data →       Score + Resume →
                                        Match Data           ATS Score          Recommendations
```

## Stage Details

### 1. parse_resume.py
- **Input**: File path (PDF/DOCX/PNG/JPG)
- **Output**: `{ "text": str, "method": str, "page_count": int }`
- **Strategy**: 
  - PDF: Try PyPDF2 direct extraction first
  - DOCX: Use python-docx paragraph extraction
  - Image: Go directly to OCR.Space
  - Fallback: If direct extraction yields < 50 chars, use OCR.Space
- **Error handling**: Returns empty text with error field if all methods fail

### 2. extract_entities.py
- **Input**: Raw text string
- **Output**: `parsed_resume.json` compliant object
- **Strategy**: Single OpenAI API call with structured output prompt
- **Confidence**: Any field the model is uncertain about gets `null` + confidence note

### 3. compare_with_job_description.py
- **Input**: Parsed resume JSON + Job description text
- **Output**: `{ "matched_keywords": [], "missing_keywords": [], "similarity_scores": {} }`
- **Strategy**:
  - Step 1: Extract structured JD data via OpenAI
  - Step 2: Keyword matching (exact + fuzzy via embeddings)
  - Step 3: Section-level semantic similarity via OpenAI embeddings

### 4. score_resume.py
- **Input**: Comparison results + parsed resume
- **Output**: `{ "ats_score": int, "category_scores": {}, "score_band": str }`
- **Strategy**: Deterministic weighted calculation from comparison data

### 5. generate_feedback.py
- **Input**: Score results + parsed resume + JD
- **Output**: Final analysis JSON with recommendations, rewritten summary, improved bullets
- **Strategy**: Single OpenAI API call focused on actionable improvement

## Data Flow

```
File upload
    │
    ▼
Raw text (string)
    │
    ▼
Parsed resume (JSON matching parsed_resume.json schema)
    │
    ├──► Comparison results (matched/missing keywords, similarity)
    │       │
    │       ▼
    │    ATS score (weighted total + category breakdown)
    │       │
    │       ▼
    └──► Final analysis (full report with recommendations)
            │
            ▼
         MongoDB storage + JSON export
```

## Error Recovery

- Each stage returns a standardized `{ "success": bool, "data": {}, "error": str }` envelope
- Pipeline halts on stage failure and returns partial results up to the failed stage
- All intermediate results are cached in `.tmp/` for debugging
