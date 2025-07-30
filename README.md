# Interview Platform API - Architectural Document

## Table of Contents
1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Core Features](#4-core-features)
5. [Database Design](#5-database-design)
6. [API Documentation](#6-api-documentation)
7. [Deployment & Environment Setup](#7-deployment--environment-setup)
8. [Infrastructure](#8-infrastructure)
9. [Security](#9-security)
10. [Monitoring & Logging](#10-monitoring--logging)
11. [Error Handling & Troubleshooting](#11-error-handling--troubleshooting)

---

## 1. Introduction

### Product Name & Overview
**Interview Platform API v7.0 Enhanced** - A comprehensive AI-powered interview management system that enables companies to conduct, evaluate, and manage technical and behavioral interviews with multi-language support and advanced AI capabilities.

### Purpose of This Document
This document provides a comprehensive overview of the Interview Platform API's architecture, design patterns, and technical implementation. It serves as a guide for developers, system administrators, and stakeholders to understand the system's structure and functionality.

### Intended Audience
- Backend developers working on the platform
- DevOps engineers managing deployment
- System administrators
- Technical leads and architects
- QA engineers

### Scope of Backend Services
The platform provides:
- Multi-tenant interview management system
- AI-powered question generation and evaluation
- Resume analysis and matching
- Real-time interview scheduling and tracking
- Multilingual support (12+ languages)
- Advanced evaluation scoring with coding assessment
- Audio processing and text-to-speech capabilities

---

## 2. System Architecture

### High-Level Architecture Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   External AI   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │◄──►│   Business      │◄──►│   Background    │
│   Database      │    │   Logic Layer   │    │   Tasks/Queue   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Storage  │◄──►│   OCR/Document  │◄──►│   Email Service │
│   (Documents)   │    │   Processing    │    │   (SMTP)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

#### API Gateway / REST Layer
- **FastAPI Framework**: High-performance async web framework
- **CORS Middleware**: Cross-origin request handling
- **Authentication Middleware**: JWT-based token validation
- **Exception Handlers**: Centralized error handling
- **Request/Response Processing**: Data validation and serialization

#### Business Logic Layer
- **Interview Management Service**: Core interview operations
- **AI Service**: Question generation and answer evaluation
- **Resume Matching Service**: Document analysis and skill matching
- **Email Service**: Notification and communication
- **OCR Service**: Document text extraction
- **Scheduler Service**: Background task management

#### Database Layer
- **PostgreSQL 14**: Primary data storage
- **Connection Pooling**: Efficient database connections
- **Transaction Management**: ACID compliance
- **Schema Versioning**: Database migration support

#### External Integrations
- **Google Gemini AI**: Question generation and evaluation
- **Deepgram**: Text-to-speech processing
- **SMTP Servers**: Email delivery

### Data Flow Between Components

1. **Authentication Flow**:
   ```
   Client → API Gateway → Auth Service → JWT Token → Client
   ```

2. **Interview Scheduling Flow**:
   ```
   Client → API Gateway → Interview Service → Database → Email Service
   ```

3. **AI Evaluation Flow**:
   ```
   Interview Data → AI Service → External AI API → Evaluation Results → Database
   ```

---

## 3. Tech Stack

### Programming Language & Framework
- **Python 3.9+**: Core programming language
- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server for production
- **Pydantic**: Data validation and serialization

```python
# main.py - FastAPI Application Setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Interview Platform API v7.0 Enhanced",
    description="Enhanced Interview Platform with AI-Powered Features",
    version="7.0.0-enhanced"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.environ.get("LOCAL_FRONTEND_URL", "http://localhost:3000"),
        os.environ.get("PROD_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.routers import auth, interview, evaluation
app.include_router(auth.router)
app.include_router(interview.router)
app.include_router(evaluation.router)
```

### Database & ORM
- **PostgreSQL 14**: Primary database
- **psycopg2**: PostgreSQL adapter
- **Custom SQL**: Direct database operations
- **Connection pooling**: Database efficiency

```python
# app/database/config.py - Database Configuration
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import os

class DatabaseConfig:
    def __init__(self):
        self.connection_url = os.getenv("DATABASE_URL")
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=self.connection_url
            )
        except Exception as e:
            logger.error(f"Database pool initialization failed: {e}")
    
    def get_cursor(self, cursor_factory=None):
        """Get database cursor with connection"""
        conn = self.pool.getconn()
        cursor = conn.cursor(cursor_factory=cursor_factory)
        return cursor, conn
    
    def return_connection(self, conn):
        """Return connection to pool"""
        self.pool.putconn(conn)

# Usage example
def get_database_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))
```

### Authentication Mechanism
- **JWT (JSON Web Tokens)**: Stateless authentication
- **HS256 Algorithm**: Token signing
- **Role-based Access Control**: Multi-level permissions
- **Token Expiration**: 30-minute default

```python
# app/utils/auth.py - Authentication Implementation
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(security)):
    """Verify and decode JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("type")
        
        if user_id is None:
            raise credentials_exception
            
        return {
            "user_id": user_id,
            "type": user_type,
            "company_id": payload.get("company_id"),
            "department_id": payload.get("department_id")
        }
    except JWTError:
        raise credentials_exception

def check_user_permissions(required_role: str = None):
    """Check user role-based permissions"""
    def permission_checker(current_user: dict = Depends(verify_token)):
        user_type = current_user.get("type")
        
        if required_role == "super_admin" and user_type != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required"
            )
        
        return current_user
    
    return permission_checker
```

### External Service Clients
- **Google Gemini API**: AI model integration
- **Deepgram API**: Audio processing
- **SMTP Clients**: Email delivery
- **CrewAI**: Multi-agent AI workflows

```python
# app/services/ai_service.py - AI Service Integration
import os
from crewai import Agent, Task, Crew, LLM
import google.generativeai as genai

class AIService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.ai_available = bool(self.gemini_api_key)
        
        if self.ai_available:
            genai.configure(api_key=self.gemini_api_key)
    
    async def generate_questions(self, domain: str, difficulty: str, count: int = 5):
        """Generate interview questions using AI"""
        if not self.ai_available:
            return self._get_fallback_questions(domain, difficulty, count)
        
        try:
            # Create AI agent for question generation
            question_agent = Agent(
                role='Technical Interview Question Generator',
                goal=f'Generate {count} high-quality {difficulty} level questions for {domain}',
                backstory="Expert interviewer with deep knowledge of technical concepts",
                llm=LLM(
                    model="gemini/gemini-2.0-flash",
                    api_key=self.gemini_api_key
                )
            )
            
            task = Task(
                description=f"""
                Generate {count} interview questions for {domain} at {difficulty} difficulty.
                Format as JSON array with question, expected_answer, and keywords.
                """,
                agent=question_agent
            )
            
            crew = Crew(agents=[question_agent], tasks=[task])
            result = crew.kickoff()
            
            return self._parse_ai_response(result)
            
        except Exception as e:
            logger.error(f"AI question generation failed: {e}")
            return self._get_fallback_questions(domain, difficulty, count)
```

---

## 4. Core Features

### Authentication & Authorization
- **User Roles**:
  - Super Admin: Full system access
  - Company User: Company-level access
  - Department User: Department-specific access
- **Token-based Access**: JWT implementation
- **Permission Validation**: Role-based resource access

### User Data Management
- **Multi-tenant Architecture**: Company and department isolation
- **Profile Management**: User information and preferences
- **Interview History**: Complete tracking and analytics
- **Role-based Data Access**: Secure data segregation

### AI Request Pipeline
1. **Input Processing**: User data validation and formatting
2. **AI API Communication**: Structured requests to external services
3. **Response Processing**: Result parsing and standardization
4. **Database Storage**: Persistent result storage
5. **Client Response**: Formatted response delivery

### Interview Management System
- **Scheduling**: Automated interview scheduling
- **Question Generation**: AI-powered question creation
- **Answer Evaluation**: Comprehensive scoring system
- **Resume Analysis**: Document processing and matching
- **Multilingual Support**: 12+ language support

---

## 5. Database Design

### Complete Schema Implementation

```python
# app/database/schema.py - Database Schema Creation
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logger = logging.getLogger(__name__)

class DatabaseSchema:
    def __init__(self, db_config):
        self.db_config = db_config
    
    def create_complete_schema(self):
        """Create complete database schema with all tables"""
        logger.info("Creating database schema...")
        
        # Create extensions and enums
        self.create_extensions()
        self.create_enums()
        
        # Create core tables
        self.create_user_tables()
        self.create_business_tables()
        self.create_module_system_tables()
        self.create_multilingual_tables()
        
        # Create constraints and indexes
        self.create_foreign_keys()
        self.create_indexes()
        
        logger.info("Database schema created successfully")
    
    def create_extensions(self):
        """Create PostgreSQL extensions"""
        with self.db_config.get_cursor() as (cursor, conn):
            extensions = [
                "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
                "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"
            ]
            
            for ext in extensions:
                try:
                    cursor.execute(ext)
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Extension creation failed: {e}")
    
    def create_enums(self):
        """Create custom enum types"""
        with self.db_config.get_cursor() as (cursor, conn):
            enums = [
                """
                DO $$ BEGIN
                    CREATE TYPE entity_status AS ENUM ('Active', 'Inactive');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """,
                """
                DO $$ BEGIN
                    CREATE TYPE interview_status AS ENUM ('pending', 'scheduled', 'in_progress', 'completed', 'cancelled');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            ]
            
            for enum_sql in enums:
                cursor.execute(enum_sql)
            conn.commit()
    
    def create_user_tables(self):
        """Create user management tables"""
        with self.db_config.get_cursor() as (cursor, conn):
            tables = [
                # Super Admin table
                """
                CREATE TABLE IF NOT EXISTS super_admin (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status entity_status DEFAULT 'Active'
                );
                """,
                
                # Companies table
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id SERIAL PRIMARY KEY,
                    company_name VARCHAR(255) NOT NULL,
                    company_email VARCHAR(100),
                    company_phone VARCHAR(20),
                    company_address TEXT,
                    status entity_status DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT NOT NULL,
                    updated_by INT
                );
                """,
                
                # Company Users table
                """
                CREATE TABLE IF NOT EXISTS company_users (
                    user_id SERIAL PRIMARY KEY,
                    company_id INT NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    phone VARCHAR(20),
                    role VARCHAR(50) DEFAULT 'company_user',
                    status entity_status DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_by INT
                );
                """,
                
                # Departments table
                """
                CREATE TABLE IF NOT EXISTS departments (
                    department_id SERIAL PRIMARY KEY,
                    company_id INT NOT NULL,
                    department_name VARCHAR(255) NOT NULL,
                    department_description TEXT,
                    status entity_status DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT NOT NULL,
                    updated_by INT,
                    UNIQUE (company_id, department_name)
                );
                """,
                
                # Department Users table
                """
                CREATE TABLE IF NOT EXISTS department_users (
                    user_id SERIAL PRIMARY KEY,
                    company_id INT NOT NULL,
                    department_id INT NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    phone VARCHAR(20),
                    role VARCHAR(50) DEFAULT 'department_user',
                    status entity_status DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_by INT
                );
                """
            ]
            
            for table_sql in tables:
                cursor.execute(table_sql)
            conn.commit()
    
    def create_business_tables(self):
        """Create business logic tables"""
        with self.db_config.get_cursor() as (cursor, conn):
            tables = [
                # Job Descriptions table
                """
                CREATE TABLE IF NOT EXISTS jd_details (
                    job_id BIGSERIAL PRIMARY KEY,
                    company_id INT NOT NULL,
                    department_id INT NOT NULL,
                    jd_title VARCHAR(255) NOT NULL,
                    jd_questions JSONB,
                    jd_file BYTEA,
                    jd_filename VARCHAR(255),
                    status entity_status DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT NOT NULL,
                    updated_by INT
                );
                """,
                
                # Main Interview table
                """
                CREATE TABLE IF NOT EXISTS interview_details_main (
                    unique_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INT NOT NULL,
                    department_id INT NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    age INT,
                    sex VARCHAR(10),
                    phone VARCHAR(20),
                    email_id VARCHAR(100),
                    resume BYTEA,
                    job_id BIGINT,
                    user_image TEXT,
                    interview_questions JSONB,
                    interview_answers JSONB,
                    domain VARCHAR(100),
                    text_file BYTEA,
                    evaluation_result JSONB,
                    coding_evaluation JSONB,
                    status interview_status DEFAULT 'pending',
                    scheduled_at TIMESTAMP,
                    evaluated_at TIMESTAMP,
                    language_preference VARCHAR(10) DEFAULT 'en' NOT NULL,
                    mode VARCHAR(20) DEFAULT 'STATIC' NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_by INT
                );
                """,
                
                # User Statistics table
                """
                CREATE TABLE IF NOT EXISTS users_stats (
                    id SERIAL PRIMARY KEY,
                    interview_id UUID,
                    company_id INT NOT NULL,
                    file_data BYTEA,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INT,
                    updated_by INT
                );
                """
            ]
            
            for table_sql in tables:
                cursor.execute(table_sql)
            conn.commit()

# Usage
def initialize_database():
    """Initialize complete database schema"""
    from app.database.config import DatabaseConfig
    
    db_config = DatabaseConfig()
    schema = DatabaseSchema(db_config)
    schema.create_complete_schema()
```

### Entity Relationship Overview

```python
# app/models/business.py - Database Models
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class CompanyModel(BaseModel):
    company_id: Optional[int] = None
    company_name: str
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    status: str = "Active"
    created_at: Optional[datetime] = None
    created_by: int

class InterviewModel(BaseModel):
    unique_id: Optional[UUID] = None
    company_id: int
    department_id: int
    full_name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    email_id: Optional[EmailStr] = None
    job_id: Optional[int] = None
    domain: Optional[str] = None
    interview_questions: Optional[Dict[str, Any]] = None
    interview_answers: Optional[Dict[str, Any]] = None
    evaluation_result: Optional[Dict[str, Any]] = None
    status: str = "pending"
    language_preference: str = "en"
    mode: str = "STATIC"
    scheduled_at: Optional[datetime] = None
```

### Key Relationships
- Companies have multiple departments
- Departments have multiple users
- Interviews belong to departments
- Job descriptions link to interviews
- Evaluation results reference interviews

### Data Storage Policy
- **Persistent Data**: User profiles, interview records, evaluations
- **Temporary Data**: File uploads, processing queues
- **Cache Data**: Generated content, translations (TTL-based)
- **Binary Data**: Resumes, documents (BYTEA fields)

---

## 6. API Documentation

### Authentication Flow

```python
# app/routers/auth.py - Authentication Router
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.utils.auth import create_access_token, verify_password
from app.database.config import get_database_connection

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    status: int
    message: str
    result: dict

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user and return JWT token
    
    Args:
        credentials: User email and password
        
    Returns:
        JWT token with user information
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Check in different user tables based on role
        user_queries = [
            ("super_admin", "SELECT id, password_hash, 'super_admin' as type FROM super_admin WHERE email = %s"),
            ("company_user", "SELECT id, password_hash, 'company_user' as type, company_id FROM company_users WHERE email = %s"),
            ("department_user", "SELECT id, password_hash, 'department_user' as type, company_id, department_id FROM department_users WHERE email = %s")
        ]
        
        user_data = None
        for user_type, query in user_queries:
            cursor.execute(query, (credentials.email,))
            result = cursor.fetchone()
            if result:
                user_data = result
                break
        
        if not user_data or not verify_password(credentials.password, user_data[1]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create token payload
        token_data = {
            "sub": str(user_data[0]),
            "type": user_data[2],
            "email": credentials.email
        }
        
        # Add company/department info if applicable
        if len(user_data) > 3:
            token_data["company_id"] = user_data[3]
        if len(user_data) > 4:
            token_data["department_id"] = user_data[4]
        
        access_token = create_access_token(token_data)
        
        return {
            "status": 200,
            "message": "Login successful",
            "result": {
                "access_token": access_token,
                "token_type": "bearer",
                "user_type": user_data[2],
                "user_id": user_data[0]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()
```

**API Usage Example:**
```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "secure_password"
}

HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": 200,
  "message": "Login successful",
  "result": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user_type": "company_user",
    "user_id": 123
  }
}
```

### Core API Endpoints

#### Interview Management

```python
# app/routers/interview.py - Interview Router
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional, List
import uuid
import json

router = APIRouter(prefix="/interview", tags=["Interview Management"])

@router.post("/schedule")
async def schedule_interview(
    full_name: str = Form(...),
    age: int = Form(...),
    sex: str = Form(...),
    phone: str = Form(...),
    email_id: str = Form(...),
    job_id: int = Form(...),
    domain: str = Form(...),
    language_preference: str = Form("en"),
    mode: str = Form("STATIC"),
    resume: UploadFile = File(...),
    user_image: Optional[str] = Form(None),
    current_user: dict = Depends(verify_token)
):
    """
    Schedule a new interview with resume upload
    
    Args:
        Interview details and resume file
        
    Returns:
        Interview unique ID and scheduling confirmation
    """
    try:
        # Generate unique interview ID
        unique_id = str(uuid.uuid4())
        
        # Read resume file
        resume_content = await resume.read()
        
        # Validate file size and type
        if len(resume_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="Resume file too large")
        
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Insert interview record
        insert_query = """
        INSERT INTO interview_details_main (
            unique_id, company_id, department_id, full_name, age, sex, 
            phone, email_id, resume, job_id, user_image, domain,
            language_preference, mode, status, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            unique_id, current_user.get("company_id"), current_user.get("department_id"),
            full_name, age, sex, phone, email_id, resume_content, job_id,
            user_image, domain, language_preference, mode, 'scheduled', current_user.get("user_id")
        ))
        
        conn.commit()
        
        return {
            "status": 200,
            "message": "Interview scheduled successfully",
            "result": {
                "unique_id": unique_id,
                "interview_status": "scheduled"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/{unique_id}")
async def get_interview(
    unique_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Get interview details by unique ID
    
    Args:
        unique_id: Interview identifier
        
    Returns:
        Complete interview information
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get interview with permission check
        query = """
        SELECT unique_id, company_id, department_id, full_name, age, sex,
               phone, email_id, job_id, domain, interview_questions,
               interview_answers, evaluation_result, status, scheduled_at,
               language_preference, mode, created_at
        FROM interview_details_main 
        WHERE unique_id = %s
        """
        
        cursor.execute(query, (unique_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Format response
        interview_data = {
            "unique_id": str(result[0]),
            "company_id": result[1],
            "department_id": result[2],
            "full_name": result[3],
            "age": result[4],
            "sex": result[5],
            "phone": result[6],
            "email_id": result[7],
            "job_id": result[8],
            "domain": result[9],
            "interview_questions": result[10],
            "interview_answers": result[11],
            "evaluation_result": result[12],
            "status": result[13],
            "scheduled_at": result[14].isoformat() if result[14] else None,
            "language_preference": result[15],
            "mode": result[16],
            "created_at": result[17].isoformat() if result[17] else None
        }
        
        return {
            "status": 200,
            "message": "Interview retrieved successfully",
            "result": interview_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()
```

### Response Format
All API responses follow this structure:
```json
{
  "status": 200,
  "message": "Operation successful",
  "result": "data_payload_here"
}
```

### Status Codes
- **200**: Success
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **422**: Validation Error
- **500**: Internal Server Error

---

## 7. Deployment & Environment Setup

### EC2 Production Deployment

#### Server Requirements
- **Instance Type**: t3.medium or larger (2 vCPU, 4GB RAM minimum)
- **Operating System**: Ubuntu 20.04 LTS or Amazon Linux 2
- **Storage**: 20GB+ SSD storage
- **Security Groups**: HTTP (80), HTTPS (443), SSH (22), Custom (8000)

#### Initial Server Setup

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.9+ and pip
sudo apt install python3.9 python3.9-venv python3-pip -y

# 3. Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# 4. Install Nginx for reverse proxy
sudo apt install nginx -y

# 5. Install supervisor for process management
sudo apt install supervisor -y

# 6. Install system dependencies
sudo apt install build-essential libpq-dev -y
```

#### Application Deployment Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

# Configuration
APP_USER="interview_app"
APP_DIR="/opt/interview-platform"
REPO_URL="https://github.com/your-repo/interview-platform.git"
PYTHON_VERSION="3.9"

echo "🚀 Starting Interview Platform deployment..."

# Create application user
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash $APP_USER
    echo "✅ Created application user: $APP_USER"
fi

# Create application directory
sudo mkdir -p $APP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR

# Switch to application user
sudo -u $APP_USER bash << EOF
cd $APP_DIR

# Clone or update repository
if [ -d ".git" ]; then
    echo "📥 Updating existing repository..."
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone $REPO_URL .
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python$PYTHON_VERSION -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs documents/uploads documents/vector_db

echo "✅ Application setup completed"
EOF

echo "🔧 Setting up system services..."
```

#### Environment Configuration

```bash
# /opt/interview-platform/.env - Production Environment File
# Copy from .env.example and configure

# Database Configuration (PostgreSQL on same server)
DATABASE_URL=postgresql://interview_user:your_secure_password@localhost:5432/interview_platform_prod
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=interview_platform_prod
DATABASE_USER=interview_user
DATABASE_PASSWORD=your_secure_password

# Google AI Configuration
GEMINI_API_KEY=your_actual_gemini_api_key

# Deepgram Configuration  
DEEPGRAM_API_KEY=your_actual_deepgram_api_key

# Email Service Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
USE_TLS=true
SENDER_EMAIL=noreply@yourcompany.com
SENDER_PASSWORD=your_app_password

# Application Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security Settings
SECRET_KEY=your_super_secure_secret_key_minimum_32_characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Production URLs
LOCAL_FRONTEND_URL=http://localhost:3000
PROD_URL=https://yourdomain.com

# Performance Settings
USE_MOCK_AI=false
ENABLE_MULTILINGUAL=true
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,es,fr,de,pt,hi,zh,ja,ko,ar,ru,it

# File Storage
UPLOAD_DIR=/opt/interview-platform/documents
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=pdf,doc,docx,txt

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/interview-platform/logs/app.log
ENABLE_FILE_LOGGING=true
```

#### Database Setup Script

```bash
#!/bin/bash
# setup_database.sh - PostgreSQL setup for production

echo "🗄️  Setting up PostgreSQL database..."

# Create database user and database
sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'interview_user') THEN
        CREATE ROLE interview_user LOGIN PASSWORD 'your_secure_password';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE interview_platform_prod OWNER interview_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'interview_platform_prod')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE interview_platform_prod TO interview_user;
GRANT USAGE ON SCHEMA public TO interview_user;
GRANT CREATE ON SCHEMA public TO interview_user;

\q
EOF

echo "✅ PostgreSQL setup completed"

# Initialize database schema
echo "🏗️  Initializing database schema..."
cd /opt/interview-platform
sudo -u interview_app bash << EOF
source venv/bin/activate
python -c "
from app.database.schema import initialize_database
initialize_database()
print('✅ Database schema initialized')
"
EOF
```

#### Supervisor Configuration

```bash
# /etc/supervisor/conf.d/interview-platform.conf
[program:interview-platform]
command=/opt/interview-platform/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/opt/interview-platform
user=interview_app
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/interview-platform/logs/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="/opt/interview-platform/venv/bin"

[program:interview-platform-scheduler]
command=/opt/interview-platform/venv/bin/python -m app.services.background_scheduler
directory=/opt/interview-platform
user=interview_app
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/interview-platform/logs/scheduler.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/opt/interview-platform/venv/bin"
```

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/interview-platform
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # File upload size limit
    client_max_body_size 15M;
    
    # API proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static files (if any)
    location /static/ {
        alias /opt/interview-platform/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Document uploads (secured)
    location /documents/ {
        internal;
        alias /opt/interview-platform/documents/;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # Rate limiting
    location /auth/ {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Rate limiting configuration
http {
    limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

#### SSL Certificate Setup with Let's Encrypt

```bash
#!/bin/bash
# setup_ssl.sh - SSL certificate setup

echo "🔒 Setting up SSL certificate with Let's Encrypt..."

# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain SSL certificate
sudo certbot certonly --standalone \
    --email admin@your-domain.com \
    --agree-tos \
    --no-eff-email \
    -d your-domain.com \
    -d www.your-domain.com

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/interview-platform /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Setup automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

echo "✅ SSL certificate setup completed"
```

#### Complete Deployment Script

```bash
#!/bin/bash
# complete_deploy.sh - Full production deployment

set -e

echo "🚀 Starting complete Interview Platform deployment on EC2..."

# Variables
DOMAIN="your-domain.com"
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

echo "📋 Deployment Configuration:"
echo "Domain: $DOMAIN"
echo "Database Password: [Generated Securely]"
echo "Secret Key: [Generated Securely]"
echo ""

# Run setup scripts
./deploy.sh
./setup_database.sh

# Configure environment
sudo -u interview_app bash << EOF
cd /opt/interview-platform
cat > .env << EOL
DATABASE_URL=postgresql://interview_user:$DB_PASSWORD@localhost:5432/interview_platform_prod
SECRET_KEY=$SECRET_KEY
# ... other configuration from template
EOL
EOF

# Setup SSL if domain is configured
if [ "$DOMAIN" != "your-domain.com" ]; then
    sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/interview-platform
    ./setup_ssl.sh
fi

# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start interview-platform
sudo supervisorctl start interview-platform-scheduler

# Enable services
sudo systemctl enable supervisor
sudo systemctl enable nginx
sudo systemctl enable postgresql

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access your application at: https://$DOMAIN"
echo "📊 Health check: https://$DOMAIN/health"
echo "📝 API docs: https://$DOMAIN/docs"
echo ""
echo "🔐 Important: Save these credentials securely:"
echo "Database Password: $DB_PASSWORD"
echo "Secret Key: $SECRET_KEY"
```

### Local Development Setup

```bash
# local_setup.sh - Development environment setup

#!/bin/bash
echo "🛠️  Setting up local development environment..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Setup local database (PostgreSQL)
createdb interview_platform_dev

# Copy environment file
cp .env.example .env

# Initialize database
python -c "
from app.database.schema import initialize_database
initialize_database()
print('✅ Local database initialized')
"

# Start development server
echo "🚀 Starting development server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000

echo "✅ Development environment ready!"
echo "🌐 Access at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
```

### Environment Variables Reference

```bash
# Production Environment Variables Checklist

# Required for basic functionality
✅ DATABASE_URL
✅ SECRET_KEY
✅ GEMINI_API_KEY (for AI features)
✅ SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD (for emails)

# Optional but recommended
✅ DEEPGRAM_API_KEY (for TTS features)
✅ PROD_URL (for CORS)
✅ LOG_LEVEL (INFO for production)

# Security settings
✅ DEBUG=false (never true in production)
✅ USE_MOCK_AI=false
✅ ENABLE_FILE_LOGGING=true

# Performance settings
✅ ACCESS_TOKEN_EXPIRE_MINUTES=30
✅ MAX_FILE_SIZE=10485760
✅ UPLOAD_DIR=/opt/interview-platform/documents
```

### Troubleshooting Common Deployment Issues

#### Issue 1: Database Connection Failed
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Check database exists
sudo -u postgres psql -l | grep interview_platform

# Test connection
psql "postgresql://interview_user:password@localhost:5432/interview_platform_prod"
```

#### Issue 2: Nginx Configuration Error
```bash
# Test nginx configuration
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Reload nginx configuration
sudo systemctl reload nginx
```

#### Issue 3: Application Won't Start
```bash
# Check supervisor status
sudo supervisorctl status

# Check application logs
tail -f /opt/interview-platform/logs/supervisor.log

# Manual start for debugging
cd /opt/interview-platform
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Issue 4: SSL Certificate Problems
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --dry-run

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -text -noout | grep "Not After"
```

### Performance Tuning for Production

#### Application Settings
```python
# Uvicorn production settings
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload
```

#### PostgreSQL Optimization
```sql
-- /etc/postgresql/*/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### System Limits
```bash
# /etc/security/limits.conf
interview_app soft nofile 65536
interview_app hard nofile 65536
interview_app soft nproc 4096
interview_app hard nproc 4096
```

# This would be run on the standby server
cat > setup_standby.sh << 'EOF'
#!/bin/bash
# Stop PostgreSQL on standby
sudo systemctl stop postgresql

# Remove existing data directory
sudo rm -rf /var/lib/postgresql/*/main

# Create base backup from primary
sudo -u postgres pg_basebackup -h primary-server-ip -D /var/lib/postgresql/*/main -U replicator -v -P -W

# Create recovery configuration
sudo -u postgres tee /var/lib/postgresql/*/main/standby.signal << EOL
# This file indicates that this server should start as a standby
EOL

sudo -u postgres tee /var/lib/postgresql/*/main/postgresql.auto.conf << EOL
primary_conninfo = 'host=primary-server-ip port=5432 user=replicator password=replication_password application_name=standby1'
promote_trigger_file = '/tmp/promote_to_primary'
EOL

# Start PostgreSQL on standby
sudo systemctl start postgresql
sudo systemctl enable postgresql
EOF

echo "✅ High Availability setup completed"
```

#### Load Balancer Health Checks

```bash
#!/bin/bash
# health_check_setup.sh - Configure comprehensive health checks

echo "🔍 Setting up health check monitoring..."

# 1. Application health check endpoint
cat > /opt/interview-platform/health_check.py << 'EOF'
#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

def check_application_health():
    """Comprehensive application health check"""
    health_results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "overall_status": "healthy"
    }
    
    try:
        # Check API endpoint
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            health_results["checks"]["api"] = {"status": "healthy", "response_time": response.elapsed.total_seconds()}
        else:
            health_results["checks"]["api"] = {"status": "unhealthy", "status_code": response.status_code}
            health_results["overall_status"] = "unhealthy"
    except Exception as e:
        health_results["checks"]["api"] = {"status": "unhealthy", "error": str(e)}
        health_results["overall_status"] = "unhealthy"
    
    # Check database connectivity
    try:
        import psycopg2
        conn = psycopg2.connect("postgresql://interview_user:password@localhost:5432/interview_platform_prod")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        health_results["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_results["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_results["overall_status"] = "unhealthy"
    
    # Check disk space
    import shutil
    disk_usage = shutil.disk_usage("/")
    free_space_percent = (disk_usage.free / disk_usage.total) * 100
    
    if free_space_percent > 10:
        health_results["checks"]["disk_space"] = {"status": "healthy", "free_percent": free_space_percent}
    else:
        health_results["checks"]["disk_space"] = {"status": "unhealthy", "free_percent": free_space_percent}
        health_results["overall_status"] = "unhealthy"
    
    print(json.dumps(health_results, indent=2))
    
    # Exit with error code if unhealthy
    if health_results["overall_status"] != "healthy":
        sys.exit(1)

if __name__ == "__main__":
    check_application_health()
EOF

chmod +x /opt/interview-platform/health_check.py

# 2. Setup cron job for regular health checks
echo "⏰ Setting up scheduled health checks..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/interview-platform/health_check.py >> /var/log/health_check.log 2>&1") | crontab -

# 3. Create alerting script
cat > /opt/interview-platform/alert_on_failure.sh << 'EOF'
#!/bin/bash
# alert_on_failure.sh - Send alerts when health checks fail

HEALTH_CHECK_LOG="/var/log/health_check.log"
LAST_CHECK_FILE="/tmp/last_health_check_status"
ALERT_EMAIL="admin@yourcompany.com"

# Run health check
/opt/interview-platform/health_check.py > /tmp/current_health_status 2>&1
CURRENT_STATUS=$?

# Read previous status
if [ -f "$LAST_CHECK_FILE" ]; then
    PREVIOUS_STATUS=$(cat "$LAST_CHECK_FILE")
else
    PREVIOUS_STATUS=0
fi

# If status changed from healthy to unhealthy, send alert
if [ $CURRENT_STATUS -ne 0 ] && [ $PREVIOUS_STATUS -eq 0 ]; then
    echo "ALERT: Interview Platform health check failed at $(date)" | \
    mail -s "Interview Platform Health Alert" "$ALERT_EMAIL"
    
    # Log the failure
    echo "$(date): Health check failed" >> "$HEALTH_CHECK_LOG"
    cat /tmp/current_health_status >> "$HEALTH_CHECK_LOG"
fi

# If status changed from unhealthy to healthy, send recovery notice
if [ $CURRENT_STATUS -eq 0 ] && [ $PREVIOUS_STATUS -ne 0 ]; then
    echo "RECOVERY: Interview Platform health check recovered at $(date)" | \
    mail -s "Interview Platform Recovery Notice" "$ALERT_EMAIL"
    
    echo "$(date): Health check recovered" >> "$HEALTH_CHECK_LOG"
fi

# Save current status
echo $CURRENT_STATUS > "$LAST_CHECK_FILE"
EOF

chmod +x /opt/interview-platform/alert_on_failure.sh

echo "✅ Health check monitoring setup completed"
```

### Infrastructure as Code

#### Terraform Configuration

```hcl
# infrastructure.tf - Terraform configuration for Interview Platform

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "key_pair_name" {
  description = "EC2 Key Pair name"
  type        = string
}

# VPC Configuration
resource "aws_vpc" "interview_platform_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "interview-platform-vpc"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "interview_platform_igw" {
  vpc_id = aws_vpc.interview_platform_vpc.id

  tags = {
    Name        = "interview-platform-igw"
    Environment = var.environment
  }
}

# Public Subnets
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.interview_platform_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "interview-platform-public-1"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.interview_platform_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name        = "interview-platform-public-2"
    Environment = var.environment
  }
}

# Private Subnets
resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.interview_platform_vpc.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name        = "interview-platform-private-1"
    Environment = var.environment
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.interview_platform_vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name        = "interview-platform-private-2"
    Environment = var.environment
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.interview_platform_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.interview_platform_igw.id
  }

  tags = {
    Name        = "interview-platform-public-rt"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public_rta_1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_rta_2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_rt.id
}

# Security Groups
resource "aws_security_group" "application_sg" {
  name_prefix = "interview-platform-app-"
  vpc_id      = aws_vpc.interview_platform_vpc.id

  # HTTP from ALB
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # HTTPS from ALB
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # Application port from ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict this in production
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "interview-platform-app-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "alb_sg" {
  name_prefix = "interview-platform-alb-"
  vpc_id      = aws_vpc.interview_platform_vpc.id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "interview-platform-alb-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "database_sg" {
  name_prefix = "interview-platform-db-"
  vpc_id      = aws_vpc.interview_platform_vpc.id

  # PostgreSQL from application
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application_sg.id]
  }

  tags = {
    Name        = "interview-platform-db-sg"
    Environment = var.environment
  }
}

# Application Load Balancer
resource "aws_lb" "interview_platform_alb" {
  name               = "interview-platform-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]

  enable_deletion_protection = false

  tags = {
    Name        = "interview-platform-alb"
    Environment = var.environment
  }
}

# Target Group
resource "aws_lb_target_group" "interview_platform_tg" {
  name     = "interview-platform-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.interview_platform_vpc.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "8000"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "interview-platform-tg"
    Environment = var.environment
  }
}

# ALB Listener
resource "aws_lb_listener" "interview_platform_listener" {
  load_balancer_arn = aws_lb.interview_platform_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.interview_platform_tg.arn
  }
}

# Launch Template
resource "aws_launch_template" "interview_platform_lt" {
  name_prefix   = "interview-platform-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = "t3.large"
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.application_sg.id]

  user_data = base64encode(templatefile("${path.module}/userdata.sh", {
    region = var.aws_region
  }))

  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = 20
      volume_type = "gp3"
      encrypted   = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "interview-platform-instance"
      Environment = var.environment
    }
  }

  tags = {
    Name        = "interview-platform-lt"
    Environment = var.environment
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "interview_platform_asg" {
  name                = "interview-platform-asg"
  vpc_zone_identifier = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  target_group_arns   = [aws_lb_target_group.interview_platform_tg.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = 1
  max_size         = 5
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.interview_platform_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "interview-platform-asg"
    propagate_at_launch = false
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "interview_platform_db_subnet_group" {
  name       = "interview-platform-db-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]

  tags = {
    Name        = "interview-platform-db-subnet-group"
    Environment = var.environment
  }
}

# RDS Instance
resource "aws_db_instance" "interview_platform_db" {
  identifier = "interview-platform-db"

  engine         = "postgres"
  engine_version = "14.9"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "interview_platform_prod"
  username = "interview_user"
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.database_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.interview_platform_db_subnet_group.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Sun:04:00-Sun:05:00"

  multi_az               = true
  publicly_accessible    = false
  deletion_protection    = true

  tags = {
    Name        = "interview-platform-db"
    Environment = var.environment
  }
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# S3 Bucket for backups
resource "aws_s3_bucket" "interview_platform_backups" {
  bucket = "interview-platform-backups-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "interview-platform-backups"
    Environment = var.environment
  }
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket_versioning" "interview_platform_backups_versioning" {
  bucket = aws_s3_bucket.interview_platform_backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "interview_platform_backups_encryption" {
  bucket = aws_s3_bucket.interview_platform_backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Outputs
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.interview_platform_alb.dns_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.interview_platform_db.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name for backups"
  value       = aws_s3_bucket.interview_platform_backups.id
}
```

#### User Data Script for EC2 Instances

```bash
# userdata.sh - EC2 instance initialization script
#!/bin/bash

# Variables
REGION="${region}"
APP_DIR="/opt/interview-platform"
APP_USER="interview_app"

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting Interview Platform instance initialization..."

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3.9 python3.9-venv python3-pip postgresql-client nginx supervisor git awscli

# Create application user
useradd -m -s /bin/bash $APP_USER

# Create application directory
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Get application code from S3 or Git (example with Git)
sudo -u $APP_USER git clone https://github.com/your-repo/interview-platform.git $APP_DIR

# Setup Python environment
cd $APP_DIR
sudo -u $APP_USER python3.9 -m venv venv
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Create necessary directories
sudo -u $APP_USER mkdir -p logs documents/uploads documents/vector_db

# Get environment variables from AWS Systems Manager Parameter Store
aws ssm get-parameter --region $REGION --name "/interview-platform/env" --with-decryption --query Parameter.Value --output text > $APP_DIR/.env
chown $APP_USER:$APP_USER $APP_DIR/.env
chmod 600 $APP_DIR/.env

# Setup Supervisor configuration
cat > /etc/supervisor/conf.d/interview-platform.conf << EOF
[program:interview-platform]
command=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
directory=$APP_DIR
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$APP_DIR/logs/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="$APP_DIR/venv/bin"
EOF

# Setup Nginx configuration
cat > /etc/nginx/sites-available/interview-platform << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/interview-platform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Start services
systemctl enable nginx supervisor
systemctl start nginx supervisor

# Initialize application
cd $APP_DIR
sudo -u $APP_USER bash -c "source venv/bin/activate && python -c 'from app.database.schema import initialize_database; initialize_database()'"

# Start application
supervisorctl reread
supervisorctl update
supervisorctl start interview-platform

echo "Interview Platform instance initialization completed successfully"
```

### Infrastructure Monitoring and Alerting

#### CloudWatch Custom Metrics

```python
# app/utils/cloudwatch_metrics.py - Custom CloudWatch metrics
import boto3
import time
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CloudWatchMetrics:
    """Send custom metrics to CloudWatch"""
    
    def __init__(self, region_name='us-west-2'):
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region_name)
            self.namespace = 'InterviewPlatform/Application'
        except Exception as e:
            logger.warning(f"CloudWatch client initialization failed: {e}")
            self.cloudwatch = None
    
    def put_metric(self, metric_name: str, value: float, unit: str = 'Count', dimensions: Dict[str, str] = None):
        """Send a custom metric to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
        except Exception as e:
            logger.error(f"Failed to send metric {metric_name}: {e}")
    
    def put_business_metrics(self, metrics: Dict[str, Any]):
        """Send business metrics to CloudWatch"""
        try:
            # Interview completion rate
            if 'interviews_completed' in metrics and 'interviews_started' in metrics:
                completion_rate = (metrics['interviews_completed'] / metrics['interviews_started']) * 100
                self.put_metric('InterviewCompletionRate', completion_rate, 'Percent')
            
            # Average evaluation score
            if 'average_evaluation_score' in metrics:
                self.put_metric('AverageEvaluationScore', metrics['average_evaluation_score'], 'None')
            
            # AI service response time
            if 'ai_response_time' in metrics:
                self.put_metric('AIServiceResponseTime', metrics['ai_response_time'], 'Seconds')
            
            # Active user sessions
            if 'active_sessions' in metrics:
                self.put_metric('ActiveUserSessions', metrics['active_sessions'], 'Count')
                
        except Exception as e:
            logger.error(f"Failed to send business metrics: {e}")

# Global CloudWatch metrics instance
cloudwatch_metrics = CloudWatchMetrics()

# Usage in application
def track_interview_completion(interview_id: str, score: float):
    """Track interview completion metrics"""
    cloudwatch_metrics.put_metric('InterviewCompleted', 1, 'Count', 
                                 dimensions={'InterviewId': interview_id})
    cloudwatch_metrics.put_metric('InterviewScore', score, 'None',
                                 dimensions={'InterviewId': interview_id})
```

#### Automated Scaling Policies

```bash
#!/bin/bash
# scaling_policies.sh - Setup Auto Scaling policies

echo "⚙️  Setting up Auto Scaling policies..."

ASG_NAME="interview-platform-asg"
REGION="us-west-2"

# 1. Create scale-up policy
aws autoscaling put-scaling-policy \
    --region $REGION \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name "interview-platform-scale-up" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalLowerBound=0,MetricIntervalUpperBound=10,ScalingAdjustment=1 \
                       MetricIntervalLowerBound=10,ScalingAdjustment=2

# 2. Create scale-down policy
aws autoscaling put-scaling-policy \
    --region $REGION \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name "interview-platform-scale-down" \
    --policy-type "StepScaling" \
    --adjustment-type "ChangeInCapacity" \
    --step-adjustments MetricIntervalUpperBound=0,ScalingAdjustment=-1

# 3. Create CloudWatch alarms for CPU utilization
aws cloudwatch put-metric-alarm \
    --region $REGION \
    --alarm-name "interview-platform-cpu-high" \
    --alarm-description "Scale up when CPU > 70%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions "arn:aws:autoscaling:$REGION:account-id:scalingPolicy:policy-id:autoScalingGroupName/$ASG_NAME:policyName/interview-platform-scale-up"

aws cloudwatch put-metric-alarm \
    --region $REGION \
    --alarm-name "interview-platform-cpu-low" \
    --alarm-description "Scale down when CPU < 30%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 30 \
    --comparison-operator LessThanThreshold \
    --evaluation-periods 3 \
    --alarm-actions "arn:aws:autoscaling:$REGION:account-id:scalingPolicy:policy-id:autoScalingGroupName/$ASG_NAME:policyName/interview-platform-scale-down"

# 4. Create target tracking scaling policy for response time
aws autoscaling put-scaling-policy \
    --region $REGION \
    --auto-scaling-group-name $ASG_NAME \
    --policy-name "interview-platform-target-tracking" \
    --policy-type "TargetTrackingScaling" \
    --target-tracking-configuration file://target-tracking-config.json

# target-tracking-config.json
cat > target-tracking-config.json << EOF
{
  "TargetValue": 2.0,
  "CustomizedMetricSpecification": {
    "MetricName": "ResponseTime",
    "Namespace": "InterviewPlatform/Application",
    "Statistic": "Average"
  },
  "ScaleOutCooldown": 300,
  "ScaleInCooldown": 300
}
EOF

echo "✅ Auto Scaling policies configured successfully"
```

This completes Section 8: Infrastructure with comprehensive coverage of:

1. **EC2 Infrastructure Architecture** - Complete production setup with diagrams
2. **Scaling Strategies** - Horizontal and vertical scaling procedures
3. **Backup and Recovery** - Automated backups and disaster recovery plans
4. **Performance Optimization** - Database tuning and application monitoring
5. **Cost Optimization** - Resource analysis and cost management## 8. Infrastructure

### EC2 Infrastructure Architecture

#### Production Infrastructure Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Load Balancer │    │   Web Server    │
│   Load Balancer │◄──►│   (ALB/NLB)     │◄──►│   (Nginx)       │
│   (Optional)    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Primary EC2   │    │   Database      │    │   Backup EC2    │
│   Instance      │◄──►│   (PostgreSQL)  │    │   Instance      │
│   (API Server)  │    │                 │    │   (Standby)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Storage  │    │   Database      │    │   Monitoring    │
│   (EBS/EFS)     │    │   Backups       │    │   & Alerting    │
│                 │    │   (S3)          │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Infrastructure Components

##### Primary Application Server
```bash
# EC2 Instance Specifications
Instance Type: t3.large (2 vCPU, 8GB RAM) - Minimum
Operating System: Ubuntu 20.04 LTS
Storage: 
  - Root Volume: 20GB GP3 SSD
  - Application Volume: 50GB GP3 SSD
  - Log Volume: 20GB GP3 SSD

Security Groups:
  - HTTP (80) from Load Balancer only
  - HTTPS (443) from Load Balancer only  
  - SSH (22) from Admin IPs only
  - PostgreSQL (5432) from Application only
  - Custom (8000) from Load Balancer only
```

##### Database Configuration
```bash
# PostgreSQL Setup on EC2 or RDS
Option 1: Self-managed on EC2
Instance Type: t3.medium (2 vCPU, 4GB RAM)
Storage: 100GB GP3 SSD with encryption
Backup: Automated daily snapshots

Option 2: Amazon RDS PostgreSQL
Instance Class: db.t3.medium
Storage: 100GB GP3 with auto-scaling
Multi-AZ: Enabled for high availability
Automated Backups: 7-day retention
```

### Scaling Strategies

#### Horizontal Scaling Setup

```bash
#!/bin/bash
# horizontal_scaling_setup.sh - Configure load balancing for multiple instances

echo "🔄 Setting up horizontal scaling infrastructure..."

# 1. Create Application Load Balancer
aws elbv2 create-load-balancer \
    --name interview-platform-alb \
    --subnets subnet-12345678 subnet-87654321 \
    --security-groups sg-abcd1234 \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4

# 2. Create Target Group
aws elbv2 create-target-group \
    --name interview-platform-targets \
    --protocol HTTP \
    --port 80 \
    --vpc-id vpc-12345678 \
    --health-check-enabled \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

# 3. Create Auto Scaling Group
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name interview-platform-asg \
    --launch-template LaunchTemplateName=interview-platform-template \
    --min-size 2 \
    --max-size 10 \
    --desired-capacity 2 \
    --target-group-arns arn:aws:elasticloadbalancing:region:account:targetgroup/interview-platform-targets \
    --health-check-type ELB \
    --health-check-grace-period 300

echo "✅ Horizontal scaling setup completed"
```

#### Auto Scaling Configuration

```json
{
  "LaunchTemplate": {
    "LaunchTemplateName": "interview-platform-template",
    "LaunchTemplateData": {
      "ImageId": "ami-0c55b159cbfafe1d0",
      "InstanceType": "t3.large",
      "SecurityGroupIds": ["sg-abcd1234"],
      "IamInstanceProfile": {
        "Name": "InterviewPlatformInstanceProfile"
      },
      "UserData": "base64-encoded-startup-script",
      "BlockDeviceMappings": [
        {
          "DeviceName": "/dev/sda1",
          "Ebs": {
            "VolumeSize": 20,
            "VolumeType": "gp3",
            "DeleteOnTermination": true,
            "Encrypted": true
          }
        }
      ],
      "TagSpecifications": [
        {
          "ResourceType": "instance",
          "Tags": [
            {"Key": "Name", "Value": "InterviewPlatform-AutoScaled"},
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Application", "Value": "InterviewPlatform"}
          ]
        }
      ]
    }
  }
}
```

#### Vertical Scaling Procedures

```bash
#!/bin/bash
# vertical_scaling.sh - Scale EC2 instance vertically

INSTANCE_ID="i-1234567890abcdef0"
NEW_INSTANCE_TYPE="t3.xlarge"  # Scale up to 4 vCPU, 16GB RAM

echo "🔄 Starting vertical scaling process..."

# 1. Create snapshot before scaling
echo "📸 Creating snapshot before scaling..."
aws ec2 create-snapshot \
    --volume-id $(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
                  --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' \
                  --output text) \
    --description "Pre-scaling snapshot $(date +%Y%m%d-%H%M%S)"

# 2. Stop the instance gracefully
echo "⏹️  Stopping instance gracefully..."
# Send shutdown signal to application
curl -X POST http://instance-ip:8000/admin/shutdown

# Wait for graceful shutdown
sleep 30

# Stop EC2 instance
aws ec2 stop-instances --instance-ids $INSTANCE_ID

# Wait for instance to stop
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID

# 3. Change instance type
echo "📈 Changing instance type to $NEW_INSTANCE_TYPE..."
aws ec2 modify-instance-attribute \
    --instance-id $INSTANCE_ID \
    --instance-type Value=$NEW_INSTANCE_TYPE

# 4. Start instance
echo "▶️  Starting instance with new configuration..."
aws ec2 start-instances --instance-ids $INSTANCE_ID

# Wait for instance to start
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# 5. Verify application health
echo "🔍 Verifying application health..."
sleep 60  # Wait for application startup

INSTANCE_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
              --query 'Reservations[0].Instances[0].PublicIpAddress' \
              --output text)

# Health check
health_status=$(curl -s -o /dev/null -w "%{http_code}" http://$INSTANCE_IP:8000/health)

if [ "$health_status" = "200" ]; then
    echo "✅ Vertical scaling completed successfully"
    echo "Instance $INSTANCE_ID scaled to $NEW_INSTANCE_TYPE"
else
    echo "❌ Health check failed after scaling"
    echo "Consider rolling back or investigating issues"
    exit 1
fi
```

### Backup and Recovery Strategies

#### Automated Backup System

```bash
#!/bin/bash
# automated_backup.sh - Comprehensive backup strategy

BACKUP_DIR="/opt/backups"
S3_BUCKET="interview-platform-backups"
RETENTION_DAYS=30
POSTGRES_USER="interview_user"
POSTGRES_DB="interview_platform_prod"

echo "🔄 Starting automated backup process..."

# Create backup directory with timestamp
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$BACKUP_TIMESTAMP"
mkdir -p "$BACKUP_PATH"

# 1. Database Backup
echo "📊 Creating database backup..."
pg_dump -U $POSTGRES_USER -h localhost $POSTGRES_DB | gzip > "$BACKUP_PATH/database_backup.sql.gz"

if [ $? -eq 0 ]; then
    echo "✅ Database backup completed"
else
    echo "❌ Database backup failed"
    exit 1
fi

# 2. Application Files Backup
echo "📁 Creating application files backup..."
tar -czf "$BACKUP_PATH/application_backup.tar.gz" \
    -C /opt/interview-platform \
    --exclude='venv' \
    --exclude='logs' \
    --exclude='__pycache__' \
    .

# 3. Configuration Backup
echo "⚙️  Creating configuration backup..."
cp /opt/interview-platform/.env "$BACKUP_PATH/env_backup"
cp -r /etc/nginx/sites-available/interview-platform "$BACKUP_PATH/nginx_config"
cp -r /etc/supervisor/conf.d/interview-platform.conf "$BACKUP_PATH/supervisor_config"

# 4. Document Storage Backup
echo "📄 Creating document storage backup..."
tar -czf "$BACKUP_PATH/documents_backup.tar.gz" \
    -C /opt/interview-platform/documents \
    .

# 5. System Information Backup
echo "🖥️  Creating system information backup..."
cat > "$BACKUP_PATH/system_info.txt" << EOF
Backup Date: $(date)
Server: $(hostname)
OS: $(lsb_release -d | cut -f2)
Kernel: $(uname -r)
Disk Usage: $(df -h /)
Memory: $(free -h)
Application Version: $(cd /opt/interview-platform && git describe --tags --always)
Database Version: $(psql -U $POSTGRES_USER -h localhost $POSTGRES_DB -c "SELECT version();" -t)
EOF

# 6. Upload to S3
echo "☁️  Uploading backup to S3..."
tar -czf "$BACKUP_DIR/backup_$BACKUP_TIMESTAMP.tar.gz" -C "$BACKUP_PATH" .

aws s3 cp "$BACKUP_DIR/backup_$BACKUP_TIMESTAMP.tar.gz" \
    "s3://$S3_BUCKET/backups/backup_$BACKUP_TIMESTAMP.tar.gz" \
    --storage-class STANDARD_IA

if [ $? -eq 0 ]; then
    echo "✅ Backup uploaded to S3 successfully"
    # Remove local backup after successful upload
    rm -rf "$BACKUP_PATH"
    rm "$BACKUP_DIR/backup_$BACKUP_TIMESTAMP.tar.gz"
else
    echo "❌ S3 upload failed, keeping local backup"
fi

# 7. Clean up old backups
echo "🧹 Cleaning up old backups..."
aws s3api list-objects-v2 \
    --bucket $S3_BUCKET \
    --prefix "backups/" \
    --query "Contents[?LastModified<='$(date -d "$RETENTION_DAYS days ago" --iso-8601)'].Key" \
    --output text | xargs -I {} aws s3 rm "s3://$S3_BUCKET/{}"

echo "✅ Automated backup process completed"

# 8. Send notification
if command -v mail &> /dev/null; then
    echo "Backup completed successfully on $(date)" | \
    mail -s "Interview Platform Backup Completed" admin@yourcompany.com
fi
```

#### Disaster Recovery Procedures

```bash
#!/bin/bash
# disaster_recovery.sh - Complete system recovery

S3_BUCKET="interview-platform-backups"
RECOVERY_DIR="/opt/recovery"
NEW_INSTANCE_CONFIG="recovery_instance.json"

echo "🚨 Starting disaster recovery process..."

# 1. Provision new EC2 instance
echo "🏗️  Provisioning new EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --cli-input-json file://$NEW_INSTANCE_CONFIG \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "New instance ID: $INSTANCE_ID"

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
              --query 'Reservations[0].Instances[0].PublicIpAddress' \
              --output text)

echo "Instance IP: $INSTANCE_IP"

# 2. Download latest backup
echo "📥 Downloading latest backup from S3..."
LATEST_BACKUP=$(aws s3api list-objects-v2 \
    --bucket $S3_BUCKET \
    --prefix "backups/" \
    --query "sort_by(Contents, &LastModified)[-1].Key" \
    --output text)

mkdir -p $RECOVERY_DIR
aws s3 cp "s3://$S3_BUCKET/$LATEST_BACKUP" "$RECOVERY_DIR/latest_backup.tar.gz"

# Extract backup
tar -xzf "$RECOVERY_DIR/latest_backup.tar.gz" -C $RECOVERY_DIR

# 3. Install dependencies on new instance
echo "📦 Installing dependencies on new instance..."
ssh -i ~/.ssh/interview-platform.pem ubuntu@$INSTANCE_IP << 'ENDSSH'
sudo apt update && sudo apt upgrade -y
sudo apt install python3.9 python3.9-venv python3-pip postgresql postgresql-contrib nginx supervisor -y
sudo mkdir -p /opt/interview-platform
sudo chown ubuntu:ubuntu /opt/interview-platform
ENDSSH

# 4. Restore application
echo "📋 Restoring application..."
scp -i ~/.ssh/interview-platform.pem -r "$RECOVERY_DIR/application_backup.tar.gz" \
    ubuntu@$INSTANCE_IP:/opt/interview-platform/

ssh -i ~/.ssh/interview-platform.pem ubuntu@$INSTANCE_IP << 'ENDSSH'
cd /opt/interview-platform
tar -xzf application_backup.tar.gz
rm application_backup.tar.gz

# Setup virtual environment
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ENDSSH

# 5. Restore database
echo "🗄️  Restoring database..."
scp -i ~/.ssh/interview-platform.pem "$RECOVERY_DIR/database_backup.sql.gz" \
    ubuntu@$INSTANCE_IP:/tmp/

ssh -i ~/.ssh/interview-platform.pem ubuntu@$INSTANCE_IP << 'ENDSSH'
# Create database and user
sudo -u postgres createdb interview_platform_prod
sudo -u postgres psql -c "CREATE USER interview_user WITH PASSWORD 'temp_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE interview_platform_prod TO interview_user;"

# Restore database
gunzip -c /tmp/database_backup.sql.gz | sudo -u postgres psql interview_platform_prod
rm /tmp/database_backup.sql.gz
ENDSSH

# 6. Restore configurations
echo "⚙️  Restoring configurations..."
scp -i ~/.ssh/interview-platform.pem "$RECOVERY_DIR/env_backup" \
    ubuntu@$INSTANCE_IP:/opt/interview-platform/.env

scp -i ~/.ssh/interview-platform.pem "$RECOVERY_DIR/nginx_config" \
    ubuntu@$INSTANCE_IP:/tmp/nginx_config

scp -i ~/.ssh/interview-platform.pem "$RECOVERY_DIR/supervisor_config" \
    ubuntu@$INSTANCE_IP:/tmp/supervisor_config

ssh -i ~/.ssh/interview-platform.pem ubuntu@$INSTANCE_IP << 'ENDSSH'
# Restore nginx config
sudo cp /tmp/nginx_config /etc/nginx/sites-available/interview-platform
sudo ln -sf /etc/nginx/sites-available/interview-platform /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Restore supervisor config
sudo cp /tmp/supervisor_config /etc/supervisor/conf.d/interview-platform.conf

# Start services
sudo systemctl start nginx
sudo systemctl start supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start interview-platform

# Enable services
sudo systemctl enable nginx
sudo systemctl enable supervisor
ENDSSH

# 7. Restore document storage
echo "📄 Restoring document storage..."
scp -i ~/.ssh/interview-platform.pem "$RECOVERY_DIR/documents_backup.tar.gz" \
    ubuntu@$INSTANCE_IP:/opt/interview-platform/

ssh -i ~/.ssh/interview-platform.pem ubuntu@$INSTANCE_IP << 'ENDSSH'
cd /opt/interview-platform
mkdir -p documents
tar -xzf documents_backup.tar.gz -C documents/
rm documents_backup.tar.gz
ENDSSH

# 8. Verify recovery
echo "🔍 Verifying recovery..."
sleep 60  # Wait for services to start

health_status=$(curl -s -o /dev/null -w "%{http_code}" http://$INSTANCE_IP/health)

if [ "$health_status" = "200" ]; then
    echo "✅ Disaster recovery completed successfully"
    echo "New instance: $INSTANCE_ID"
    echo "IP Address: $INSTANCE_IP"
    echo "🔄 Update DNS records to point to new IP"
    echo "🔑 Update environment variables with production values"
else
    echo "❌ Recovery verification failed"
    echo "Check logs and manual verification required"
fi

# Cleanup
rm -rf $RECOVERY_DIR

echo "📧 Sending recovery notification..."
if command -v mail &> /dev/null; then
    echo "Disaster recovery completed. New instance: $INSTANCE_ID at $INSTANCE_IP" | \
    mail -s "Interview Platform Disaster Recovery Completed" admin@yourcompany.com
fi
```

### Performance Optimization

#### Database Performance Tuning

```bash
#!/bin/bash
# database_optimization.sh - PostgreSQL performance tuning

echo "🔧 Optimizing PostgreSQL performance..."

# Backup current configuration
sudo cp /etc/postgresql/*/main/postgresql.conf /etc/postgresql/*/main/postgresql.conf.backup

# Apply performance optimizations
sudo tee -a /etc/postgresql/*/main/postgresql.conf << EOF

# Performance Optimizations
shared_buffers = 256MB                    # 25% of available RAM
effective_cache_size = 1GB                # 75% of available RAM
maintenance_work_mem = 64MB               # For maintenance operations
checkpoint_completion_target = 0.9       # Spread checkpoints
wal_buffers = 16MB                        # WAL buffer size
default_statistics_target = 100          # Statistics target
random_page_cost = 1.1                   # SSD optimization
effective_io_concurrency = 200           # SSD optimization

# Connection settings
max_connections = 100                     # Adjust based on load
shared_preload_libraries = 'pg_stat_statements'

# Logging for performance monitoring
log_min_duration_statement = 1000        # Log slow queries (1 second)
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

EOF

# Restart PostgreSQL
sudo systemctl restart postgresql

# Create performance monitoring extension
sudo -u postgres psql interview_platform_prod -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

echo "✅ PostgreSQL optimization completed"
```

#### Application Performance Monitoring

```python
# app/utils/performance_monitoring.py - Application Performance Monitoring
import time
import psutil
import logging
from functools import wraps
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "database_queries": [],
            "memory_usage": [],
            "cpu_usage": [],
            "active_connections": 0
        }
    
    def track_response_time(self, func):
        """Decorator to track API response times"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                
                self.metrics["response_times"].append({
                    "endpoint": func.__name__,
                    "response_time": response_time,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
                
                # Log slow responses
                if response_time > 2.0:  # 2 second threshold
                    logger.warning(f"Slow response: {func.__name__} took {response_time:.2f}s")
                
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                self.metrics["response_times"].append({
                    "endpoint": func.__name__,
                    "response_time": response_time,
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e)
                })
                raise
        
        return wrapper
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "process_count": len(psutil.pids())
            }
            
            # Store metrics for analysis
            self.metrics["cpu_usage"].append(cpu_percent)
            self.metrics["memory_usage"].append(memory.percent)
            
            # Keep only last 1000 entries
            if len(self.metrics["cpu_usage"]) > 1000:
                self.metrics["cpu_usage"] = self.metrics["cpu_usage"][-1000:]
                self.metrics["memory_usage"] = self.metrics["memory_usage"][-1000:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.metrics["response_times"]:
            return {"message": "No performance data available"}
        
        response_times = [m["response_time"] for m in self.metrics["response_times"]]
        
        return {
            "summary_period": "last_24_hours",
            "total_requests": len(response_times),
            "average_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "slow_requests_count": len([t for t in response_times if t > 2.0]),
            "error_rate": len([m for m in self.metrics["response_times"] if m.get("status") == "error"]) / len(self.metrics["response_times"]) * 100,
            "average_cpu_usage": sum(self.metrics["cpu_usage"]) / len(self.metrics["cpu_usage"]) if self.metrics["cpu_usage"] else 0,
            "average_memory_usage": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Performance endpoint
@app.get("/admin/performance")
async def get_performance_metrics(current_user: dict = Depends(check_user_permissions("super_admin"))):
    """Get system performance metrics"""
    try:
        system_metrics = performance_monitor.collect_system_metrics()
        performance_summary = performance_monitor.get_performance_summary()
        
        return {
            "status": 200,
            "message": "Performance metrics retrieved",
            "result": {
                "current_system_metrics": system_metrics,
                "performance_summary": performance_summary,
                "collection_timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")
```

### Cost Optimization Strategies

#### Resource Right-Sizing

```bash
#!/bin/bash
# cost_optimization.sh - Analyze and optimize AWS costs

echo "💰 Starting cost optimization analysis..."

# 1. Analyze current instance utilization
echo "📊 Analyzing instance utilization..."

INSTANCE_ID="i-1234567890abcdef0"
START_TIME=$(date -d '7 days ago' --iso-8601)
END_TIME=$(date --iso-8601)

# Get CPU utilization metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=$INSTANCE_ID \
    --start-time $START_TIME \
    --end-time $END_TIME \
    --period 3600 \
    --statistics Average,Maximum \
    --output table

# 2. Analyze storage usage
echo "💾 Analyzing storage usage..."
df -h | grep -E "(Filesystem|/dev/)"

# 3. Database optimization recommendations
echo "🗄️  Database optimization recommendations..."
sudo -u postgres psql interview_platform_prod << EOF
-- Check database size
SELECT pg_size_pretty(pg_database_size('interview_platform_prod')) as database_size;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY bytes DESC;

-- Check unused indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as index_size
FROM pg_stat_user_indexes 
WHERE idx_scan < 10
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;

EOF

# 4. Generate cost optimization recommendations
cat > /tmp/cost_optimization_report.txt << EOF
=== COST OPTIMIZATION REPORT ===
Generated: $(date)

CURRENT CONFIGURATION:
- Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)
- Instance ID: $INSTANCE_ID
- Region: $(curl -s http://169.254.169.254/latest/meta-data/placement/region)

RECOMMENDATIONS:

1. Instance Right-Sizing:
   - Monitor CPU utilization over 2 weeks
   - If average CPU < 40%, consider smaller instance type
   - If CPU consistently > 80%, consider larger instance type

2. Storage Optimization:
   - Current disk usage: $(df -h / | awk 'NR==2{print $5}')
   - Consider GP3 over GP2 for better price/performance
   - Implement log rotation to reduce storage needs

3. Database Optimization:
   - Remove unused indexes to save storage
   - Implement data archiving for old interview records
   - Consider RDS if management overhead is high

4. Scheduling Optimizations:
   - Use scheduled scaling for predictable load patterns
   - Consider spot instances for non-critical workloads
   - Implement auto-shutdown for development environments

5. Reserved Instances:
   - Consider 1-3 year reserved instances for stable workloads
   - Potential savings: 30-60% over on-demand pricing

EOF

echo "📋 Cost optimization report generated: /tmp/cost_optimization_report.txt"
cat /tmp/cost_optimization_report.txt

# 5. Automated cost alerts setup
echo "🚨 Setting up cost alerts..."

# Create CloudWatch alarm for high costs
aws cloudwatch put-metric-alarm \
    --alarm-name "InterviewPlatform-HighCosts" \
    --alarm-description "Alert when monthly costs exceed threshold" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 200.0 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=Currency,Value=USD \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:region:account:cost-alerts

echo "✅ Cost optimization analysis completed"
```

### High Availability Setup

#### Multi-AZ Database Configuration

```bash
#!/bin/bash
# high_availability_setup.sh - Configure HA for PostgreSQL

echo "🔄 Setting up High Availability for PostgreSQL..."

# 1. Setup PostgreSQL streaming replication
echo "📊 Configuring PostgreSQL streaming replication..."

# Primary server configuration
sudo tee -a /etc/postgresql/*/main/postgresql.conf << EOF
# Replication settings
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
synchronous_commit = on
synchronous_standby_names = 'standby1'
EOF

# Configure pg_hba.conf for replication
sudo tee -a /etc/postgresql/*/main/pg_hba.conf << EOF
# Replication connections
host replication replicator 10.0.0.0/8 md5
EOF

# Create replication user
sudo -u postgres psql << EOF
CREATE USER replicator REPLICATION LOGIN CONNECTION LIMIT 1 ENCRYPTED PASSWORD 'replication_password';
EOF

# 2. Setup standby server
echo "🔄 Setting up standby server..."

# This would be run on the standby server
cat > setup_standby.sh << 'EOF'
#!/bin/bash
# Stop PostgreSQL on standby
sudo systemctl stop postgresql

# Remove existing data directory
sudo rm -rf /var/lib/postgresql/*/main

# Create base backup from primary
sudo -u postgres pg_basebackup -h primary-server-ip -D /var/lib/postgresql/*/main


## 9. Security

### Security Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Gateway   │    │   Application   │
│   (SSL Term)    │◄──►│   (Rate Limit)  │◄──►│   Security      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TLS/SSL       │    │   JWT Auth      │    │   Input         │
│   Encryption    │    │   Validation    │    │   Validation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │◄──►│   Password      │◄──►│   Environment   │
│   Security      │    │   Hashing       │    │   Variables     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Authentication and Authorization Security

#### JWT Token Security Implementation

```python
# app/utils/secure_auth.py - Enhanced JWT Security
import os
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
import logging

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

security = HTTPBearer()

class SecureAuthentication:
    """Enhanced authentication with security features"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with enhanced security"""
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Add security claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16),  # JWT ID for blacklisting
            "token_type": "access"
        })
        
        # Encode token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token with security checks"""
        try:
            # Decode token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Validate required fields
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

# Enhanced authentication dependency
async def get_current_user(token: str = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user with security validation"""
    payload = SecureAuthentication.verify_token(token.credentials)
    return payload

# Role-based access control
def require_role(required_role: str):
    """Decorator for role-based access control"""
    def role_checker(current_user: Dict = Depends(get_current_user)):
        user_role = current_user.get("type")
        
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role not specified"
            )
        
        # Role hierarchy check
        role_hierarchy = {
            "super_admin": 3,
            "company_user": 2,
            "department_user": 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker
```

### Input Validation and Sanitization

#### Comprehensive Input Security

```python
# app/utils/input_validation.py - Input Validation Security
import re
import html
from typing import Any
from pydantic import BaseModel, validator, EmailStr
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Security-focused input validation"""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?[0-9]{10,15}$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    
    # Basic security patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\b)',
        r'(--|#|/\*|\*/)',
    ]
    
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValueError("Email is required")
        
        email = email.strip().lower()
        
        if not cls.EMAIL_PATTERN.match(email):
            raise ValueError("Invalid email format")
        
        if len(email) > 254:  # RFC 5321 limit
            raise ValueError("Email too long")
        
        return email
    
    @classmethod
    def validate_phone(cls, phone: str) -> str:
        """Validate phone number format"""
        if not phone or not isinstance(phone, str):
            raise ValueError("Phone number is required")
        
        # Remove spaces, dashes, parentheses
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        if not cls.PHONE_PATTERN.match(clean_phone):
            raise ValueError("Invalid phone number format")
        
        return clean_phone
    
    @classmethod
    def check_malicious_input(cls, text: str) -> bool:
        """Check for basic malicious patterns"""
        if not text:
            return False
        
        text_upper = text.upper()
        
        # Check SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected")
                return True
        
        # Check XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential XSS attack detected")
                return True
        
        return False
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 1000) -> str:
        """Sanitize text input"""
        if not text:
            return text
        
        # Check length
        if len(text) > max_length:
            raise ValueError(f"Text too long (max {max_length} characters)")
        
        # Check for malicious patterns
        if cls.check_malicious_input(text):
            raise ValueError("Invalid characters detected")
        
        # HTML escape
        text = html.escape(text)
        
        return text.strip()

# Secure Pydantic models
class SecureInterviewData(BaseModel):
    """Secure interview data model"""
    unique_id: str
    full_name: str
    email_id: EmailStr
    phone: str
    domain: str
    language_preference: str = "en"
    
    @validator('full_name')
    def validate_name(cls, v):
        return SecurityValidator.sanitize_text(v, max_length=255)
    
    @validator('phone')
    def validate_phone_format(cls, v):
        return SecurityValidator.validate_phone(v)
    
    @validator('domain')
    def validate_domain(cls, v):
        allowed_domains = [
            'python', 'javascript', 'java', 'react', 'nodejs', 
            'system-design', 'data-science', 'devops'
        ]
        if v not in allowed_domains:
            raise ValueError(f"Domain must be one of: {allowed_domains}")
        return v
    
    @validator('language_preference')
    def validate_language(cls, v):
        allowed_languages = ['en', 'es', 'fr', 'de', 'pt', 'hi', 'zh', 'ja', 'ko', 'ar', 'ru', 'it']
        if v not in allowed_languages:
            raise ValueError(f"Language must be one of: {allowed_languages}")
        return v
```

### Database Security

#### PostgreSQL Security Configuration

```sql
-- database_security.sql - Basic PostgreSQL Security

-- 1. Create database roles with minimal privileges
CREATE ROLE application_role;
CREATE ROLE readonly_role;

-- Grant specific permissions to application role
GRANT CONNECT ON DATABASE interview_platform_prod TO application_role;
GRANT USAGE ON SCHEMA public TO application_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO application_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO application_role;

-- Grant read-only permissions
GRANT CONNECT ON DATABASE interview_platform_prod TO readonly_role;
GRANT USAGE ON SCHEMA public TO readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_role;

-- 2. Create audit logging table
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_id VARCHAR(50),
    record_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

-- 3. Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES (TG_TABLE_NAME, TG_OP, OLD.unique_id::text, row_to_json(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.unique_id::text, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, NEW.unique_id::text, row_to_json(NEW));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit triggers for sensitive tables
CREATE TRIGGER interview_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON interview_details_main
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

### Environment Security

#### Secure Configuration Management

```python
# app/utils/secure_config.py - Secure Configuration
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SecureConfig:
    """Secure configuration management"""
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL securely"""
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL not configured")
        return db_url
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT signing secret"""
        secret = os.getenv('SECRET_KEY')
        if not secret:
            raise ValueError("SECRET_KEY not configured")
        
        if len(secret) < 32:
            logger.warning("SECRET_KEY should be at least 32 characters long")
        
        return secret
    
    @staticmethod
    def get_api_key(service_name: str) -> Optional[str]:
        """Get API key for external service"""
        return os.getenv(f"{service_name.upper()}_API_KEY")
    
    @staticmethod
    def is_debug_mode() -> bool:
        """Check if debug mode is enabled"""
        return os.getenv("DEBUG", "false").lower() == "true"
    
    @staticmethod
    def validate_environment():
        """Validate required environment variables"""
        required_vars = [
            'DATABASE_URL',
            'SECRET_KEY',
            'GEMINI_API_KEY',
            'SMTP_SERVER',
            'SENDER_EMAIL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Security checks
        if SecureConfig.is_debug_mode():
            logger.warning("DEBUG mode is enabled - not recommended for production")
        
        return True

# Global configuration instance
secure_config = SecureConfig()
```

### Security Middleware

#### Request Security Middleware

```python
# app/middleware/security.py - Security Middleware
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Basic security middleware"""
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
        self.rate_limit_store = {}
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Check request size
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_request_size:
            client_ip = self.get_client_ip(request)
            logger.warning(f"Request too large from {client_ip}: {content_length}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Basic rate limiting
        client_ip = self.get_client_ip(request)
        if not self.check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self.add_security_headers(response)
        
        # Log request
        process_time = time.time() - start_time
        logger.info(f"Request: {request.method} {request.url} from {client_ip} in {process_time:.3f}s")
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check X-Forwarded-For header (from load balancer)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Fall back to direct connection IP
        return request.client.host if request.client else 'unknown'
    
    def check_rate_limit(self, client_ip: str, requests_per_minute: int = 60) -> bool:
        """Simple rate limiting"""
        current_time = time.time()
        minute_window = int(current_time // 60)
        
        key = f"{client_ip}:{minute_window}"
        
        if key not in self.rate_limit_store:
            self.rate_limit_store[key] = 0
        
        self.rate_limit_store[key] += 1
        
        # Clean old entries
        self.cleanup_rate_limit_store(current_time)
        
        return self.rate_limit_store[key] <= requests_per_minute
    
    def cleanup_rate_limit_store(self, current_time: float):
        """Clean up old rate limit entries"""
        current_minute = int(current_time // 60)
        keys_to_remove = []
        
        for key in self.rate_limit_store:
            minute = int(key.split(':')[1])
            if current_minute - minute > 5:  # Keep 5 minutes
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.rate_limit_store[key]
    
    def add_security_headers(self, response):
        """Add security headers to response"""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
```

### SSL/TLS Configuration

#### Nginx SSL Security

```nginx
# /etc/nginx/sites-available/interview-platform-secure
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # File upload size limit
    client_max_body_size 15M;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=1r/s;
    
    # API proxy
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Stricter rate limiting for auth endpoints
    location /auth/ {
        limit_req zone=auth burst=5 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

### Security Monitoring

#### Basic Security Logging

```bash
#!/bin/bash
# security_monitor.sh - Basic security monitoring

SECURITY_LOG="/var/log/interview-platform/security.log"
AUTH_LOG="/var/log/auth.log"
NGINX_LOG="/var/log/nginx/access.log"

echo "🔍 Security monitoring report for $(date)"

# Check for failed login attempts
echo "=== Failed Login Attempts (last 24 hours) ==="
grep "Failed password" $AUTH_LOG | grep "$(date +%b\ %d)" | wc -l

# Check for suspicious IP addresses
echo "=== Top IP addresses with failed attempts ==="
grep "Failed password" $AUTH_LOG | grep "$(date +%b\ %d)" | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -nr | head -10

# Check for rate limiting triggers
echo "=== Rate limiting events ==="
grep "limiting requests" /var/log/nginx/error.log | grep "$(date +%Y/%m/%d)" | wc -l

# Check application security events
echo "=== Application security events ==="
if [ -f "$SECURITY_LOG" ]; then
    grep "$(date +%Y-%m-%d)" "$SECURITY_LOG" | wc -l
else
    echo "Security log not found"
fi

# Check for SSL certificate status
echo "=== SSL Certificate Status ==="
if [ -f /etc/letsencrypt/live/*/cert.pem ]; then
    days_until_expiry=$(openssl x509 -in /etc/letsencrypt/live/*/cert.pem -noout -dates | \
        grep notAfter | cut -d= -f2 | xargs -I {} date -d {} +%s)
    current_date=$(date +%s)
    days_left=$(( (days_until_expiry - current_date) / 86400 ))
    echo "Certificate expires in $days_left days"
else
    echo "No SSL certificate found"
fi

echo "=== Security monitoring completed ==="
```

### Security Checklist

#### Production Security Verification

```bash
#!/bin/bash
# security_checklist.sh - Production security verification

echo "🔒 Security Checklist Verification"
echo "=================================="

SCORE=0
MAX_SCORE=10

# 1. Check if HTTPS is enforced
if curl -I http://localhost 2>/dev/null | grep -q "301\|302"; then
    echo "✅ HTTPS redirect configured"
    ((SCORE++))
else
    echo "❌ HTTPS redirect not configured"
fi

# 2. Check if debug mode is disabled
if grep -q "DEBUG=false" /opt/interview-platform/.env 2>/dev/null; then
    echo "✅ Debug mode disabled"
    ((SCORE++))
else
    echo "❌ Debug mode may be enabled"
fi

# 3. Check if strong JWT secret is configured
JWT_SECRET=$(grep "SECRET_KEY" /opt/interview-platform/.env 2>/dev/null | cut -d'=' -f2)
if [ ${#JWT_SECRET} -ge 32 ]; then
    echo "✅ Strong JWT secret configured"
    ((SCORE++))
else
    echo "❌ JWT secret too short or not found"
fi

# 4. Check if firewall is enabled
if ufw status | grep -q "Status: active"; then
    echo "✅ Firewall enabled"
    ((SCORE++))
else
    echo "❌ Firewall not enabled"
fi

# 5. Check if fail2ban is running
if systemctl is-active --quiet fail2ban; then
    echo "✅ Fail2ban active"
    ((SCORE++))
else
    echo "❌ Fail2ban not active"
fi

# 6. Check if SSL certificate is valid
if openssl x509 -in /etc/letsencrypt/live/*/cert.pem -checkend 2592000 -noout 2>/dev/null; then
    echo "✅ SSL certificate valid"
    ((SCORE++))
else
    echo "❌ SSL certificate invalid or expiring"
fi

# 7. Check if database connection is encrypted
if grep -q "sslmode=require" /opt/interview-platform/.env 2>/dev/null; then
    echo "✅ Database SSL enabled"
    ((SCORE++))
else
    echo "❌ Database SSL not configured"
fi

# 8. Check if logs are properly configured
if [ -d "/var/log/interview-platform" ] && [ -f "/var/log/interview-platform/app.log" ]; then
    echo "✅ Logging configured"
    ((SCORE++))
else
    echo "❌ Logging not properly configured"
fi

# 9. Check if rate limiting is active
if nginx -T 2>/dev/null | grep -q "limit_req"; then
    echo "✅ Rate limiting configured"
    ((SCORE++))
else
    echo "❌ Rate limiting not configured"
fi

# 10. Check if security headers are set
if curl -I https://localhost 2>/dev/null | grep -q "X-Frame-Options"; then
    echo "✅ Security headers configured"
    ((SCORE++))
else
    echo "❌ Security headers not configured"
fi

echo ""
echo "SECURITY SCORE: $SCORE/$MAX_SCORE ($(( SCORE * 100 / MAX_SCORE ))%)"

if [ $SCORE -ge 8 ]; then
    echo "✅ SECURITY STATUS: GOOD"
elif [ $SCORE -ge 6 ]; then
    echo "⚠️  SECURITY STATUS: ACCEPTABLE"
else
    echo "❌ SECURITY STATUS: NEEDS IMPROVEMENT"
fi
```

## 10. Monitoring & Logging

### Application Logging Configuration

#### Basic Logging Setup

```python
# app/utils/logging_config.py - Application Logging
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging():
    """Setup application logging"""
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true":
        file_handler = logging.handlers.RotatingFileHandler(
            filename="logs/app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename="logs/errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(console_formatter)
    root_logger.addHandler(error_handler)

# Request logging
import uuid
from fastapi import Request

class RequestLoggingMiddleware:
    """Log API requests"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("requests")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id = str(uuid.uuid4())
            start_time = datetime.now()
            
            # Log request start
            self.logger.info(f"Request {request_id}: {scope['method']} {scope['path']}")
            
            # Process request
            await self.app(scope, receive, send)
            
            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Request {request_id} completed in {duration:.3f}s")
        else:
            await self.app(scope, receive, send)
```

### Health Check Monitoring

#### Application Health Endpoint

```python
# main.py - Health check endpoint
from fastapi import HTTPException
from app.database.config import get_database_connection
import logging

logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check AI service configuration
    ai_api_key = os.getenv("GEMINI_API_KEY")
    health_status["services"]["ai_service"] = "configured" if ai_api_key else "not_configured"
    
    # Check email service configuration
    smtp_server = os.getenv("SMTP_SERVER")
    sender_email = os.getenv("SENDER_EMAIL")
    health_status["services"]["email"] = "configured" if (smtp_server and sender_email) else "not_configured"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "message": "Health check completed",
            "result": health_status
        }
    )
```

### Performance Monitoring

#### Basic Performance Tracking

```python
# app/utils/performance.py - Simple performance monitoring
import time
import psutil
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def track_performance(func):
    """Decorator to track function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow operations
            if execution_time > 2.0:
                logger.warning(f"Slow operation: {func.__name__} took {execution_time:.2f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed operation: {func.__name__} failed after {execution_time:.2f}s - {e}")
            raise
    
    return wrapper

def get_system_metrics():
    """Get basic system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        }
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
        return {}

# Performance endpoint
@app.get("/admin/metrics")
async def get_metrics(current_user: dict = Depends(require_role("super_admin"))):
    """Get system performance metrics"""
    try:
        metrics = get_system_metrics()
        return {
            "status": 200,
            "message": "Metrics retrieved",
            "result": {
                "system_metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")
```

### Log Monitoring

#### Log Analysis Script

```bash
#!/bin/bash
# log_monitor.sh - Basic log monitoring

LOG_DIR="/opt/interview-platform/logs"
APP_LOG="$LOG_DIR/app.log"
ERROR_LOG="$LOG_DIR/errors.log"

echo "📊 Log Analysis Report - $(date)"
echo "================================"

# Check if logs exist
if [ ! -f "$APP_LOG" ]; then
    echo "❌ Application log not found: $APP_LOG"
    exit 1
fi

# Basic log statistics
echo "📈 Log Statistics (last 24 hours):"
echo "Total log entries: $(grep "$(date +%Y-%m-%d)" "$APP_LOG" 2>/dev/null | wc -l)"
echo "Error entries: $(grep "ERROR" "$APP_LOG" 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l)"
echo "Warning entries: $(grep "WARNING" "$APP_LOG" 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l)"

# Check for specific error patterns
echo ""
echo "🔍 Error Pattern Analysis:"
if [ -f "$ERROR_LOG" ]; then
    echo "Database errors: $(grep -i "database\|postgresql" "$ERROR_LOG" 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l)"
    echo "AI service errors: $(grep -i "ai\|gemini" "$ERROR_LOG" 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l)"
    echo "Authentication errors: $(grep -i "auth\|token\|login" "$ERROR_LOG" 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l)"
else
    echo "No error log found"
fi

# Check recent errors
echo ""
echo "🚨 Recent Errors (last 10):"
if [ -f "$ERROR_LOG" ]; then
    tail -10 "$ERROR_LOG" 2>/dev/null || echo "No recent errors"
else
    grep "ERROR" "$APP_LOG" 2>/dev/null | tail -10 || echo "No recent errors"
fi

# Log file sizes
echo ""
echo "📁 Log File Sizes:"
ls -lh "$LOG_DIR"/*.log 2>/dev/null | awk '{print $9 ": " $5}' || echo "No log files found"

echo ""
echo "Log analysis completed"
```

### System Monitoring

#### Basic System Health Script

```bash
#!/bin/bash
# system_monitor.sh - System health monitoring

echo "🖥️  System Health Monitor - $(date)"
echo "=================================="

# System resources
echo "💾 System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk Usage: $(df / | awk 'NR==2{printf "%s", $5}')"

# Service status
echo ""
echo "🔧 Service Status:"
services=("nginx" "supervisor" "postgresql")
for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service: running"
    else
        echo "❌ $service: not running"
    fi
done

# Application status
echo ""
echo "📱 Application Status:"
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ Application: healthy"
else
    echo "❌ Application: unhealthy"
fi

# Database connections
echo ""
echo "🗄️  Database Status:"
if systemctl is-active --quiet postgresql; then
    connections=$(sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" -t 2>/dev/null | tr -d ' ')
    echo "Active connections: $connections"
else
    echo "PostgreSQL not running"
fi

# Disk space check
echo ""
echo "💿 Disk Space Check:"
df -h | grep -E "(Filesystem|/dev/)" | awk '{printf "%-20s %s\n", $1, $5}'

# Load average
echo ""
echo "⚡ Load Average:"
uptime | awk -F'load average:' '{print $2}'

echo ""
echo "System monitoring completed"
```


## 11. Error Handling & Troubleshooting

### Exception Handling Framework

#### Custom Exception Classes

```python
# app/utils/exceptions.py - Basic Exception Handling
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

class DatabaseException(Exception):
    """Database operation exceptions"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AIServiceException(Exception):
    """AI service exceptions"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AuthenticationException(Exception):
    """Authentication exceptions"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
```

#### Global Exception Handlers

```python
# main.py - Exception handlers setup
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

def setup_exception_handlers(app):
    """Setup global exception handlers"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "message": "Request validation failed",
                "result": []
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        logger.warning(f"HTTP exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": exc.status_code,
                "message": exc.detail,
                "result": []
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unexpected error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": 500,
                "message": "Internal server error",
                "result": []
            }
        )

# Setup exception handlers
setup_exception_handlers(app)
```

### Common Error Scenarios

#### Database Connection Issues

```python
# Database error handling example
def get_database_connection():
    """Get database connection with error handling"""
    try:
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise DatabaseException("Database connection failed")
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise DatabaseException("Database operation failed")
```

#### AI Service Failures

```python
# AI service error handling
async def generate_questions_with_fallback(domain: str, difficulty: str, count: int = 5):
    """Generate questions with fallback handling"""
    try:
        # Try AI service
        ai_service = AIService()
        return await ai_service.generate_questions(domain, difficulty, count)
    except Exception as e:
        logger.warning(f"AI service failed: {e}")
        # Return fallback questions
        return get_fallback_questions(domain, difficulty, count)

def get_fallback_questions(domain: str, difficulty: str, count: int):
    """Fallback questions when AI service fails"""
    fallback_questions = [
        {
            "question": f"Explain basic concepts in {domain}",
            "expected_answer": f"Fundamental knowledge of {domain}",
            "keywords": [domain, "basics", "fundamentals"]
        }
    ]
    return fallback_questions[:count]
```

### Health Check Implementation

```python
# Health check with error handling
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Database health
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # AI service health
    try:
        ai_service = AIService()
        health_status["services"]["ai_service"] = "healthy" if ai_service.ai_available else "disabled"
    except Exception as e:
        logger.error(f"AI service check failed: {e}")
        health_status["services"]["ai_service"] = "unhealthy"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "message": "Health check completed",
            "result": health_status
        }
    )
```

### Error Logging

```python
# Enhanced error logging
import traceback

def log_error_with_context(error: Exception, context: dict = None):
    """Log error with additional context"""
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context or {}
    }
    
    logger.error(f"Error occurred: {error_info}")
```

### Troubleshooting Guide

#### Common Issues and Solutions

**1. Database Connection Failed**
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Check database exists
sudo -u postgres psql -l | grep interview_platform

# Test connection
psql $DATABASE_URL
```

**2. Application Won't Start**
```bash
# Check supervisor status
sudo supervisorctl status

# Check application logs
tail -f /opt/interview-platform/logs/app.log

# Manual start for debugging
cd /opt/interview-platform
source venv/bin/activate
python main.py
```

**3. AI Service Errors**
```bash
# Check API key configuration
grep GEMINI_API_KEY /opt/interview-platform/.env

# Test AI service manually
curl -H "Authorization: Bearer $GEMINI_API_KEY" https://api.gemini.com/v1/test
```

**4. Authentication Issues**
```bash
# Check JWT secret configuration
grep SECRET_KEY /opt/interview-platform/.env

# Verify token generation
python -c "from app.utils.auth import create_access_token; print('JWT working')"
```

### Error Response Format

```python
# Standardized error response format
def create_error_response(status_code: int, message: str, details: dict = None):
    """Create standardized error response"""
    return {
        "status": status_code,
        "message": message,
        "result": details or []
    }

# Usage examples
@app.post("/example")
async def example_endpoint():
    try:
        # Some operation
        pass
    except ValidationError as e:
        return create_error_response(400, "Validation failed", {"errors": str(e)})
    except DatabaseException as e:
        return create_error_response(500, "Database error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_response(500, "Internal server error")
```

### Debugging Tools

#### Development Debugging

```python
# Debug mode configuration
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG_MODE:
    import debugpy
    debugpy.listen(5678)
    logger.info("Debug server started on port 5678")

# Enhanced logging for development
if DEBUG_MODE:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")
```

#### Production Error Tracking

```python
# Simple error tracking
error_counts = {}

def track_error(error_type: str):
    """Track error occurrences"""
    if error_type not in error_counts:
        error_counts[error_type] = 0
    error_counts[error_type] += 1
    
    # Log if error count is high
    if error_counts[error_type] > 10:
        logger.warning(f"High error count for {error_type}: {error_counts[error_type]}")

@app.get("/admin/errors")
async def get_error_stats(current_user: dict = Depends(verify_token)):
    """Get error statistics"""
    if current_user.get("type") != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "status": 200,
        "message": "Error statistics retrieved",
        "result": error_counts
    }
```

