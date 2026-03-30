# Feedback Generation Rules

## Principles

1. **Actionable**: Every recommendation must include a specific action the user can take
2. **Prioritized**: Recommendations sorted by impact (high → medium → low)
3. **Section-Specific**: Link each suggestion to a resume section
4. **Example-Driven**: Show before/after where possible

## Feedback Categories

### 1. Missing Keywords (Priority: High)
- List JD keywords not found in resume
- Suggest where to naturally incorporate them
- Warn against keyword stuffing

### 2. Weak Bullet Points (Priority: High)
- Identify bullets without quantified impact
- Rewrite with STAR method (Situation, Task, Action, Result)
- Add metrics where inferable

### 3. Summary Rewrite (Priority: Medium)
- Generate a tailored professional summary
- Align with JD's key requirements
- Keep under 3 sentences

### 4. Skills Gap (Priority: Medium)
- Identify missing required skills
- Suggest related skills the candidate might have
- Recommend learning resources for critical gaps

### 5. Formatting Improvements (Priority: Low)
- Suggest section reordering for ATS
- Flag problematic formatting
- Recommend optimal resume length

## Rewrite Rules

When rewriting bullet points:
- Start with strong action verbs
- Include quantified results (%, $, time saved)
- Match JD terminology
- Keep under 2 lines

### Action Verb Categories
- **Leadership**: Directed, Orchestrated, Spearheaded, Championed
- **Technical**: Engineered, Architected, Implemented, Optimized
- **Achievement**: Achieved, Delivered, Exceeded, Accelerated
- **Analysis**: Analyzed, Evaluated, Assessed, Investigated

## Output Structure

```json
{
  "recommendations": [
    {
      "section": "experience",
      "priority": "high",
      "suggestion": "Add quantified impact to your role at Company X. Example: 'Reduced API response time by 40% through query optimization'"
    }
  ],
  "rewritten_summary": "Results-driven software engineer...",
  "improved_bullet_points": [
    {
      "original": "Worked on the backend API",
      "improved": "Engineered RESTful API serving 10K+ daily requests, reducing response latency by 35% through Redis caching and query optimization",
      "section": "experience"
    }
  ]
}
```
