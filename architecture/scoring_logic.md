# ATS Scoring Logic

## Scoring Formula

```
ATS Score = Σ (category_score × weight / 100)
```

Each category is scored 0-100 independently, then weighted:

| # | Category | Weight | How It's Calculated |
|---|----------|--------|---------------------|
| 1 | Keyword Match | 30% | `(matched_keywords / total_jd_keywords) × 100` |
| 2 | Skill Relevance | 20% | `(matched_required_skills / total_required_skills) × 80 + (matched_preferred / total_preferred) × 20` |
| 3 | Project Quality | 15% | LLM assessment: relevance, impact quantification, tech alignment |
| 4 | Experience Alignment | 15% | Years match + responsibility overlap + seniority fit |
| 5 | Resume Formatting | 10% | Section presence, bullet consistency, length appropriateness |
| 6 | Education Fit | 5% | Degree level match + field relevance |
| 7 | Grammar / Readability | 5% | LLM assessment of writing quality |

## Score Bands

| Range | Band | Color Code | Meaning |
|-------|------|------------|---------|
| 85-100 | Excellent | `#10B981` (green) | Strong ATS match, likely to pass screening |
| 70-84 | Strong | `#3B82F6` (blue) | Good match, minor improvements possible |
| 50-69 | Needs Improvement | `#F59E0B` (amber) | Significant gaps, specific fixes needed |
| 0-49 | Weak | `#EF4444` (red) | Major mismatch, substantial rewrite needed |

## Deterministic vs LLM Scoring

Categories 1, 2, 5, 6 use **deterministic** algorithms (keyword counting, skill matching, section detection).

Categories 3, 4, 7 use **LLM assessment** with structured scoring rubrics to ensure consistency.

## Keyword Matching Algorithm

```python
1. Extract all keywords from JD (skills, tools, technologies, qualifications)
2. Normalize: lowercase, remove punctuation, expand abbreviations
3. Exact match: direct string comparison
4. Fuzzy match: cosine similarity > 0.85 between embeddings
5. Score = (exact_matches + 0.7 × fuzzy_matches) / total_keywords
```

## Formatting Score Rubric

| Check | Points |
|-------|--------|
| Has summary/objective section | 15 |
| Has skills section | 15 |
| Has experience section with dates | 15 |
| Has education section | 10 |
| Has projects section | 10 |
| Bullet points used (not paragraphs) | 10 |
| Reasonable length (1-2 pages worth) | 10 |
| Contact information complete | 10 |
| No excessive formatting artifacts | 5 |
