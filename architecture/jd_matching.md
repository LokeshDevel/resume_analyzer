# JD Matching Architecture

## Two-Layer Matching Strategy

### Layer 1: Keyword Matching (Fast, Deterministic)

1. **JD Keyword Extraction**: Use OpenAI to extract structured keywords from raw JD text
2. **Resume Keyword Extraction**: Pull from parsed resume skills, project technologies, experience responsibilities
3. **Exact Match**: Case-insensitive direct comparison
4. **Synonym Expansion**: Common equivalences (e.g., "JS" = "JavaScript", "K8s" = "Kubernetes")

### Layer 2: Semantic Matching (Deep, Embedding-Based)

1. **Embed resume sections**: Create embeddings for skills, experience, projects
2. **Embed JD sections**: Create embeddings for requirements, responsibilities
3. **Cosine Similarity**: Compare section-by-section
4. **Threshold**: similarity > 0.75 counts as semantic match

## Embedding Model

Using `text-embedding-3-small` for cost efficiency:
- 1536 dimensions
- $0.02 per 1M tokens
- Sufficient accuracy for keyword-level comparison

## Output Format

```json
{
  "keyword_match": {
    "matched": ["Python", "React", "AWS"],
    "missing": ["Terraform", "GraphQL"],
    "match_ratio": 0.6
  },
  "semantic_match": {
    "skills_similarity": 0.82,
    "experience_similarity": 0.71,
    "overall_similarity": 0.76
  },
  "section_analysis": {
    "skills": { "match_level": "strong", "gaps": ["DevOps tools"] },
    "experience": { "match_level": "moderate", "gaps": ["team leadership"] },
    "projects": { "match_level": "strong", "gaps": [] }
  }
}
```
