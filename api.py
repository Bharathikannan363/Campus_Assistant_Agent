"""FastAPI web API specified by the campus assistant contract."""
import base64, hashlib, hmac, json, os, secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from database import create_database, get_connection
from agent import ask_agent_for_college
from scraper import scrape_college

app = FastAPI(title="AI Campus Assistant")
create_database()
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")

@app.get("/health")
def health():
    return {"status": "ok"}

def _b64(v): return base64.urlsafe_b64encode(v).rstrip(b"=").decode()
def _password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210000).hex()
def _valid(password, stored):
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(_password(password, salt).split("$", 1)[1], digest)
def _jwt(payload):
    head = _b64(b'{"alg":"HS256","typ":"JWT"}'); body = _b64(json.dumps(payload).encode())
    sig = _b64(hmac.new(JWT_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"
def _user(token):
    try:
        head, body, sig = token.split(".")
        if not hmac.compare_digest(sig, _b64(hmac.new(JWT_SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())): raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if data["exp"] < datetime.now(timezone.utc).timestamp(): raise ValueError()
        return data
    except Exception: raise HTTPException(401, "Invalid or expired token")
def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "Bearer token required")
    return _user(authorization[7:])
def admin_user(user=Depends(current_user)):
    if user.get("role") != "admin": raise HTTPException(403, "Admin role required")
    return user

class AuthIn(BaseModel): email: str; password: str = Field(min_length=8); name: str = "Student"; college_id: int | None = None
class ChatIn(BaseModel): college_id: int; message: str; conversation_id: int | None = None

@app.post("/api/auth/register")
def register(data: AuthIn):
    db=get_connection()
    try:
        cur=db.execute("INSERT INTO users(email,name,password_hash,college_id) VALUES(?,?,?,?)",(data.email.lower(),data.name,_password(data.password),data.college_id)); db.commit()
    except Exception: db.close(); raise HTTPException(409,"Email already registered")
    uid=cur.lastrowid; db.close(); return {"access_token":_jwt({"sub":uid,"email":data.email.lower(),"role":"student","exp":(datetime.now(timezone.utc)+timedelta(days=7)).timestamp()}),"token_type":"bearer"}
@app.post("/api/auth/login")
def login(data: AuthIn):
    db=get_connection(); row=db.execute("SELECT * FROM users WHERE email=?",(data.email.lower(),)).fetchone(); db.close()
    if not row or not _valid(data.password,row["password_hash"]): raise HTTPException(401,"Invalid credentials")
    return {"access_token":_jwt({"sub":row["id"],"email":row["email"],"role":row["role"],"exp":(datetime.now(timezone.utc)+timedelta(days=7)).timestamp()}),"token_type":"bearer"}
@app.get("/api/auth/me")
def me(user=Depends(current_user)): return user

def _list(table, college_id=None):
    db=get_connection(); q=f"SELECT * FROM {table}"; args=()
    if college_id is not None: q+=" WHERE college_id=?"; args=(college_id,)
    rows=[dict(x) for x in db.execute(q,args).fetchall()]; db.close(); return rows
@app.get("/api/colleges")
def colleges(): return _list("colleges")
@app.get("/api/colleges/{college_id}")
def college(college_id:int):
    rows=_list("colleges",college_id)
    if not rows: raise HTTPException(404,"College not found")
    return rows[0]
@app.post("/api/chat")
def chat(data:ChatIn, user=Depends(current_user)):
    db=get_connection(); cid=data.conversation_id
    if cid is None:
        cid=db.execute("INSERT INTO conversations(user_id,college_id,title) VALUES(?,?,?)",(user["sub"],data.college_id,data.message[:80])).lastrowid
    db.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",(cid,"user",data.message)); db.commit()
    result=ask_agent_for_college(data.message,data.college_id)
    db.execute("INSERT INTO messages(conversation_id,role,content,tool_name) VALUES(?,?,?,?)",(cid,"assistant",result["answer"],result.get("tool_used"))); db.commit(); db.close()
    return {**result,"conversation_id":cid,"college_id":data.college_id}
@app.get("/api/conversations")
def conversations(user=Depends(current_user)): return _list_user("conversations",user["sub"])
def _list_user(table,uid):
    db=get_connection(); rows=[dict(x) for x in db.execute(f"SELECT * FROM {table} WHERE user_id=?",(uid,)).fetchall()]; db.close(); return rows
@app.get("/api/conversations/{conversation_id}")
def conversation(conversation_id:int,user=Depends(current_user)):
    db=get_connection(); row=db.execute("SELECT * FROM conversations WHERE id=? AND user_id=?",(conversation_id,user["sub"])).fetchone(); db.close()
    if not row: raise HTTPException(404,"Conversation not found")
    return dict(row)
@app.get("/api/conversations/{conversation_id}/messages")
def messages(conversation_id:int,user=Depends(current_user)):
    conversation(conversation_id,user); db=get_connection(); rows=[dict(x) for x in db.execute("SELECT * FROM messages WHERE conversation_id=?",(conversation_id,)).fetchall()]; db.close(); return rows

for path, table in (("/api/timetable","timetables"),("/api/hostel","hostels"),("/api/announcements","announcements"),("/api/events","events"),("/api/courses","courses"),("/api/calendar","academic_calendar")):
    app.get(path)(lambda table=table, college_id=None: _list(table,college_id))
@app.get("/api/hostel/details")
def hostel_details(college_id:int=None): return _list("hostels",college_id)
@app.get("/api/map")
def map_data(college_id:int=None): return _list("college_maps",college_id)
@app.get("/api/map/location")
def map_location(college_id:int, location_name:str|None=None): return _list("map_locations",college_id)
@app.get("/api/map/route")
def map_route(college_id:int, source_location:str, destination_location:str): return {"college_id":college_id,"from":source_location,"to":destination_location,"steps":[]}

@app.post("/api/admin/colleges")
def add_college(data:dict,user=Depends(admin_user)):
    db=get_connection(); cur=db.execute("INSERT INTO colleges(name,short_name,district,state,website_url) VALUES(?,?,?,?,?)",tuple(data.get(k) for k in ("name","short_name","district","state","website_url"))); db.commit(); db.close(); return {"id":cur.lastrowid}
@app.put("/api/admin/colleges/{id}")
def update_college(id:int,data:dict,user=Depends(admin_user)):
    fields={k:v for k,v in data.items() if k in ("name","short_name","district","state","website_url","is_active")}
    if not fields: return {"updated":False}
    db=get_connection(); db.execute(f"UPDATE colleges SET {','.join(k+'=?' for k in fields)} WHERE id=?",(*fields.values(),id)); db.commit(); db.close(); return {"updated":True}
@app.delete("/api/admin/colleges/{id}")
def delete_college(id:int,user=Depends(admin_user)):
    db=get_connection(); db.execute("UPDATE colleges SET is_active=0 WHERE id=?",(id,)); db.commit(); db.close(); return {"deactivated":True}
@app.post("/api/admin/scrape/{college_id}")
def scrape(college_id:int,user=Depends(admin_user)):
    db=get_connection(); row=db.execute("SELECT short_name FROM colleges WHERE id=?",(college_id,)).fetchone(); db.close()
    if not row: raise HTTPException(404,"College not found")
    return scrape_college(college_id,row["short_name"])
@app.post("/api/admin/scrape-all")
def scrape_all(user=Depends(admin_user)):
    return [scrape_college(r["id"],r["short_name"]) for r in _list("colleges")]
@app.get("/api/admin/scraping-status")
def scraping_status(user=Depends(admin_user)): return _list("colleges")

# The lightweight frontend is intentionally served by the same origin so
# browser clients need no secret or cross-origin configuration.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
