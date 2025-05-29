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
    scraped_content: Optional[str] = None

class SectionResearchNotes(BaseModel):
    section_id: str
    findings: List[ResearchFinding]
    summary: Optional[str] = None

class ResearchNotes(BaseModel):
    notes_by_section: List[SectionResearchNotes]

class SectionPlanWithResearch(BaseModel):
    section_plan: SectionPlan
    research_notes: SectionResearchNotes

class SythesizedSection(BaseModel):
    section_id: int
    title: str
    content: str

class SythesizedArticle(BaseModel):
    sections: List[SythesizedSection]
    full_text_for_editing: Optional[str] = None 
    
class FinalArticle(BaseModel):
    title: str
    meta_description: str
    meta_keywords: List[str] = []
    image_description: str
    table_of_contents: List[str] = []
    tldr: str
    article_body: str
    conclusion: str
    references: List[str] = []
    full_text_markdown: str

class FinalArticleWithGemini(BaseModel):
    gemini_article: str
    gemini_article_html: Optional[str] = None