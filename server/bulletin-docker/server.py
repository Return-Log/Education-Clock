import os
import json
import logging
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

logger = logging.getLogger("school-bulletin")

# -------------------- 数据库配置 --------------------
DB_DIR = os.environ.get("DB_DIR", "/app/data")
DATA_FILE = os.environ.get("DATA_FILE", "/app/data/init_data.json")
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
    grades = relationship("Grade", back_populates="school", cascade="all, delete-orphan")

class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"))
    school = relationship("School", back_populates="grades")
    classes = relationship("Class", back_populates="grade", cascade="all, delete-orphan")

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
    scopes = relationship("UserScope", back_populates="user", cascade="all, delete-orphan")

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
SECRET_KEY = os.environ.get("SECRET_KEY", "log")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# -------------------- 从 JSON 文件加载初始数据 --------------------
def resolve_class_id(db: Session, school_name: str, grade_name: str, class_name: str) -> Optional[int]:
    """根据 学校/年级/班级 名称查找 class_id"""
    cls = (
        db.query(Class)
        .join(Grade, Class.grade_id == Grade.id)
        .join(School, Grade.school_id == School.id)
        .filter(School.name == school_name, Grade.name == grade_name, Class.name == class_name)
        .first()
    )
    return cls.id if cls else None

def resolve_grade_id(db: Session, school_name: str, grade_name: str) -> Optional[int]:
    grade = (
        db.query(Grade)
        .join(School, Grade.school_id == School.id)
        .filter(School.name == school_name, Grade.name == grade_name)
        .first()
    )
    return grade.id if grade else None

def resolve_school_id(db: Session, school_name: str) -> Optional[int]:
    school = db.query(School).filter(School.name == school_name).first()
    return school.id if school else None

# -------------------- 默认初始数据（JSON 不存在时自动写入） --------------------
DEFAULT_INIT_DATA = {
    "schools": [
        {
            "name": "实验第一小学",
            "grades": [
                {"name": "一年级", "classes": ["1班", "2班"]},
                {"name": "二年级", "classes": ["1班", "2班"]}
            ]
        },
        {
            "name": "希望中学",
            "grades": [
                {"name": "一年级", "classes": ["1班", "2班"]},
                {"name": "二年级", "classes": ["1班", "2班"]}
            ]
        }
    ],
    "users": [
        {
            "username": "principal_a",
            "password": "123456",
            "display_name": "学校A王校长",
            "school": "实验第一小学",
            "scopes": [{"type": "school", "target": "实验第一小学"}]
        },
        {
            "username": "grade2_a",
            "password": "123456",
            "display_name": "学校A二年级主任",
            "school": "实验第一小学",
            "scopes": [{"type": "grade", "target": "实验第一小学/二年级"}]
        },
        {
            "username": "teacher_a1",
            "password": "123456",
            "display_name": "学校A一年1班班主任",
            "school": "实验第一小学",
            "scopes": [
                {"type": "class", "target": "实验第一小学/一年级/1班"},
                {"type": "class", "target": "实验第一小学/一年级/2班"}
            ]
        },
        {
            "username": "principal_b",
            "password": "123456",
            "display_name": "学校B李校长",
            "school": "希望中学",
            "scopes": [{"type": "school", "target": "希望中学"}]
        },
        {
            "username": "teacher_b1",
            "password": "123456",
            "display_name": "学校B一年1班班主任",
            "school": "希望中学",
            "scopes": [{"type": "class", "target": "希望中学/一年级/1班"}]
        }
    ],
    "devices": [
        {"school": "实验第一小学", "grade": "一年级", "class": "1班", "secret_key": "schoolA_class1_1_key"},
        {"school": "实验第一小学", "grade": "一年级", "class": "2班", "secret_key": "schoolA_class1_2_key"},
        {"school": "实验第一小学", "grade": "二年级", "class": "1班", "secret_key": "schoolA_class2_1_key"},
        {"school": "实验第一小学", "grade": "二年级", "class": "2班", "secret_key": "schoolA_class2_2_key"},
        {"school": "希望中学", "grade": "一年级", "class": "1班", "secret_key": "schoolB_class1_1_key"},
        {"school": "希望中学", "grade": "一年级", "class": "2班", "secret_key": "schoolB_class1_2_key"},
        {"school": "希望中学", "grade": "二年级", "class": "1班", "secret_key": "schoolB_class2_1_key"},
        {"school": "希望中学", "grade": "二年级", "class": "2班", "secret_key": "schoolB_class2_2_key"}
    ]
}


