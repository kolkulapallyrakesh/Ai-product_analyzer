import os
import io
import json
import base64
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from groq import Groq
from dotenv import load_dotenv
import bcrypt
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
import jwt
load_dotenv()
app = FastAPI(title="Enterprise AI Product Analyzer Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("CRITICAL ERROR: GROQ_API_KEY environment variable is missing!")
groq_client = Groq(api_key=GROQ_API_KEY)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_temporary_development_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
DATABASE_URL = "sqlite:///./ingredients_vault.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    analyses = relationship("ProductAnalysisModel", back_populates="owner", cascade="all, delete-orphan")

class ProductAnalysisModel(Base):
    __tablename__ = "product_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, index=True)
    health_score = Column(Integer)
    detected_ingredients = Column(Text)  
    red_flags = Column(Text)              
    healthy_alternatives = Column(Text)   
    summary = Column(Text)
    color = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("UserModel", back_populates="analyses")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session signature expired or invalid validation token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        raise credentials_exception
    return user
class UserRegistrationSchema(BaseModel):
    username: str
    password: str

class TokenSchema(BaseModel):
    access_token: str
    token_type: str

class AnalysisResultSchema(BaseModel):
    health_score: int
    detected_ingredients: List[str]
    red_flags: List[str]
    healthy_alternatives: List[str]
    summary: str
    color: str

    class Config:
        from_attributes = True

@app.post("/register", response_model=TokenSchema, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegistrationSchema, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Profile credentials already exist.")
    
    secured_password = hash_password(user_data.password)
    new_user = UserModel(username=user_data.username, hashed_password=secured_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=TokenSchema)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect configuration parameters provided.")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/analyze", response_model=AnalysisResultSchema)
async def analyze_packet(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        file_bytes = await file.read()
        base64_image = base64.b64encode(file_bytes).decode("utf-8")
        image_data_url = f"data:{file.content_type};base64,{base64_image}"

        prompt = """
        Look at this image of a product packaging. Read the ingredient list, analyze it, 
        and provide the output in a strict structured JSON format matching these fields:
        - health_score: An integer from 1 to 10 evaluating how healthy it is.
        - detected_ingredients: A clean, parsed list of the individual ingredients found.
        - red_flags: List any ultra-processed chemicals, excessive sugars, hidden artificial additives, or allergens.
        - summary: A 2-3 sentence overview explaining why it received its health score.
        - healthy_alternatives: A parsed list of 2-3 healthier component swaps or completely clean, direct product changes instead.
        - color: color value like 'green' if between 7-10, 'yellow' if 4-6, and 'red' if 1-3.

        Respond ONLY with a valid JSON object. Do not include markdown codeblocks.
        """

        response = groq_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    ]
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        evaluation_payload = json.loads(raw_content)

        db_record = ProductAnalysisModel(
            user_id=current_user.id,
            filename=file.filename,
            health_score=int(evaluation_payload.get("health_score", 5)),
            detected_ingredients=json.dumps(evaluation_payload.get("detected_ingredients", [])),
            red_flags=json.dumps(evaluation_payload.get("red_flags", [])),
            healthy_alternatives=json.dumps(evaluation_payload.get("healthy_alternatives", [])),
            summary=evaluation_payload.get("summary", ""),
            color=evaluation_payload.get("color", "yellow")
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return evaluation_payload

    except Exception as e:
        print(f"!!! CRASH LOG TRACEBACK: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Diagnostic failure error: {str(e)}")
@app.get("/history")
def get_history(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    records = db.query(ProductAnalysisModel).filter(ProductAnalysisModel.user_id == current_user.id).order_by(ProductAnalysisModel.created_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "health_score": r.health_score,
            "detected_ingredients": json.loads(r.detected_ingredients),
            "red_flags": json.loads(r.red_flags),
            "healthy_alternatives": json.loads(r.healthy_alternatives if r.healthy_alternatives else "[]"),
            "summary": r.summary,
            "color": r.color,
            "timestamp": r.created_at.isoformat()
        } for r in records
    ]
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)