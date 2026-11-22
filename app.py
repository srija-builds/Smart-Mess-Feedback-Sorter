import os, sqlite3, json, re, hashlib, secrets
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT=Path(__file__).parent
DB=ROOT/"mess_app.db"
CATEGORIES=["Food quality and taste","Food quantity / portion size","Food hygiene and cleanliness","Food safety / suspected contamination","Menu variety and planning","Timings and service delays","Staff behaviour and service","Drinking water and facilities","Dining hall cleanliness and maintenance","Other / uncategorised"]
STATUSES=["Pending","Under Review","In Progress","Resolved","Reopened"]
DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
def db():
    return sqlite3.connect(DB,check_same_thread=False)
def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, passhash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, anonymous INTEGER DEFAULT 0, meal TEXT, comment TEXT, taste INTEGER, quality INTEGER, hygiene INTEGER, quantity INTEGER, category TEXT, sentiment TEXT, urgency TEXT, summary TEXT, safety_flag INTEGER DEFAULT 0, needs_review INTEGER DEFAULT 0, status TEXT DEFAULT 'Pending', assigned TEXT DEFAULT '', reply TEXT DEFAULT '', resolution TEXT DEFAULT '', created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS menu(id INTEGER PRIMARY KEY AUTOINCREMENT, week TEXT, day TEXT, meal TEXT, items TEXT, published INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS dishes(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, name TEXT, description TEXT, status TEXT DEFAULT 'Pending', votes INTEGER DEFAULT 0, created TEXT);
        CREATE TABLE IF NOT EXISTS polls(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, period TEXT, options TEXT, active INTEGER DEFAULT 1, created TEXT);
        CREATE TABLE IF NOT EXISTS votes(poll_id INTEGER, username TEXT, option TEXT, created TEXT, PRIMARY KEY(poll_id,username));
        CREATE TABLE IF NOT EXISTS feature_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, title TEXT, details TEXT, status TEXT DEFAULT 'Submitted', admin_note TEXT DEFAULT '', created TEXT);
        CREATE TABLE IF NOT EXISTS feature_votes(request_id INTEGER, username TEXT, PRIMARY KEY(request_id,username));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, record_type TEXT, record_id INTEGER, details TEXT, created TEXT);
        """)
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]==0:
            c.executemany("INSERT INTO users VALUES(?,?,?,1)",[
                ("student",hashpw("student123"),"student"),("admin",hashpw("admin123"),"admin")])
        if c.execute("SELECT COUNT(*) FROM menu").fetchone()[0]==0:
            week=date.today().strftime("%Y-%W")
            rows=[]
            sample={"Monday":("Idli, sambar, chutney","Rice, dal, poriyal, curd","Chapati, kurma"),
            "Tuesday":("Pongal, sambar","Rice, rasam, vegetables","Dosa, chutney"),
            "Wednesday":("Upma, chutney","Lemon rice, curd","Chapati, chana masala"),
            "Thursday":("Idli, sambar","Rice, sambar, poriyal","Vegetable pulao, raita"),
            "Friday":("Pongal, chutney","Rice, dal, vegetables","Poori, kurma"),
            "Saturday":("Dosa, sambar","Rice, rasam, poriyal","Chapati, dal"),
            "Sunday":("Bread, jam, milk","Veg biryani, raita","Curd rice")}
            for d,meals in sample.items():
                for meal,items in zip(["Breakfast","Lunch","Dinner"],meals): rows.append((week,d,meal,items,1))
            c.executemany("INSERT INTO menu(week,day,meal,items,published) VALUES(?,?,?,?,?)",rows)
        if c.execute("SELECT COUNT(*) FROM polls").fetchone()[0]==0:
            c.execute("INSERT INTO polls(title,period,options,active,created) VALUES(?,?,?,?,?)",
                      ("Favourite dish of the week","Weekly","Idli;Dosa;Veg biryani;Chapati",1,now()))
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def hashpw(p): return hashlib.sha256(p.encode()).hexdigest()
def log(actor,action,typ,rid,details=""):
    with db() as c:c.execute("INSERT INTO audit(actor,action,record_type,record_id,details,created) VALUES(?,?,?,?,?,?)",(actor,action,typ,rid,details,now()))
def local_analysis(text):
    t=text.lower()
    high=["insect","hair","expired","illness","food poisoning","vomit","allergy","glass","worm","raw chicken","contaminat","stomach pain","foreign object"]
    medium=["cold","dirty","delay","late","poor","bad","salty","bland","quantity","small portion","unclean"]
    cat="Other / uncategorised"
    for key,label in [("hygiene","Food hygiene and cleanliness"),("dirty","Food hygiene and cleanliness"),("quantity","Food quantity / portion size"),("portion","Food quantity / portion size"),("delay","Timings and service delays"),("late","Timings and service delays"),("taste","Food quality and taste"),("food poisoning","Food safety / suspected contamination"),("insect","Food safety / suspected contamination"),("hair","Food safety / suspected contamination"),("expired","Food safety / suspected contamination")]:
        if key in t: cat=label;break
    urgency="High" if any(x in t for x in high) else ("Medium" if any(x in t for x in medium) else "Low")
    sentiment="Negative" if any(x in t for x in ["bad","poor","dirty","cold","late","not good","hate","disappoint","insect","hair","expired","illness"]) else ("Positive" if any(x in t for x in ["good","great","tasty","excellent","love","fresh"]) else "Neutral")
    return {"category":cat,"sentiment":sentiment,"urgency":urgency,"summary":text[:160].strip(),"safety_flag":int(urgency=="High"),"needs_review":0}
def analyse(text):
    # Reliable offline fallback. Optional LLM can be added through main.py batch pipeline.
    result=local_analysis(text)
    if not text.strip(): return {"category":"Other / uncategorised","sentiment":"Neutral","urgency":"Low","summary":"","safety_flag":0,"needs_review":1}
    return result
def frame(query,params=()):
    with db() as c:return pd.read_sql_query(query,c,params=params)
def add_feedback(user,anon,meal,comment,ratings):
    a=analyse(comment)
    with db() as c:
        cur=c.execute("""INSERT INTO feedback(username,anonymous,meal,comment,taste,quality,hygiene,quantity,category,sentiment,urgency,summary,safety_flag,needs_review,status,created,updated)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?)""",
        (user,int(anon),meal,comment,*ratings,a["category"],a["sentiment"],a["urgency"],a["summary"],a["safety_flag"],a["needs_review"],"Pending",now(),now()))
        rid=cur.lastrowid
    log(user,"submitted","feedback",rid)
    return rid,a
init()
st.set_page_config(page_title="Mess Feedback Sorter",page_icon="🍲",layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.5rem;max-width:1200px}
[data-testid="stMetric"]{background:#f5f8fc;padding:14px;border-radius:12px}
div.stButton>button{border-radius:10px}
</style>""",unsafe_allow_html=True)
st.title("🍲 Smart Mess Feedback & Management System")
st.caption("Student voice → responsible review → visible action")
if "auth" not in st.session_state: st.session_state.auth=None
if "role" not in st.session_state: st.session_state.role=None
with st.sidebar:
    st.header("Account")
    if st.session_state.auth:
        st.success(f"{st.session_state.auth} · {st.session_state.role.title()}")
        if st.button("Log out"):
            st.session_state.auth=None;st.session_state.role=None;st.rerun()
    else:
        role=st.radio("Portal",["Student","Admin"])
        u=st.text_input("Username");p=st.text_input("Password",type="password")
        st.caption("Demo: student / student123 · admin / admin123")
        if st.button("Sign in",type="primary"):
            rec=frame("SELECT passhash,role,active FROM users WHERE username=?",(u,))
            if not rec.empty and rec.iloc[0].passhash==hashpw(p) and rec.iloc[0].active and rec.iloc[0].role==role.lower():
                st.session_state.auth=u;st.session_state.role=role.lower();st.rerun()
            else: st.error("Invalid login or account role.")
