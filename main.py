"""Required CSV + LLM processing pipeline for Mess Feedback Sorter.
Run: python main.py
Optional OpenAI: set OPENAI_API_KEY. Offline rule-based fallback works without it.
"""
import csv, json, os, re
from pathlib import Path
from collections import Counter
from datetime import datetime

ROOT=Path(__file__).parent
INPUT=ROOT/"feedback.csv"
PROMPT_FILE=ROOT/"system_prompt.txt"
RESULTS=ROOT/"results.csv"
URGENT=ROOT/"urgent.csv"
SUMMARY=ROOT/"summary.txt"
CATEGORIES=["Food quality and taste","Food quantity / portion size","Food hygiene and cleanliness",
"Food safety / suspected contamination","Menu variety and planning","Timings and service delays",
"Staff behaviour and service","Drinking water and facilities","Dining hall cleanliness and maintenance","Other / uncategorised"]
FIELDS=["category","sentiment","urgency","summary"]
def classify(comment):
    t=(comment or "").lower()
    high=["insect","hair","expired","illness","food poisoning","vomit","allergy","glass","worm","raw chicken","contaminat","foreign object"]
    medium=["cold","dirty","delay","late","poor","bad","salty","bland","small portion"]
    category="Other / uncategorised"
    mapping=[(["insect","hair","expired","food poisoning","contaminat","glass","worm"],"Food safety / suspected contamination"),
    (["dirty","hygiene","unclean"],"Food hygiene and cleanliness"),(["quantity","portion","less food"],"Food quantity / portion size"),
    (["late","delay","waiting"],"Timings and service delays"),(["taste","tasty","bland","salty"],"Food quality and taste"),
    (["menu","variety"],"Menu variety and planning"),(["staff","behaviour"],"Staff behaviour and service"),
    (["water","drinking"],"Drinking water and facilities"),(["dining hall","table","cleanliness"],"Dining hall cleanliness and maintenance")]
    for keys,label in mapping:
        if any(k in t for k in keys): category=label;break
    urgency="High" if any(k in t for k in high) else ("Medium" if any(k in t for k in medium) else "Low")
    sentiment="Negative" if any(k in t for k in ["bad","poor","dirty","cold","late","not good","disappoint","insect","hair","expired","illness"]) else ("Positive" if any(k in t for k in ["good","great","tasty","excellent","fresh","love"]) else "Neutral")
    return {"category":category,"sentiment":sentiment,"urgency":urgency,"summary":(comment or "").strip()[:180]}
def parse_reply(raw):
    if isinstance(raw,dict): return raw
    return json.loads(raw)
def is_valid(data):
    return isinstance(data,dict) and set(FIELDS).issubset(data) and data["category"] in CATEGORIES and data["sentiment"] in ["Positive","Negative","Neutral"] and data["urgency"] in ["Low","Medium","High"] and isinstance(data["summary"],str)
def apply_safety_net(comment,analysis):
    local=classify(comment)
    if not is_valid(analysis): analysis={**local,"needs_manual_review":1}
    rank={"Low":0,"Medium":1,"High":2}
    if rank[local["urgency"]]>rank[analysis["urgency"]]:
        analysis=dict(analysis);analysis["urgency"]=local["urgency"]
    analysis["safety_flag"]=int(local["urgency"]=="High")
    return analysis
def call_llm(comment):
    from openai import OpenAI
    client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    system=PROMPT_FILE.read_text(encoding="utf-8")
    response=client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":system},{"role":"user","content":comment}],
        response_format={"type":"json_object"})
    return response.choices[0].message.content
def process_one(comment):
    if not (comment or "").strip():
        return {"category":"Other / uncategorised","sentiment":"Neutral","urgency":"Low","summary":"","safety_flag":0,"needs_manual_review":1}
    if not os.getenv("OPENAI_API_KEY"):
        return apply_safety_net(comment,classify(comment))
    for attempt in range(2):
        try:
            data=parse_reply(call_llm(comment))
            if is_valid(data): return apply_safety_net(comment,data)
        except Exception:
            pass
    fallback=apply_safety_net(comment,classify(comment))
    fallback["needs_manual_review"]=1
    return fallback
def write_reports(records):
    columns=["id","comment",*FIELDS,"safety_flag","needs_manual_review"]
    with RESULTS.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(records)
    urgent=[r for r in records if r["urgency"]=="High"]
    with URGENT.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(urgent)
    total=len(records);negative=sum(r["sentiment"]=="Negative" for r in records)
    counts=Counter(r["category"] for r in records)
    lines=[f"Generated: {datetime.now():%Y-%m-%d %H:%M}",f"Total feedback: {total}",
           f"Negative feedback: {negative} ({negative/total*100 if total else 0:.1f}%)","Category counts:"]
    lines += [f"  {k}: {v}" for k,v in sorted(counts.items())]
    lines.append("Urgent complaints:")
    lines += [f"  {r['id']}: {r['comment']}" for r in urgent]
    SUMMARY.write_text("\n".join(lines)+"\n",encoding="utf-8")
def main():
    records=[]
    with INPUT.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or "comment" not in reader.fieldnames:
            raise ValueError("feedback.csv must include a 'comment' column.")
        for i,row in enumerate(reader,1):
            original=row.get("comment","") or ""
            result=process_one(original)
            records.append({"id":row.get("id",str(i)),"comment":original,**result})
    write_reports(records)
    print(f"Processed {len(records)} rows. Wrote results.csv, urgent.csv and summary.txt.")
if __name__=="__main__": main()