def ensure_init_data_file():
    """如果 init_data.json 不存在，自动生成默认文件"""
    data_file = Path(DATA_FILE)
    if not data_file.exists():
        logger.info(f"未检测到 {DATA_FILE}，自动生成默认配置...")
        data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_INIT_DATA, f, ensure_ascii=False, indent=2)
        logger.info(f"已生成默认配置: {DATA_FILE}")


def load_init_data():
    """从外部 JSON 文件加载初始数据（仅当数据库为空时）"""
    # 先确保文件存在
    ensure_init_data_file()

    db = SessionLocal()
    try:
        if db.query(School).count() > 0:
            logger.info("数据库已有数据，跳过初始化")
            return

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"从 {DATA_FILE} 加载初始数据...")

        # 1. 创建学校 / 年级 / 班级
        for school_data in data.get("schools", []):
            school = School(name=school_data["name"])
            db.add(school)
            db.flush()
            for grade_data in school_data.get("grades", []):
                grade = Grade(name=grade_data["name"], school_id=school.id)
                db.add(grade)
                db.flush()
                for class_name in grade_data.get("classes", []):
                    db.add(Class(name=class_name, grade_id=grade.id))
        db.flush()

        # 2. 创建设备
        for dev in data.get("devices", []):
            cid = resolve_class_id(db, dev["school"], dev["grade"], dev["class"])
            if cid:
                db.add(Device(class_id=cid, secret_key=dev["secret_key"]))
            else:
                logger.warning(f"设备找不到班级: {dev}")

        # 3. 创建用户 + 权限
        for user_data in data.get("users", []):
            school_id = resolve_school_id(db, user_data.get("school", ""))
            user = User(
                username=user_data["username"],
                hashed_password=make_hash(user_data["password"]),
                display_name=user_data["display_name"],
                school_id=school_id,
            )
            db.add(user)
            db.flush()

            for scope in user_data.get("scopes", []):
                scope_type = scope["type"]
                parts = scope["target"].split("/")
                if scope_type == "school" and len(parts) >= 1:
                    sid = resolve_school_id(db, parts[0])
                    db.add(UserScope(user_id=user.id, scope_type="school", target_school_id=sid))
                elif scope_type == "grade" and len(parts) >= 2:
                    gid = resolve_grade_id(db, parts[0], parts[1])
                    db.add(UserScope(user_id=user.id, scope_type="grade", target_grade_id=gid))
                elif scope_type == "class" and len(parts) >= 3:
                    cid = resolve_class_id(db, parts[0], parts[1], parts[2])
                    db.add(UserScope(user_id=user.id, scope_type="class", target_class_id=cid))

        db.commit()
        logger.info("初始数据加载完成")

    except Exception as e:
        db.rollback()
        logger.error(f"加载初始数据失败: {e}")
        raise
    finally:
        db.close()

load_init_data()

# -------------------- 认证函数 --------------------
def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not check_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

# ---- 管理 API 模型 ----
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    school: Optional[str] = None
    scopes: Optional[List[dict]] = None

class UserUpdate(BaseModel):
    password: Optional[str] = None
    display_name: Optional[str] = None
    school: Optional[str] = None
    scopes: Optional[List[dict]] = None

class DeviceCreate(BaseModel):
    school: str
    grade: str
    class_name: str
    secret_key: str

class DeviceUpdate(BaseModel):
    secret_key: Optional[str] = None

class ReloadResponse(BaseModel):
    status: str
    message: str

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

# -------------------- 公共路由 --------------------

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    template_file = TEMPLATE_DIR / "index.html"
    if not template_file.exists():
        return HTMLResponse(content="<h1>校园公告系统</h1><p>服务运行正常。</p>")
    return templates.TemplateResponse(request=request, name="index.html")

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