if not st.session_state.auth:
    st.info("Sign in using the demo account details in the sidebar.")
    c1,c2,c3=st.columns(3);c1.metric("Student features","Feedback + polls");c2.metric("Admin features","Review + actions");c3.metric("Analysis","Safety-screening aid")
    st.stop()
user=st.session_state.auth; role=st.session_state.role
if role=="student":
    st.subheader("Student Portal")
    tabs=st.tabs(["Dashboard","Submit feedback","My complaints","Weekly menu","Dish polls","Suggest a dish","Feature requests"])
    with tabs[0]:
        own=frame("SELECT * FROM feedback WHERE username=? ORDER BY id DESC",(user,))
        x,y,z=st.columns(3);x.metric("My submissions",len(own));y.metric("Open complaints",int((~own.status.eq("Resolved")).sum()) if len(own) else 0);z.metric("Resolved",int(own.status.eq("Resolved").sum()) if len(own) else 0)
        st.write("Use the tabs to send feedback, check replies, vote on dishes, or suggest improvements.")
        st.subheader("Latest mess announcements")
        st.info("Please submit urgent food-safety concerns promptly. Automated flags are only screening aids and require human review.")
    with tabs[1]:
        with st.form("feedback"):
            meal=st.selectbox("Meal",["Breakfast","Lunch","Snacks","Dinner"])
            anon=st.checkbox("Submit anonymously (your account is still used privately to show your own status)")
            comment=st.text_area("Feedback or complaint",max_chars=3000,placeholder="Describe the meal or service issue…")
            st.write("Rate each area (1 = poor, 5 = excellent)")
            r1,r2,r3,r4=st.columns(4)
            ratings=[r1.slider("Taste",1,5,3),r2.slider("Quality",1,5,3),r3.slider("Hygiene",1,5,3),r4.slider("Quantity",1,5,3)]
            send=st.form_submit_button("Submit feedback",type="primary")
        if send:
            if not comment.strip(): st.error("Feedback cannot be empty.")
            elif len(comment.strip())<5: st.warning("Please add a little more detail so the mess team can understand.")
            else:
                rid,a=add_feedback(user,anon,meal,comment.strip(),ratings)
                st.success(f"Submitted. Your reference number is FB-{rid:05d}.")
                st.write(f"Screening result: **{a['category']} · {a['sentiment']} · {a['urgency']} urgency**")
                if a["safety_flag"]: st.warning("Potential safety concern: sent for human review. This is not a diagnosis or proof of contamination.")
    with tabs[2]:
        mine=frame("SELECT id,meal,comment,urgency,status,reply,resolution,created,updated FROM feedback WHERE username=? ORDER BY id DESC",(user,))
        if mine.empty: st.info("You have not submitted feedback yet.")
        else:
            for _,r in mine.iterrows():
                with st.expander(f"FB-{int(r.id):05d} · {r.meal} · {r.status} · {r.created}"):
                    st.write(r.comment);st.write(f"Urgency: {r.urgency}")
                    st.write("Admin reply: "+(r.reply or "No reply yet"))
                    if r.resolution: st.write("Resolution: "+r.resolution)
    with tabs[3]:
        m=frame("SELECT day,meal,items FROM menu WHERE published=1 ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END, meal")
        st.dataframe(m,use_container_width=True,hide_index=True)
    with tabs[4]:
        polls=frame("SELECT * FROM polls WHERE active=1 ORDER BY id DESC")
        if polls.empty: st.info("No active polls right now.")
        for _,poll in polls.iterrows():
            st.markdown(f"**{poll.title}** · {poll.period}")
            opts=poll.options.split(";")
            previous=frame("SELECT option FROM votes WHERE poll_id=? AND username=?",(int(poll.id),user))
            with st.form(f"vote{poll.id}"):
                choice=st.radio("Choose one dish",opts,index=opts.index(previous.iloc[0,0]) if not previous.empty and previous.iloc[0,0] in opts else None)
                do=st.form_submit_button("Cast / update vote")
            if do and choice:
                with db() as c:c.execute("INSERT INTO votes VALUES(?,?,?,?) ON CONFLICT(poll_id,username) DO UPDATE SET option=excluded.option,created=excluded.created",(int(poll.id),user,choice,now()))
                log(user,"voted","poll",int(poll.id),choice);st.success("Vote saved.");st.rerun()
            counts=frame("SELECT option,COUNT(*) AS votes FROM votes WHERE poll_id=? GROUP BY option",(int(poll.id),))
            if not counts.empty: st.bar_chart(counts.set_index("option"))
        st.subheader("Vote on approved dish suggestions")
        dishes=frame("SELECT * FROM dishes WHERE status='Approved' ORDER BY votes DESC")
        for _,d in dishes.iterrows():
            c1,c2=st.columns([4,1]);c1.write(f"**{d['name']}** — {d['description']} · {d['votes']} votes")
            if c2.button("Vote",key=f"dvote{d.id}"):
                with db() as c:
                    exists=c.execute("SELECT 1 FROM feature_votes WHERE request_id=-? AND username=?",(int(d.id),user)).fetchone()
                    # one vote per student/dish using a negative request id in the shared vote table
                    if not exists:
                        c.execute("INSERT INTO feature_votes VALUES(?,?)",(-int(d.id),user));c.execute("UPDATE dishes SET votes=votes+1 WHERE id=?",(int(d.id),))
                st.rerun()
    with tabs[5]:
        with st.form("dishsuggest"):
            dn=st.text_input("Dish name");dd=st.text_area("Why should it be added?")
            submitdish=st.form_submit_button("Suggest dish")
        if submitdish:
            if dn.strip():
                with db() as c:c.execute("INSERT INTO dishes(username,name,description,status,votes,created) VALUES(?,?,?,'Pending',0,?)",(user,dn.strip(),dd.strip(),now()))
                log(user,"suggested","dish",0,dn.strip());st.success("Suggestion sent for admin approval.")
            else:st.error("Enter a dish name.")
        st.subheader("Your dish suggestions")
        st.dataframe(frame("SELECT name,description,status,votes,created FROM dishes WHERE username=? ORDER BY id DESC",(user,)),use_container_width=True,hide_index=True)
    with tabs[6]:
        with st.form("featurereq"):
            title=st.text_input("Feature idea",placeholder="e.g. Add a breakfast rating trend")
            details=st.text_area("How would it help students?")
            sub=st.form_submit_button("Send feature request")
        if sub:
            if title.strip():
                with db() as c:c.execute("INSERT INTO feature_requests(username,title,details,status,created) VALUES(?,?,?,'Submitted',?)",(user,title.strip(),details.strip(),now()))
                st.success("Feature request submitted.")
            else:st.error("Enter a feature idea.")
        reqs=frame("SELECT id,title,details,status,admin_note,created FROM feature_requests WHERE username=? ORDER BY id DESC",(user,))
        st.dataframe(reqs,use_container_width=True,hide_index=True)
