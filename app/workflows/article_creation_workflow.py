from __future__ import annotations
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
from slugify import slugify
import markdown

from agents import Runner, gen_trace_id, trace
from app.agents.planner_agent import agent as planner_agent
from app.agents.research_agent import agent as research_agent
from app.agents.section_synthesizer_agent import agent as section_synthesizer_agent
from app.agents.article_synthesizer_agent import agent as article_synthesizer_agent
from app.models.article_schemas import SectionPlans, ResearchNotes, SythesizedArticle, SythesizedSection, SectionPlanWithResearch, FinalArticle, FinalArticleWithGemini
from app.core.printer import Printer
from app.core.console_config import console
from app.services.workflow_display_manager import WorkflowDisplayManager
from app.services.workflow_data_manager import WorkflowDataManager
from app.services.web_scraping_service import WebScrapingService
from app.services import gemini_enhancer
from app.models.workflow_schemas import ArticleCreationWorkflowConfig

class ArticleCreationWorkflow:
    """
    Orchestrates the article creation flow: planning, researching, scraping, and synthesizing.
    """
    DATA_DIR = Path("data")

    def __init__(self, config: ArticleCreationWorkflowConfig) -> None:
        self.config = config
        self.query_slug = self._get_query_slug(self.config.query)
        self.printer = Printer(console)
        
        # Initialize service components
        self.display_manager = WorkflowDisplayManager(self.printer, self.config.query, self.query_slug)
        self.data_manager = WorkflowDataManager(self.DATA_DIR, self.printer)
        self.web_scraping_service = WebScrapingService()

    def _get_query_slug(self, query: str) -> str:
        return slugify(query)

    async def run(self) -> None:
        trace_id = gen_trace_id()
        with trace("Article Creation Workflow Trace", trace_id=trace_id):
            # Start the workflow with clear indication
            self.display_manager.display_workflow_start(trace_id)

            # Phase 1: Article Planning
            self.display_manager.display_phase_start(1, "Article Planning")
            section_plans = await self._plan_article()

            if section_plans:
                self.printer.update_item("plan_summary", f"✅ Generated plan with {len(section_plans.section_plans)} sections", is_done=True, hide_checkmark=True)
                self.display_manager.print_article_plan(section_plans)
            else:
                self.printer.update_item("plan_failed", "❌ Article planning failed - workflow terminated", is_done=True, hide_checkmark=True)
                self.display_manager.display_workflow_complete()
                return
                
            # Phase 2: Research
            self.display_manager.display_phase_start(2, "Research Collection")
            research_notes = await self._research_sections(section_plans)

            if research_notes:
                self.printer.update_item("research_summary", f"✅ Collected research for {len(research_notes.notes_by_section)} sections", is_done=True, hide_checkmark=True)
                self.display_manager.print_research_summary(research_notes)
            else:
                self.printer.update_item("research_warning", "⚠️ No research notes generated - continuing with limited data", is_done=True, hide_checkmark=True)
                
            # Phase 3: Web Content Scraping
            self.display_manager.display_phase_start(3, "Web Content Scraping")
            final_research_notes = await self._scrape_web_content(research_notes)

            if final_research_notes:
                self.display_manager.print_scraping_summary(final_research_notes)
            else:
                self.printer.update_item("scraping_skipped", "⚠️ Web scraping skipped or failed", is_done=True, hide_checkmark=True)

            # Phase 4: Section Synthesis
            self.display_manager.display_phase_start(4, "Section Synthesis")
            synthesized_article = await self._synthesize_sections(section_plans, final_research_notes)

            if synthesized_article:
                self.printer.update_item("synthesis_summary", f"✅ Synthesized {len(synthesized_article.sections)} sections", is_done=True, hide_checkmark=True)
                self.display_manager.print_synthesis_summary(synthesized_article)
            else:
                self.printer.update_item("synthesis_failed", "❌ Article synthesis failed", is_done=True, hide_checkmark=True)

            # Phase 5: Final Article Creation
            self.display_manager.display_phase_start(5, "Final Article Creation")
            final_article = await self._create_openai_final_article(synthesized_article, final_research_notes)

            if final_article:
                self.printer.update_item("final_success", "🎉 Final article created successfully", is_done=True, hide_checkmark=True)
                self.display_manager.print_final_article_summary(final_article)
            else:
                self.printer.update_item("final_failed", "❌ Final article creation failed", is_done=True, hide_checkmark=True)

            # Phase 6: Gemini Enhancement
            self.display_manager.display_phase_start(6, "Gemini Article Enhancement")
            gemini_enhanced_article = await self._enhance_article_with_gemini(final_article)

            if gemini_enhanced_article:
                self.printer.update_item("gemini_success", "✨ Article enhanced by Gemini successfully", is_done=True, hide_checkmark=True)
                # Display a snippet of the Gemini enhanced article
                self.printer.update_item("gemini_snippet", f"Gemini Enhanced Article (snippet): {gemini_enhanced_article.gemini_article[:200]}...", is_done=True, hide_checkmark=True)
            else:
                self.printer.update_item("gemini_failed", "❌ Gemini article enhancement failed", is_done=True, hide_checkmark=True)

            # Workflow completion
            self.display_manager.display_workflow_complete()


    async def _plan_article(self) -> SectionPlans | None:
        """
        Generate a section plan for the article using the planner agent.

        This method checks for a cached article plan for the current query. If a cached plan exists,
        it is loaded and returned. Otherwise, it invokes the planner agent to create a new section plan
        based on the workflow configuration. The resulting plan is saved for future use.

        Returns:
            SectionPlans | None: The generated or cached section plans, or None if planning fails.
        """
        phase_name = "planning"
        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, SectionPlans)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached article plan", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🔄 Creating new article plan...")
        try:
            result = await Runner.run(planner_agent, input=self.config.query, context=self.config)
            section_plans_output = result.final_output_as(SectionPlans)
            self.data_manager.save_data(self.query_slug, phase_name, section_plans_output)
            self.printer.update_item(
                phase_name,
                f"✅ Planning complete - {len(section_plans_output.section_plans)} sections created",
                is_done=True,
            )
            return section_plans_output
        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Planning failed: {str(e)}", is_done=True)
            return None

    async def _research_sections(self, section_plans: SectionPlans | None) -> ResearchNotes | None:
        phase_name = "researching"
        if not section_plans:
            self.printer.update_item(phase_name, "⏭️ Skipped - no section plan available", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached research notes", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, f"🔄 Researching {len(section_plans.section_plans)} sections...")
        try:
            result = await Runner.run(research_agent, input=section_plans.model_dump_json(), max_turns=100)
            research_notes_output = result.final_output_as(ResearchNotes)
            self.data_manager.save_data(self.query_slug, phase_name, research_notes_output)
            self.printer.update_item(
                phase_name,
                f"✅ Research complete - {len(research_notes_output.notes_by_section)} sections researched",
                is_done=True,
            )
            return research_notes_output
        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Research failed: {str(e)}", is_done=True)
            return None

    async def _scrape_web_content(self, original_research_notes: ResearchNotes | None) -> ResearchNotes | None:
        phase_name = "scrape_web_content"

        if not original_research_notes:
            self.printer.update_item(phase_name, "⏭️ Skipped - no research notes available", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached scraped content", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🔄 Analyzing URLs for scraping...")

        # Extract URLs and check if any exist
        urls_to_scrape = self.web_scraping_service._extract_urls_from_research(original_research_notes)
        
        if not urls_to_scrape:
            self.printer.update_item(phase_name, "⚠️ No URLs found to scrape - using original notes", is_done=True)
            self.data_manager.save_data(self.query_slug, phase_name, original_research_notes)
            return original_research_notes
        
        self.printer.update_item(phase_name, f"🌐 Scraping {len(urls_to_scrape)} unique URLs...")

        try:
            # Use the web scraping service to extract and scrape URLs
            notes_to_augment = await self.web_scraping_service.extract_and_scrape_urls(original_research_notes)
            
            if notes_to_augment:
                self.data_manager.save_data(self.query_slug, phase_name, notes_to_augment)
                total_urls, scraped_urls, success_rate = self.web_scraping_service.get_scraping_stats(notes_to_augment)
                self.printer.update_item(
                    phase_name,
                    f"✅ Scraping complete - {scraped_urls}/{total_urls} URLs scraped successfully",
                    is_done=True,
                )
                return notes_to_augment
            else:
                self.printer.update_item(phase_name, "❌ Scraping failed - using original notes", is_done=True)
                return original_research_notes
                
        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Scraping failed: {str(e)} - using original notes", is_done=True)
            return original_research_notes
        
    async def _synthesize_sections(
        self, 
        section_plans: SectionPlans | None, 
        research_notes: ResearchNotes | None
    ) -> SythesizedArticle | None:
        phase_name = "synthesize_sections"

        if not section_plans or not research_notes:
            self.printer.update_item(phase_name, "⏭️ Skipped - missing plans or research notes", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, SythesizedArticle)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached synthesized article", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, f"🔄 Synthesizing {len(section_plans.section_plans)} sections...")

        # Prepare inputs for each section synthesis task
        synthesis_tasks = []
        research_notes_map = {note.section_id: note for note in research_notes.notes_by_section}

        for plan in section_plans.section_plans:
            section_id_str = str(plan.section_id)
            if section_id_str in research_notes_map:
                section_specific_research = research_notes_map[section_id_str]
                
                agent_input = SectionPlanWithResearch(
                    section_plan=plan,
                    research_notes=section_specific_research
                )
                synthesis_tasks.append(
                    Runner.run(section_synthesizer_agent, agent_input.model_dump_json())
                )

        if not synthesis_tasks:
            self.printer.update_item(phase_name, "❌ No sections available for synthesis", is_done=True)
            return None

        try:
            # Run all synthesis tasks concurrently
            results = await asyncio.gather(*synthesis_tasks)
            
            synthesized_sections: list[SythesizedSection] = []
            failed_syntheses = 0

            for i, result in enumerate(results):
                try:
                    section_output = result.final_output_as(SythesizedSection)
                    synthesized_sections.append(section_output)
                except Exception as e:
                    failed_syntheses += 1
                    original_plan = section_plans.section_plans[i]
                    self.printer.update_item(f"synthesis_section_fail_{original_plan.section_id}", f"⚠️ Section {original_plan.section_id} synthesis failed", is_done=True, hide_checkmark=True)

            if not synthesized_sections:
                self.printer.update_item(phase_name, "❌ All section syntheses failed", is_done=True)
                return None

            # Create the final SythesizedArticle object
            final_article = SythesizedArticle(sections=synthesized_sections)
            final_article.full_text_for_editing = "\n\n---\n\n".join(
                f"{s.content}" for s in synthesized_sections
            )

            self.data_manager.save_data(self.query_slug, phase_name, final_article)
            
            success_message = f"✅ Synthesis complete - {len(synthesized_sections)} sections synthesized"
            if failed_syntheses > 0:
                success_message += f" ({failed_syntheses} failed)"
            self.printer.update_item(phase_name, success_message, is_done=True)
            
            return final_article

        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Synthesis failed: {str(e)}", is_done=True)
            return None

    async def _create_openai_final_article(self, synthesized_article: SythesizedArticle | None, final_research_notes: ResearchNotes | None) -> FinalArticle | None:
        phase_name = "openai_final_article_creation"

        if not synthesized_article or not synthesized_article.full_text_for_editing:
            self.printer.update_item(phase_name, "⏭️ Skipped - no synthesized content available", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, FinalArticle)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached final article", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🔄 Creating final article with SEO optimization...")
        
        # Extract source URLs from research notes if available
        source_urls = set()
        if final_research_notes and final_research_notes.notes_by_section:
            for section_note in final_research_notes.notes_by_section:
                for finding in section_note.findings:
                    if finding.source_url:
                        source_urls.add(finding.source_url)

        try:
            # Prepare combined input for the agent including both content and research sources
            agent_input = {
                "synthesized_content": synthesized_article.full_text_for_editing,
                "source_urls": list(source_urls)
            }
            
            result = await Runner.run(
                article_synthesizer_agent, 
                input=json.dumps(agent_input, indent=2)
            )
            final_article_output = result.final_output_as(FinalArticle)
            
            self.data_manager.save_data(self.query_slug, phase_name, final_article_output)
            
            reference_count = len(final_article_output.references) if final_article_output.references else 0
            self.printer.update_item(
                phase_name,
                f"✅ Final article created with {reference_count} references",
                is_done=True,
            )
            return final_article_output

        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Final article creation failed: {str(e)}", is_done=True)
            return None

    async def _enhance_article_with_gemini(self, final_article: FinalArticle | None) -> FinalArticleWithGemini | None:
        phase_name = "gemini_enhancement"

        if not final_article or not final_article.full_text_markdown:
            self.printer.update_item(phase_name, "⏭️ Skipped - no final article content available for Gemini enhancement", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.query_slug, phase_name, FinalArticleWithGemini)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached Gemini enhanced article", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🤖 Enhancing article with Gemini...")
        
        try:
            enhanced_markdown = await asyncio.to_thread(
                gemini_enhancer.generate, 
                final_article.full_text_markdown,
                self.config.query,      # Pass query
                self.config.article_layout # Pass article_layout
            )
            
            if not enhanced_markdown:
                self.printer.update_item(phase_name, "❌ Gemini enhancement returned empty content.", is_done=True)
                return None

            # Convert markdown to HTML
            enhanced_html = markdown.markdown(enhanced_markdown).replace('\n', '')

            gemini_article_output = FinalArticleWithGemini(
                gemini_article=enhanced_markdown,
                gemini_article_html=enhanced_html
            )
            
            self.data_manager.save_data(self.query_slug, phase_name, gemini_article_output)
            
            self.printer.update_item(
                phase_name,
                "✅ Gemini enhancement complete",
                is_done=True,
            )
            return gemini_article_output

        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Gemini enhancement failed: {str(e)}", is_done=True)
            return None


if __name__ == "__main__":
    config = ArticleCreationWorkflowConfig(
        query=input("Enter the article description: "),
        article_layout=input("Enter the article layout (leave empty for auto-generated layout): ")
    )
    workflow = ArticleCreationWorkflow(config)
    asyncio.run(workflow.run())