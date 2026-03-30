# Resume Analyzer — Project Context

## Purpose

A deterministic resume analysis platform that extracts structured data from resumes, compares against target job descriptions, produces weighted ATS scores, and delivers actionable improvement feedback.

## Architecture

```
Upload → Text Extraction → Entity Parsing → JD Comparison → ATS Scoring → Feedback Generation → Storage
```

**Key Principle**: Each step is a standalone Python module in `tools/`. The Flask server orchestrates the pipeline. The frontend is a premium SPA.

---

## Schemas

All schemas live in `schemas/` as JSON Schema files:

| File | Purpose |
|------|---------|
| `resume_input.json` | Validates upload API requests |
| `parsed_resume.json` | Structured resume data from LLM extraction |
| `job_description.json` | Structured JD data for comparison |
| `final_analysis.json` | Complete analysis output with scores and recommendations |

### Parsed Resume Fields
- `personal_info`: name, email, phone, location, links, summary
- `education[]`: institution, degree, field, GPA, dates
- `skills`: languages, frameworks, tools, databases, cloud, soft_skills
- `experience[]`: company, role, dates, responsibilities
- `projects[]`: title, description, technologies, impact, URLs
- `certifications[]`: name, issuer, date, credential_id
- `links[]`: label, url
- `confidence_notes[]`: fields with low extraction confidence

### Final Analysis Fields
- `ats_score`: 0-100 weighted total
- `score_band`: Weak (0-49) | Needs Improvement (50-69) | Strong (70-84) | Excellent (85-100)
- `category_scores`: per-category breakdown with weights
- `matched_keywords` / `missing_keywords`
- `semantic_similarity`: cosine similarity from embeddings
- `strengths` / `weaknesses`
- `recommendations[]`: section, priority, suggestion
- `rewritten_summary`: AI-improved summary
- `improved_bullet_points[]`: original vs improved

---

## ATS Scoring Weights

| Category | Weight | Description |
|----------|--------|-------------|
| Keyword Match | 30% | JD keywords found in resume |
| Skill Relevance | 20% | Skills alignment with JD requirements |
| Project Quality | 15% | Projects demonstrate relevant capability |
| Experience Alignment | 15% | Role/responsibility match with JD |
| Resume Formatting | 10% | Structure, readability, ATS-friendliness |
| Education Fit | 5% | Education matches JD qualifications |
| Grammar / Readability | 5% | Writing quality and clarity |

---

## Behavioral Rules

1. **Never guess missing fields** — mark as `null` with a confidence note
2. **Extraction order**: Direct text extraction first → OCR.Space fallback only on failure
3. **Store intermediates** in `.tmp/` — never clutter `outputs/`
4. **Update `progress.md`** after every major pipeline step
5. **Log discoveries** in `findings.md`
6. **Schema is law** — all outputs must validate against their schema
7. **Fail gracefully** — if an API fails, return a partial result with error context, never crash silently

## Architectural Invariants

1. Each tool in `tools/` is a standalone module with a `main()` function
2. Tools communicate via JSON — no object coupling between modules
3. The Flask server never contains business logic — it only orchestrates tools
4. All API responses follow `{ "success": bool, "data": {}, "error": str|null }` format
5. Environment variables are loaded once in `app.py` and passed explicitly to tools
6. MongoDB writes happen only after successful full pipeline completion
7. Frontend communicates exclusively via REST API — no server-side rendering