else:
    st.subheader("Restricted Admin Portal")
    tabs=st.tabs(["Dashboard","Feedback & complaints","Dish approvals","Polls","Menu editor","Feature requests","Reports & audit"])
    allfb=frame("SELECT * FROM feedback ORDER BY id DESC")
    with tabs[0]:
        a,b,c,d=st.columns(4);a.metric("Total",len(allfb));b.metric("High urgency",int((allfb.urgency=="High").sum()) if len(allfb) else 0);c.metric("Open",int((allfb.status!="Resolved").sum()) if len(allfb) else 0);d.metric("Resolved",int((allfb.status=="Resolved").sum()) if len(allfb) else 0)
        if len(allfb):
            st.subheader("Urgency distribution");st.bar_chart(allfb.groupby("urgency").size())
            st.subheader("Category distribution");st.bar_chart(allfb.groupby("category").size())
            st.subheader("Recent feedback");st.dataframe(allfb[["id","meal","category","sentiment","urgency","status","created"]],use_container_width=True,hide_index=True)
    with tabs[1]:
        if allfb.empty:st.info("No feedback yet.")
        else:
            filt=st.selectbox("Filter urgency",["All","High","Medium","Low"])
            choices=allfb if filt=="All" else allfb[allfb.urgency==filt]
            selected=st.selectbox("Feedback reference",choices.id.tolist(),format_func=lambda i:f"FB-{i:05d} · {choices[choices.id==i].iloc[0].urgency} · {choices[choices.id==i].iloc[0].meal}")
            item=allfb[allfb.id==selected].iloc[0]
            st.write(f"**Original feedback:** {item.comment}")
            st.write(f"AI/local analysis: {item.category} · {item.sentiment} · {item.urgency}")
            if item.safety_flag:st.error("Potential food-safety flag — human review required; not a confirmed incident.")
            with st.form("adminfb"):
                status=st.selectbox("Status",STATUSES,index=STATUSES.index(item.status) if item.status in STATUSES else 0)
                assigned=st.text_input("Assigned staff / department",value=item.assigned or "")
                reply=st.text_area("Reply to student",value=item.reply or "")
                resolution=st.text_area("Resolution note",value=item.resolution or "")
                corrected=st.selectbox("Corrected category",CATEGORIES,index=CATEGORIES.index(item.category) if item.category in CATEGORIES else len(CATEGORIES)-1)
                save=st.form_submit_button("Save review")
            if save:
                with db() as c:c.execute("UPDATE feedback SET status=?,assigned=?,reply=?,resolution=?,category=?,updated=? WHERE id=?",(status,assigned,reply,resolution,corrected,now(),int(selected)))
                log(user,"updated","feedback",int(selected),f"status={status}; category={corrected}");st.success("Saved.");st.rerun()
    with tabs[2]:
        dishes=frame("SELECT * FROM dishes ORDER BY id DESC")
        if dishes.empty:st.info("No dish suggestions.")
        for _,r in dishes.iterrows():
            with st.expander(f"{r['name']} · {r['status']} · {r['votes']} votes"):
                st.write(r.description)
                c1,c2=st.columns(2)
                if c1.button("Approve",key=f"approve{r.id}"):
                    with db() as con:con.execute("UPDATE dishes SET status='Approved' WHERE id=?",(int(r.id),))
                    log(user,"approved","dish",int(r.id));st.rerun()
                if c2.button("Reject",key=f"reject{r.id}"):
                    with db() as con:con.execute("UPDATE dishes SET status='Rejected' WHERE id=?",(int(r.id),))
                    log(user,"rejected","dish",int(r.id));st.rerun()
    with tabs[3]:
        with st.form("newpoll"):
            title=st.text_input("Poll title");period=st.selectbox("Period",["Weekly","Monthly"]);opts=st.text_input("Dish options (separate with semicolons)")
            create=st.form_submit_button("Create poll")
        if create and title.strip() and len([x for x in opts.split(";") if x.strip()])>=2:
            with db() as c:c.execute("INSERT INTO polls(title,period,options,active,created) VALUES(?,?,?,1,?)",(title.strip(),period,";".join(x.strip() for x in opts.split(";") if x.strip()),now()))
            st.success("Poll created.")
        ps=frame("SELECT * FROM polls ORDER BY id DESC")
        for _,r in ps.iterrows():
            st.write(f"**{r.title}** ({r.period}) · {'Active' if r.active else 'Closed'}")
            res=frame("SELECT option,COUNT(*) AS votes FROM votes WHERE poll_id=? GROUP BY option",(int(r.id),))
            if not res.empty:st.dataframe(res,hide_index=True)
            if r.active and st.button("Close poll",key=f"close{r.id}"):
                with db() as c:c.execute("UPDATE polls SET active=0 WHERE id=?",(int(r.id),))
                st.rerun()
    with tabs[4]:
        st.dataframe(frame("SELECT id,week,day,meal,items,published FROM menu ORDER BY id DESC"),use_container_width=True,hide_index=True)
        with st.form("menuadd"):
            week=st.text_input("Week identifier (YYYY-WW)",value=date.today().strftime("%Y-%W"));day=st.selectbox("Day",DAYS);meal=st.selectbox("Meal",["Breakfast","Lunch","Snacks","Dinner"]);items=st.text_input("Menu items");pub=st.checkbox("Publish",True)
            add=st.form_submit_button("Add menu row")
        if add and items.strip():
            with db() as c:c.execute("INSERT INTO menu(week,day,meal,items,published) VALUES(?,?,?,?,?)",(week,day,meal,items.strip(),int(pub)))
            st.success("Menu updated.");st.rerun()
    with tabs[5]:
        reqs=frame("SELECT * FROM feature_requests ORDER BY id DESC")
        if reqs.empty:st.info("No feature requests yet.")
        for _,r in reqs.iterrows():
            with st.expander(f"#{r.id} {r.title} · {r.status}"):
                st.write(r.details or "No details provided.")
                with st.form(f"feature{r.id}"):
                    status=st.selectbox("Request status",["Submitted","Under Review","Approved","Rejected","Planned","Implemented"],index=["Submitted","Under Review","Approved","Rejected","Planned","Implemented"].index(r.status) if r.status in ["Submitted","Under Review","Approved","Rejected","Planned","Implemented"] else 0)
                    note=st.text_area("Admin note",value=r.admin_note or "")
                    save=st.form_submit_button("Update request")
                if save:
                    with db() as c:c.execute("UPDATE feature_requests SET status=?,admin_note=? WHERE id=?",(status,note,int(r.id)))
                    log(user,"updated","feature_request",int(r.id),status);st.rerun()
    with tabs[6]:
        st.subheader("Export reports")
        if st.button("Generate report files"):
            with db() as c:
                all_data=pd.read_sql_query("SELECT * FROM feedback",c)
                urgent=all_data[all_data.urgency=="High"] if len(all_data) else all_data
                all_data.to_csv(ROOT/"results.csv",index=False);urgent.to_csv(ROOT/"urgent.csv",index=False)
                total=len(all_data);negative=int((all_data.sentiment=="Negative").sum()) if total else 0
                cats=all_data.category.value_counts().to_dict() if total else {}
                urgent_lines="\n".join(f"- FB-{int(r.id):05d}: {r.comment}" for _,r in urgent.iterrows())
                (ROOT/"summary.txt").write_text(f"Feedback summary generated {now()}\nTotal records: {total}\nNegative feedback: {negative} ({(negative/total*100 if total else 0):.1f}%)\nCategory counts: {cats}\nUrgent complaints:\n{urgent_lines}\n",encoding="utf-8")
            st.success("Reports generated.")
        for name in ["results.csv","urgent.csv","summary.txt"]:
            path=ROOT/name
            if path.exists():st.download_button("Download "+name,path.read_bytes(),file_name=name)
        st.subheader("Audit history")
        st.dataframe(frame("SELECT actor,action,record_type,record_id,details,created FROM audit ORDER BY id DESC LIMIT 100"),use_container_width=True,hide_index=True)
st.caption("Demo build. Analysis is a screening aid, not a diagnosis. Replace demo accounts with secure institution-approved authentication before deployment.")
