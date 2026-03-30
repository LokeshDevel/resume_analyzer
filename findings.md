# Resume Analyzer — Findings

## Decisions Made

1. **Flask over FastAPI**: Chose Flask for simplicity since this is a file-upload-heavy app. FastAPI's async benefits aren't critical here since the bottleneck is OpenAI API calls, not concurrent connections.

2. **GPT-4.1-mini as default model**: Balances cost and quality. Entity extraction and feedback don't need the full GPT-4.1 model. Can be upgraded by changing the model string.

3. **text-embedding-3-small**: Cheapest embedding model with good enough accuracy for keyword-level semantic matching.

4. **Deterministic + LLM hybrid scoring**: Categories like keyword matching use exact algorithms (reproducible, fast). Categories like project quality use LLM assessment (more nuanced). This avoids the problem of LLM scores being non-deterministic across runs.

5. **Local file storage over GridFS**: Simpler for v1. Uploaded files are copied to `.tmp/` after processing for debugging, then removed from `uploads/`.

## Known Limitations

1. OCR.Space free tier: 25K requests/month, 1MB file size limit for free tier
2. No authentication in v1 — anyone with the URL can use the analyzer
3. MongoDB is optional — the app falls back to local JSON file storage
4. No rate limiting on the API endpoints
