# One-page project specification — draft for faculty review

**Project:** Mess Feedback Sorter / Smart Mess Feedback & Management System  
**Purpose:** Collect student mess feedback, ratings, dish votes and suggestions; classify comments; highlight possible urgent safety concerns; and support admin responses and reporting.

**Users:** Students and authorised mess administrators. Students can submit feedback, see their own status/replies, view menu, vote in polls, suggest dishes, and submit feature requests. Admins can review/classify/assign/answer complaints, update statuses, manage menu/polls/suggestions/feature requests, and export reports.

**Technology:** Python, Streamlit, SQLite, CSV/JSON, optional LLM API, pandas charts.  
**Responsible AI:** Validate structured JSON; retry invalid response once; manual-review fallback; Python safety net may raise but never lower urgency; AI flags are not diagnoses or proof.  
**Outputs:** `results.csv`, `urgent.csv`, `summary.txt`.  
**Privacy/security:** Role-restricted admin portal, demo-only credentials, minimal student data, no public display of identities. Replace demo authentication before deployment.  
**Approval needed:** Confirm categories, urgency policy, AI provider/data rules, anonymity, credential policy and evaluation test cases with faculty.