# -------------------- 管理 API（动态增删改） --------------------

@app.get("/admin/users", summary="列出所有用户")
async def admin_list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    result = []
    for u in users:
        school_name = ""
        if u.school_id:
            s = db.query(School).filter(School.id == u.school_id).first()
            school_name = s.name if s else ""
        scopes_out = []
        for sc in u.scopes:
            scopes_out.append({
                "type": sc.scope_type,
                "school_id": sc.target_school_id,
                "grade_id": sc.target_grade_id,
                "class_id": sc.target_class_id,
            })
        result.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "school": school_name,
            "scopes": scopes_out,
        })
    return result

@app.post("/admin/users", summary="创建用户")
async def admin_create_user(
    body: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail=f"用户名 {body.username} 已存在")

    school_id = None
    if body.school:
        school_id = resolve_school_id(db, body.school)
        if not school_id:
            raise HTTPException(status_code=404, detail=f"学校 {body.school} 不存在")

    user = User(
        username=body.username,
        hashed_password=make_hash(body.password),
        display_name=body.display_name,
        school_id=school_id,
    )
    db.add(user)
    db.flush()

    if body.scopes:
        for scope in body.scopes:
            scope_type = scope.get("type")
            target = scope.get("target", "")
            parts = target.split("/")
            if scope_type == "school" and len(parts) >= 1:
                sid = resolve_school_id(db, parts[0])
                db.add(UserScope(user_id=user.id, scope_type="school", target_school_id=sid))
            elif scope_type == "grade" and len(parts) >= 2:
                gid = resolve_grade_id(db, parts[0], parts[1])
                db.add(UserScope(user_id=user.id, scope_type="grade", target_grade_id=gid))
            elif scope_type == "class" and len(parts) >= 3:
                cid = resolve_class_id(db, parts[0], parts[1], parts[2])
                db.add(UserScope(user_id=user.id, scope_type="class", target_class_id=cid))

    db.commit()
    return {"status": "ok", "user_id": user.id, "username": user.username}

@app.put("/admin/users/{user_id}", summary="更新用户")
async def admin_update_user(
    user_id: int,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.password:
        user.hashed_password = make_hash(body.password)
    if body.display_name:
        user.display_name = body.display_name
    if body.school:
        sid = resolve_school_id(db, body.school)
        if not sid:
            raise HTTPException(status_code=404, detail=f"学校 {body.school} 不存在")
        user.school_id = sid

    if body.scopes is not None:
        # 清除旧权限，写入新权限
        db.query(UserScope).filter(UserScope.user_id == user_id).delete()
        for scope in body.scopes:
            scope_type = scope.get("type")
            target = scope.get("target", "")
            parts = target.split("/")
            if scope_type == "school" and len(parts) >= 1:
                sid = resolve_school_id(db, parts[0])
                db.add(UserScope(user_id=user.id, scope_type="school", target_school_id=sid))
            elif scope_type == "grade" and len(parts) >= 2:
                gid = resolve_grade_id(db, parts[0], parts[1])
                db.add(UserScope(user_id=user.id, scope_type="grade", target_grade_id=gid))
            elif scope_type == "class" and len(parts) >= 3:
                cid = resolve_class_id(db, parts[0], parts[1], parts[2])
                db.add(UserScope(user_id=user.id, scope_type="class", target_class_id=cid))

    db.commit()
    return {"status": "ok", "user_id": user.id}

@app.delete("/admin/users/{user_id}", summary="删除用户")
async def admin_delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"status": "ok", "deleted": user.username}

@app.get("/admin/devices", summary="列出所有设备")
async def admin_list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    devices = db.query(Device).all()
    result = []
    for d in devices:
        cls = db.query(Class).filter(Class.id == d.class_id).first()
        info = {"id": d.id, "class_id": d.class_id, "secret_key": d.secret_key}
        if cls and cls.grade and cls.grade.school:
            info["school"] = cls.grade.school.name
            info["grade"] = cls.grade.name
            info["class"] = cls.name
        result.append(info)
    return result

