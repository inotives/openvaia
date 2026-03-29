---
name: course_design
description: Curriculum design, learning objectives, assessment rubrics, and essay grading frameworks
tags: [education, curriculum, assessment, rubric, grading]
source: awesome-openclaw-agents/education/curriculum-designer, awesome-openclaw-agents/education/essay-grader
---

## Course Design and Assessment

> ~780 tokens

### Backward Design Process
1. **Define outcomes** — what should the learner be able to DO after this course?
2. **Design assessments** — how will you prove they can do it?
3. **Create content** — what do they need to learn to pass the assessments?

### Learning Objectives (Bloom's Taxonomy)
Every objective must start with a measurable verb:

| Level | Verbs | Example |
|-------|-------|---------|
| Remember | list, define, identify, recall | List the 5 stages of grief |
| Understand | explain, summarize, describe | Explain how TCP handshake works |
| Apply | use, implement, solve, calculate | Implement a binary search in Python |
| Analyze | compare, contrast, categorize, debug | Debug a race condition in concurrent code |
| Evaluate | assess, critique, justify, recommend | Evaluate trade-offs between SQL and NoSQL |
| Create | design, build, compose, propose | Design a REST API for a booking system |

Never use "understand" or "learn" as objectives — they are not measurable.

### Course Outline Template
```
Course: [Title]
Target: [audience + prerequisites]
Total: [hours] ([hours/week] x [weeks])

Module [N] (Week [N]): [Title]
- Lessons: [count], [hours]
- Objectives: [measurable verbs + outcomes]
- Assessment: [type] ([grading method])
- Activity: [hands-on exercise]
```

**Rules:**
- Formative assessment every 2-3 lessons
- Summative assessment per module
- No module exceeds 2 hours without a hands-on activity
- Include time estimates for each lesson
- Specify prerequisites and target audience

### Assessment Rubric Template
```
Rubric: [Assessment Name] | Total: [points]

[Dimension] ([points]):
- Excellent ([range]): [specific criteria]
- Good ([range]): [specific criteria]
- Needs Work ([range]): [specific criteria]
- Insufficient ([range]): [specific criteria]
```

### Essay Grading Framework

**Standard dimensions:**
| Dimension | Weight | What to Evaluate |
|-----------|--------|-----------------|
| Thesis/Argument | 25-30% | Clear, debatable, maintained throughout |
| Evidence/Support | 20-25% | Cited sources, relevant data, examples |
| Organization | 15-20% | Logical flow, transitions, structure |
| Writing Quality | 10-15% | Clarity, grammar, voice, word choice |
| Formatting | 5-10% | Citations, formatting, requirements met |

**Grading rules:**
- Score each dimension independently with justification
- Always highlight at least one genuine strength before weaknesses
- Feedback must be specific: point to the exact sentence, show how to fix it
- Provide a priority-ordered list of top 3 improvements for biggest impact
- Frame weaknesses as growth opportunities, not failures

**Feedback template:**
```
Overall Score: [X]/[Y] ([grade])

Rubric Breakdown:
- [Dimension] ([score]/[max]): [justification]

Strength Spotlight: [specific thing done well with reference to text]

Top 3 Improvements:
1. [specific, actionable improvement with before/after example]
2. [specific, actionable improvement]
3. [specific, actionable improvement]
```
