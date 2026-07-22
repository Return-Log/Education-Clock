import os
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base, relationship, Session, sessionmaker
from starlette.websockets import WebSocketState

# -------------------- 数据库配置 --------------------
DB_DIR = os.environ.get("DB_DIR", "/app/data")
os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIR}/school_bulletin.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------- 数据库模型 --------------------
class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    grades = relationship("Grade", back_populates="school")

class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"))
    school = relationship("School", back_populates="grades")
    classes = relationship("Class", back_populates="grade")

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"))
    grade = relationship("Grade", back_populates="classes")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    scopes = relationship("UserScope", back_populates="user")

class UserScope(Base):
    __tablename__ = "user_scopes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    scope_type = Column(String, nullable=False)
    target_school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    target_grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    target_class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    user = relationship("User", back_populates="scopes")

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), unique=True)
    secret_key = Column(String, nullable=False)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------- 数据库 Session 依赖 --------------------
def get_db():
    """每个请求获取一个独立的 Session，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- 密码工具 --------------------
def _truncate_to_72_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]

def make_hash(password: str) -> str:
    pwd_bytes = _truncate_to_72_bytes(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def check_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = _truncate_to_72_bytes(plain_password)
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))

# -------------------- JWT 配置 --------------------
SECRET_KEY = "log"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# -------------------- 初始数据 --------------------
def init_db():
    db = SessionLocal()
    try:
        if db.query(School).count() == 0:
            school_a = School(name="实验第一小学")
            school_b = School(name="希望中学")
            db.add_all([school_a, school_b])
            db.flush()

            g_a1 = Grade(name="一年级", school_id=school_a.id)
            g_a2 = Grade(name="二年级", school_id=school_a.id)
            db.add_all([g_a1, g_a2])
            db.flush()

            c_a1_1 = Class(name="1班", grade_id=g_a1.id)
            c_a1_2 = Class(name="2班", grade_id=g_a1.id)
            c_a2_1 = Class(name="1班", grade_id=g_a2.id)
            c_a2_2 = Class(name="2班", grade_id=g_a2.id)
            db.add_all([c_a1_1, c_a1_2, c_a2_1, c_a2_2])

            g_b1 = Grade(name="一年级", school_id=school_b.id)
            g_b2 = Grade(name="二年级", school_id=school_b.id)
            db.add_all([g_b1, g_b2])
            db.flush()

            c_b1_1 = Class(name="1班", grade_id=g_b1.id)
            c_b1_2 = Class(name="2班", grade_id=g_b1.id)
            c_b2_1 = Class(name="1班", grade_id=g_b2.id)
            c_b2_2 = Class(name="2班", grade_id=g_b2.id)
            db.add_all([c_b1_1, c_b1_2, c_b2_1, c_b2_2])

            devices = [
                Device(class_id=c_a1_1.id, secret_key="schoolA_class1_1_key"),
                Device(class_id=c_a1_2.id, secret_key="schoolA_class1_2_key"),
                Device(class_id=c_a2_1.id, secret_key="schoolA_class2_1_key"),
                Device(class_id=c_a2_2.id, secret_key="schoolA_class2_2_key"),
                Device(class_id=c_b1_1.id, secret_key="schoolB_class1_1_key"),
                Device(class_id=c_b1_2.id, secret_key="schoolB_class1_2_key"),
                Device(class_id=c_b2_1.id, secret_key="schoolB_class2_1_key"),
                Device(class_id=c_b2_2.id, secret_key="schoolB_class2_2_key"),
            ]
            db.add_all(devices)

            u_a1 = User(username="principal_a", hashed_password=make_hash("123456"),
                        display_name="学校A王校长", school_id=school_a.id)
            u_a2 = User(username="grade2_a", hashed_password=make_hash("123456"),
                        display_name="学校A二年级主任", school_id=school_a.id)
            u_a3 = User(username="teacher_a1", hashed_password=make_hash("123456"),
                        display_name="学校A一年1班班主任", school_id=school_a.id)
            u_b1 = User(username="principal_b", hashed_password=make_hash("123456"),
                        display_name="学校B李校长", school_id=school_b.id)
            u_b2 = User(username="teacher_b1", hashed_password=make_hash("123456"),
                        display_name="学校B一年1班班主任", school_id=school_b.id)

            db.add_all([u_a1, u_a2, u_a3, u_b1, u_b2])
            db.flush()

            db.add(UserScope(user_id=u_a1.id, scope_type="school", target_school_id=school_a.id))
            db.add(UserScope(user_id=u_a2.id, scope_type="grade", target_grade_id=g_a2.id))
            db.add(UserScope(user_id=u_a3.id, scope_type="class", target_class_id=c_a1_1.id))
            db.add(UserScope(user_id=u_a3.id, scope_type="class", target_class_id=c_a1_2.id))
            db.add(UserScope(user_id=u_b1.id, scope_type="school", target_school_id=school_b.id))
            db.add(UserScope(user_id=u_b2.id, scope_type="class", target_class_id=c_b1_1.id))

            db.commit()
    finally:
        db.close()

init_db()

# -------------------- 认证函数 --------------------
def verify_password(plain_password, hashed_password):
    return check_password(plain_password, hashed_password)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ✅ 修复：通过 Depends(get_db) 注入 Session，请求期间 Session 保持存活
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# -------------------- Pydantic 模型 --------------------
class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    school_name: Optional[str]
    scopes: List[dict]

class TargetInfo(BaseModel):
    classes: List[dict]
    grades: List[dict]
    school: bool
    school_name: Optional[str]

class AnnouncementIn(BaseModel):
    target_type: str
    target_ids: Optional[List[int]] = None
    content: str

# -------------------- FastAPI 应用 --------------------
app = FastAPI()

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, class_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(class_id, []).append(websocket)

    def disconnect(self, class_id: int, websocket: WebSocket):
        if class_id in self.active_connections:
            self.active_connections[class_id] = [
                ws for ws in self.active_connections[class_id] if ws != websocket
            ]
            if not self.active_connections[class_id]:
                del self.active_connections[class_id]

    async def broadcast_to_class(self, class_id: int, message: str):
        for ws in self.active_connections.get(class_id, []):
            try:
                if ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception:
                pass

    async def broadcast_to_classes(self, class_ids: list[int], message: str):
        for cid in class_ids:
            await self.broadcast_to_class(cid, message)

manager = ConnectionManager()

def get_user_scope_details(db: Session, user: User):
    class_ids = set()
    grade_ids = set()
    is_school_admin = False
    user_school_id = user.school_id
    for scope in user.scopes:
        if scope.scope_type == "school":
            if scope.target_school_id:
                classes = db.query(Class).join(Grade).filter(Grade.school_id == scope.target_school_id).all()
                class_ids.update(c.id for c in classes)
                is_school_admin = True
        elif scope.scope_type == "grade":
            if scope.target_grade_id:
                grade_ids.add(scope.target_grade_id)
                classes = db.query(Class).filter(Class.grade_id == scope.target_grade_id).all()
                class_ids.update(c.id for c in classes)
        elif scope.scope_type == "class":
            if scope.target_class_id:
                class_ids.add(scope.target_class_id)
    return class_ids, grade_ids, is_school_admin, user_school_id

# -------------------- 路由 --------------------

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    template_file = TEMPLATE_DIR / "index.html"
    if not template_file.exists():
        return HTMLResponse(content="<h1>校园公告系统</h1><p>服务运行正常。</p>")
    return templates.TemplateResponse(request=request, name="index.html")

# ✅ 修复：使用 Depends(get_db)
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ✅ 修复：使用 Depends(get_db)，current_user.scopes 可正常懒加载
@app.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scopes_out = []
    for s in current_user.scopes:
        target_name = ""
        if s.scope_type == "school":
            school = db.query(School).filter(School.id == s.target_school_id).first()
            target_name = school.name if school else "未知学校"
        elif s.scope_type == "grade":
            grade = db.query(Grade).filter(Grade.id == s.target_grade_id).first()
            if grade:
                school = db.query(School).filter(School.id == grade.school_id).first()
                target_name = f"{school.name} {grade.name}" if school else grade.name
        elif s.scope_type == "class":
            cls = db.query(Class).filter(Class.id == s.target_class_id).first()
            if cls and cls.grade and cls.grade.school:
                target_name = f"{cls.grade.school.name} {cls.grade.name} {cls.name}"
            elif cls:
                target_name = cls.name
        scopes_out.append({
            "type": s.scope_type,
            "target_id": s.target_school_id or s.target_grade_id or s.target_class_id,
            "target_name": target_name,
        })

    school_name = ""
    if current_user.school_id:
        school = db.query(School).filter(School.id == current_user.school_id).first()
        school_name = school.name if school else ""

    return UserOut(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        school_name=school_name,
        scopes=scopes_out,
    )

# ✅ 修复：使用 Depends(get_db)
@app.get("/targets", response_model=TargetInfo)
async def get_available_targets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    class_ids, grade_ids, is_school, user_school_id = get_user_scope_details(db, current_user)

    classes_out = []
    for cid in class_ids:
        c = db.query(Class).filter(Class.id == cid).first()
        if c:
            classes_out.append({
                "id": c.id,
                "name": c.name,
                "grade": c.grade.name if c.grade else "",
                "school": c.grade.school.name if c.grade and c.grade.school else ""
            })

    grades_out = []
    for gid in grade_ids:
        g = db.query(Grade).filter(Grade.id == gid).first()
        if g:
            grades_out.append({
                "id": g.id,
                "name": g.name,
                "school": g.school.name if g.school else ""
            })

    school_name = ""
    if is_school and user_school_id:
        school = db.query(School).filter(School.id == user_school_id).first()
        school_name = school.name if school else ""

    return TargetInfo(classes=classes_out, grades=grades_out, school=is_school, school_name=school_name)

# ✅ 修复：使用 Depends(get_db)
@app.post("/announcements")
async def send_announcement(
    ann: AnnouncementIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    class_ids, grade_ids, is_school, user_school_id = get_user_scope_details(db, current_user)
    target_class_ids = []

    if ann.target_type == "school":
        if not is_school:
            raise HTTPException(status_code=403, detail="没有全校发送权限")
        all_classes = db.query(Class).join(Grade).filter(Grade.school_id == current_user.school_id).all()
        target_class_ids = [c.id for c in all_classes]

    elif ann.target_type == "grade":
        if not ann.target_ids:
            raise HTTPException(status_code=400, detail="缺少年级ID")
        for gid in ann.target_ids:
            if gid not in grade_ids and not is_school:
                raise HTTPException(status_code=403, detail=f"没有年级ID {gid} 的发送权限")
        classes = db.query(Class).filter(Class.grade_id.in_(ann.target_ids)).all()
        target_class_ids = [c.id for c in classes]

    elif ann.target_type == "classes":
        if not ann.target_ids:
            raise HTTPException(status_code=400, detail="缺少班级ID")
        for cid in ann.target_ids:
            if cid not in class_ids:
                raise HTTPException(status_code=403, detail=f"没有班级ID {cid} 的发送权限")
        target_class_ids = ann.target_ids

    else:
        raise HTTPException(status_code=400, detail="target_type 必须为 classes, grade 或 school")

    new_ann = Announcement(content=ann.content, school_id=current_user.school_id)
    db.add(new_ann)
    db.commit()

    message = json.dumps({
        "type": "announcement",
        "content": ann.content,
        "timestamp": datetime.utcnow().isoformat()
    })
    await manager.broadcast_to_classes(target_class_ids, message)

    return {"status": "ok", "sent_to_class_ids": target_class_ids}

# WebSocket 端点（不能使用 Depends，手动管理 Session）
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, class_id: int, token: str):
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.class_id == class_id, Device.secret_key == token).first()
    finally:
        db.close()

    if not device:
        await websocket.close(code=4001, reason="设备认证失败")
        return

    await manager.connect(class_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(class_id, websocket)
    except Exception:
        manager.disconnect(class_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)