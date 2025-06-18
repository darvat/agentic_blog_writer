from __future__ import annotations

from app.models.article_schemas import SectionPlans, ResearchNotes, SythesizedArticle, FinalArticle
from app.core.printer import Printer


class WorkflowDisplayManager:
    """
    Handles all display and status printing for the article creation workflow.
    """

    def __init__(self, printer: Printer, title: str, title_slug: str):
        self.printer = printer
        self.title = title
        self.title_slug = title_slug

    def display_workflow_start(self, trace_id: str | None = None) -> None:
        """Display workflow initialization status"""
        self.printer.update_item("workflow_start", "🚀 Starting article creation workflow", is_done=True, hide_checkmark=True)
        self.printer.update_item("title", f"📝 Title: {self.title}", is_done=True, hide_checkmark=True)
        self.printer.update_item("slug", f"📁 Data directory: data/{self.title_slug}", is_done=True, hide_checkmark=True)
        
        if trace_id:
            self.printer.update_item(
                "trace_id",
                f"🔗 View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}",
                is_done=True,
                hide_checkmark=True,
            )

    def display_phase_start(self, phase_number: int, phase_name: str) -> None:
        """Display phase start status"""
        phase_emojis = {
            1: "📋",
            2: "🔍", 
            3: "🌐",
            4: "✍️",
            5: "🎯"
        }
        emoji = phase_emojis.get(phase_number, "🔄")
        self.printer.update_item(f"phase_{phase_number}", f"{emoji} PHASE {phase_number}: {phase_name}", is_done=True, hide_checkmark=True)

    def display_workflow_complete(self) -> None:
        """Display workflow completion and end printer"""
        self.printer.update_item("workflow_complete", "🏁 Article creation workflow completed", is_done=True)
        self.printer.end()

    def print_article_plan(self, section_plans: SectionPlans) -> None:
        """Print a formatted summary of the article plan"""
        print("\n" + "="*60)
        print("📋 ARTICLE PLAN")
        print("="*60)
        print(f"📰 Topic: {section_plans.article_brief.topic}")
        print(f"👥 Target Audience: {section_plans.article_brief.target_audience}")
        print(f"🔍 Keywords: {', '.join(section_plans.article_brief.keywords)}")
        print(f"\n📑 Sections ({len(section_plans.section_plans)}):")
        for i, plan in enumerate(section_plans.section_plans, 1):
            print(f"  {i}. {plan.title} (ID: {plan.section_id})")
            if plan.key_points:
                print(f"     🎯 Key Points: {', '.join(plan.key_points[:3])}{'...' if len(plan.key_points) > 3 else ''}")
            if plan.research_queries:
                print(f"     🔍 Research Queries: {len(plan.research_queries)} queries")
        print("="*60 + "\n")

    def print_research_summary(self, research_notes: ResearchNotes) -> None:
        """Print a formatted summary of research findings"""
        print("\n" + "="*60)
        print("🔍 RESEARCH SUMMARY")
        print("="*60)
        for section_note in research_notes.notes_by_section:
            print(f"📑 Section {section_note.section_id}:")
            if section_note.summary:
                print(f"   📝 Summary: {section_note.summary[:100]}{'...' if len(section_note.summary) > 100 else ''}")
            else:
                print(f"   📝 Summary: No summary available")
            print(f"   📊 Findings: {len(section_note.findings)} sources found")
            for i, finding in enumerate(section_note.findings[:3], 1):  # Show first 3 findings
                print(f"     {i}. {finding.source_url}")
            if len(section_note.findings) > 3:
                print(f"     ... and {len(section_note.findings) - 3} more sources")
            print()
        print("="*60 + "\n")

    def print_scraping_summary(self, research_notes: ResearchNotes) -> None:
        """Print a formatted summary of web scraping results"""
        print("\n" + "="*60)
        print("🌐 WEB SCRAPING SUMMARY")
        print("="*60)
        
        total_urls = 0
        scraped_urls = 0
        
        for section_note in research_notes.notes_by_section:
            section_total = len(section_note.findings)
            section_scraped = sum(1 for finding in section_note.findings if finding.scraped_content)
            total_urls += section_total
            scraped_urls += section_scraped
            
            print(f"📑 Section {section_note.section_id}: {section_scraped}/{section_total} URLs scraped")
        
        success_rate = (scraped_urls / total_urls * 100) if total_urls > 0 else 0
        print(f"\n📊 Overall: {scraped_urls}/{total_urls} URLs scraped successfully ({success_rate:.1f}%)")
        print("="*60 + "\n")

    def print_synthesis_summary(self, synthesized_article: SythesizedArticle) -> None:
        """Print a formatted summary of synthesized sections"""
        print("\n" + "="*60)
        print("✍️ SYNTHESIS SUMMARY")
        print("="*60)
        
        for i, section in enumerate(synthesized_article.sections, 1):
            word_count = len(section.content.split()) if section.content else 0
            print(f"{i}. {section.title} (ID: {section.section_id})")
            print(f"   📊 Word count: {word_count} words")
            if section.content:
                preview = section.content[:150].replace('\n', ' ')
                print(f"   📝 Preview: {preview}{'...' if len(section.content) > 150 else ''}")
            print()
        
        total_words = sum(len(s.content.split()) if s.content else 0 for s in synthesized_article.sections)
        print(f"📊 Total article length: {total_words} words across {len(synthesized_article.sections)} sections")
        print("="*60 + "\n")

    def print_final_article_summary(self, final_article: FinalArticle) -> None:
        """Print a formatted summary of the final article"""
        print("\n" + "="*60)
        print("🎯 FINAL ARTICLE SUMMARY")
        print("="*60)
        print(f"📰 Title: {final_article.title}")
        print(f"📝 Meta Description: {final_article.meta_description}")
        print(f"🏷️ Keywords: {final_article.meta_keywords}")
        
        if final_article.tldr:
            print(f"📋 TL;DR: {final_article.tldr}")
        
        if final_article.table_of_contents:
            print(f"📑 Table of Contents: Available")
        
        if final_article.article_body:
            word_count = len(final_article.article_body.split())
            print(f"📊 Article Length: {word_count} words")
        
        if final_article.conclusion:
            print(f"🎯 Conclusion: Available ({len(final_article.conclusion.split())} words)")
        
        if final_article.references:
            print(f"📚 References: {len(final_article.references)} sources")
        
        print("="*60 + "\n") 