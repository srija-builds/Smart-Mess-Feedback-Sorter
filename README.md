# Mess_Feedback_Sorter — Smart Mess Feedback & Management System

## Included
- Streamlit Student Portal and restricted Admin Portal
- Student feedback, four meal ratings, private complaint history, admin replies/status
- Weekly menu, favourite dish polls, dish suggestions and approval, votes on approved dishes
- Student Feature Requests with admin review/status notes
- Admin dashboard, urgency/category charts, feedback correction, assignment, report downloads and audit log
- Required standalone CSV + JSON + LLM batch pipeline (`main.py`) with `classify()`, `parse_reply()`, `is_valid()`, `apply_safety_net()`, `write_reports()`
- 20 sample feedback records, system prompt, test suite and output files

## Run
Python 3.10+ recommended.
```bash
pip install -r requirements.txt
streamlit run app.py
```
Demo accounts: `student` / `student123`; `admin` / `admin123`.
The demo passwords are for local demonstration only. Replace them with institution-approved secure authentication before deployment.

## Required batch pipeline
```bash
python main.py
python -m unittest test.py
```
`main.py` works offline using a transparent local classifier. To use an LLM, set `OPENAI_API_KEY` before running. The model output is validated and retried once; after failure the record is marked for manual review. The Python safety net can raise urgency but never lowers it. Counts and report calculations are performed in Python.

## Generated outputs
- `results.csv`: all input records and analysis
- `urgent.csv`: only High urgency records, preserving original comments
- `summary.txt`: category counts, negative-feedback percentage and urgent list

## Important
This is a submission/demo MVP. AI and keyword screening can be wrong; a High flag is not proof of contamination or illness. Serious reports require human review. Do not use real student data in a public demo. Confirm official categories, AI provider permissions, and privacy rules with your faculty.