@app.post("/admin/devices", summary="创建设备")
async def admin_create_device(
    body: DeviceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cid = resolve_class_id(db, body.school, body.grade, body.class_name)
    if not cid:
        raise HTTPException(status_code=404, detail="找不到对应班级")
    existing = db.query(Device).filter(Device.class_id == cid).first()
    if existing:
        raise HTTPException(status_code=400, detail="该班级已有设备")
    device = Device(class_id=cid, secret_key=body.secret_key)
    db.add(device)
    db.commit()
    return {"status": "ok", "device_id": device.id}

@app.put("/admin/devices/{device_id}", summary="更新设备密钥")
async def admin_update_device(
    device_id: int,
    body: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if body.secret_key:
        device.secret_key = body.secret_key
    db.commit()
    return {"status": "ok", "device_id": device.id}

@app.delete("/admin/devices/{device_id}", summary="删除设备")
async def admin_delete_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    db.delete(device)
    db.commit()
    return {"status": "ok", "deleted_device_id": device_id}

@app.post("/admin/reload", response_model=ReloadResponse, summary="重新加载 init_data.json（增量同步）")
async def admin_reload_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重新读取 init_data.json，增量同步：
    - 新的学校/年级/班级/设备/用户会被创建
    - 已存在的不会重复创建
    - 不会删除已有数据
    """
    data_file = Path(DATA_FILE)
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {DATA_FILE}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    created = {"schools": 0, "grades": 0, "classes": 0, "devices": 0, "users": 0}

    # 同步学校/年级/班级
    for school_data in data.get("schools", []):
        school = db.query(School).filter(School.name == school_data["name"]).first()
        if not school:
            school = School(name=school_data["name"])
            db.add(school)
            db.flush()
            created["schools"] += 1

        for grade_data in school_data.get("grades", []):
            grade = db.query(Grade).filter(
                Grade.name == grade_data["name"], Grade.school_id == school.id
            ).first()
            if not grade:
                grade = Grade(name=grade_data["name"], school_id=school.id)
                db.add(grade)
                db.flush()
                created["grades"] += 1

            for class_name in grade_data.get("classes", []):
                cls = db.query(Class).filter(
                    Class.name == class_name, Class.grade_id == grade.id
                ).first()
                if not cls:
                    db.add(Class(name=class_name, grade_id=grade.id))
                    created["classes"] += 1

    db.flush()

    # 同步设备
    for dev in data.get("devices", []):
        cid = resolve_class_id(db, dev["school"], dev["grade"], dev["class"])
        if cid:
            existing = db.query(Device).filter(Device.class_id == cid).first()
            if not existing:
                db.add(Device(class_id=cid, secret_key=dev["secret_key"]))
                created["devices"] += 1

    # 同步用户
    for user_data in data.get("users", []):
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if existing:
            continue
        school_id = resolve_school_id(db, user_data.get("school", ""))
        user = User(
            username=user_data["username"],
            hashed_password=make_hash(user_data["password"]),
            display_name=user_data["display_name"],
            school_id=school_id,
        )
        db.add(user)
        db.flush()
        created["users"] += 1

        for scope in user_data.get("scopes", []):
            scope_type = scope["type"]
            parts = scope["target"].split("/")
            if scope_type == "school" and len(parts) >= 1:
                sid = resolve_school_id(db, parts[0])
                db.add(UserScope(user_id=user.id, scope_type="school", target_school_id=sid))
            elif scope_type == "grade" and len(parts) >= 2:
                gid = resolve_grade_id(db, parts[0], parts[1])
                db.add(UserScope(user_id=user.id, scope_type="grade", target_grade_id=gid))
            elif scope_type == "class" and len(parts) >= 3:
                cid = resolve_class_id(db, parts[0], parts[1], parts[2])
                db.add(UserScope(user_id=user.id, scope_type="class", target_class_id=cid))

    db.commit()
    return ReloadResponse(
        status="ok",
        message=f"增量同步完成: {json.dumps(created, ensure_ascii=False)}"
    )

# -------------------- WebSocket --------------------

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