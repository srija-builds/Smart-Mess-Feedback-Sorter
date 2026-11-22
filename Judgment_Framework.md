# Judgment Framework (demo defaults; faculty approval required)

| Dimension | Allowed values | Guideline |
|---|---|---|
| Category | One approved category from `main.py` | Classify the main concern; preserve original comment |
| Sentiment | Positive / Neutral / Negative | Based on expressed opinion, not presumed intent |
| Urgency | Low / Medium / High | High for possible safety/health concerns; Medium for repeated/service/quality concerns; Low for general suggestions |
| Safety flag | true / false | Potential concern only; always human-review |
| Manual review | true / false | Empty input or invalid model output after one retry |

Safety-net terms include insect, hair, expired, illness, food poisoning, allergy, glass, worm, raw chicken, contamination and foreign object. The Python safety net may raise urgency, never lower the model's urgency. This is a suggested starting policy and must be approved/tuned by the institution.
