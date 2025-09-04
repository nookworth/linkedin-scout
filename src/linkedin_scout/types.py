from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl


class SearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"


class ConnectionDegree(str, Enum):
    FIRST = "1st"
    SECOND = "2nd"  
    THIRD_PLUS = "3rd+"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class Contact(BaseModel):
    id: Optional[str] = None
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: str
    location: Optional[str] = None
    profile_url: HttpUrl
    linkedin_id: Optional[str] = None
    summary: Optional[str] = None
    relevance_score: Optional[float] = None
    search_query_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Company(BaseModel):
    id: Optional[str] = None
    name: str
    linkedin_url: Optional[HttpUrl] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SearchCriteria(BaseModel):
    id: Optional[str] = None
    name: str
    companies: Optional[List[str]] = Field(default_factory=list)
    job_titles: Optional[List[str]] = Field(default_factory=list)
    locations: Optional[List[str]] = Field(default_factory=list)
    seniority_levels: Optional[List[str]] = Field(default_factory=list)
    industries: Optional[List[str]] = Field(default_factory=list)
    keywords: Optional[List[str]] = Field(default_factory=list)
    exclude_keywords: Optional[List[str]] = Field(default_factory=list)
    connection_degree: Optional[ConnectionDegree] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    id: Optional[str] = None
    search_criteria_id: str
    query: str
    status: SearchStatus = SearchStatus.PENDING
    total_results: Optional[int] = None
    processed_results: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SearchOptions(BaseModel):
    companies: Optional[List[str]] = None
    limit: int = 50
    offset: int = 0
    criteria_id: Optional[str] = None
    dry_run: bool = False
    ai_enhanced: bool = True
    results_per_company: int = 20
    user_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExportOptions(BaseModel):
    format: ExportFormat = ExportFormat.CSV
    output: Optional[str] = None
    fields: Optional[List[str]] = None
    filter_company: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class AIConfig(BaseModel):
    model: str = "llama3.2:3b"
    endpoint: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 1000
    timeout: int = 30


class BrowserConfig(BaseModel):
    headless: bool = True
    user_data_dir: Optional[str] = None
    slow_mo: int = 0
    timeout: int = 30000
    rate_limit_delay: int = 2000


class Config(BaseModel):
    database_url: str = "sqlite:///linkedin_scout.db"
    ai: AIConfig = Field(default_factory=AIConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    linkedin_base_url: str = "https://www.linkedin.com"
    export_dir: str = "./exports"


class AIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchSession(BaseModel):
    id: Optional[str] = None
    search_query_id: str
    status: SearchStatus = SearchStatus.PENDING
    contacts_found: int = 0
    pages_processed: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None