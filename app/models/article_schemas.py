from pydantic import BaseModel, Field
from typing import List, Optional

class ArticleBrief(BaseModel):
    topic: str
    keywords: Optional[List[str]] = None
    target_audience: Optional[str] = None
    tone: Optional[str] = "informative"
    desired_length_words: Optional[int] = 1000

class SectionPlan(BaseModel):
    section_id: int 
    title: str
    key_points: List[str]
    research_queries: Optional[List[str]] = None

class SectionPlans(BaseModel):
    section_plans: List[SectionPlan]
    article_brief: ArticleBrief

class ArticlePlan(BaseModel):
    main_title_suggestion: str
    overall_abstract: Optional[str] = None
    sections: List[SectionPlan]

class ResearchFinding(BaseModel):
    source_url: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = None 

class SectionResearchNotes(BaseModel):
    section_id: str
    findings: List[ResearchFinding]
    summary: Optional[str] = None

class ResearchNotes(BaseModel):
    notes_by_section: List[SectionResearchNotes]
    general_findings: Optional[List[ResearchFinding]] = None 

class ArticleSection(BaseModel):
    section_id: str
    title: str
    content: str
    references: Optional[List[str]] = None

class DraftArticle(BaseModel):
    main_title: str
    sections: List[ArticleSection]
    full_text_for_editing: Optional[str] = None 

class FinalArticle(BaseModel):
    title: str
    introduction: Optional[str] = None 
    body_sections: List[ArticleSection] 
    conclusion: Optional[str] = None 
    full_text_markdown: str
    full_text_html: Optional[str] = None
    meta_description: Optional[str] = None
    citations: Optional[List[str]] = None