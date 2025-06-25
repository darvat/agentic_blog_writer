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
from app.agents.research_recovery_agent import agent as research_recovery_agent
from app.models.article_schemas import SectionPlans, ResearchNotes, SythesizedArticle, SythesizedSection, SectionPlanWithResearch, FinalArticle, FinalArticleWithGemini, SectionResearchNotes
from app.core.printer import Printer
from app.core.console_config import console
from app.services.workflow_display_manager import WorkflowDisplayManager
from app.services.workflow_data_manager import WorkflowDataManager
from app.services.web_scraping_service import WebScrapingService
from app.services import gemini_enhancer
from app.models.workflow_schemas import ArticleCreationWorkflowConfig
from app.core.config import config as app_config

class ArticleCreationWorkflow:
    """
    Orchestrates the article creation flow: planning, researching, scraping, and synthesizing.
    """
    DATA_DIR = Path("data")

    def __init__(self, config: ArticleCreationWorkflowConfig) -> None:
        self.config = config
        self.title_slug = self._get_title_slug(self.config.title)
        self.printer = Printer(console)
        
        # Initialize service components
        self.display_manager = WorkflowDisplayManager(self.printer, self.config.title, self.title_slug)
        self.data_manager = WorkflowDataManager(self.DATA_DIR, self.printer)
        self.web_scraping_service = WebScrapingService()

    def _get_title_slug(self, title: str) -> str:
        return slugify(title)

    async def run(self) -> None:
        trace_id = gen_trace_id()
        with trace("Article Creation Workflow Trace", trace_id=trace_id):
            # Start the workflow with clear indication
            self.display_manager.display_workflow_start(trace_id)

            # Save initial configuration
            self.printer.update_item("save_config", "💾 Saving workflow configuration...", is_done=False)
            self.data_manager.save_data(self.title_slug, "workflow_config", self.config)
            self.printer.update_item("save_config", "✅ Workflow configuration saved", is_done=True, hide_checkmark=True)

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

        This method checks for a cached article plan for the current title. If a cached plan exists,
        it is loaded and returned. Otherwise, it invokes the planner agent to create a new section plan
        based on the workflow configuration. The resulting plan is saved for future use.

        Returns:
            SectionPlans | None: The generated or cached section plans, or None if planning fails.
        """
        phase_name = "planning"
        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, SectionPlans)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached article plan", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🔄 Creating new article plan...")
        try:
            result = await Runner.run(planner_agent, input=self.config.title, context=self.config)
            section_plans_output = result.final_output_as(SectionPlans)
            self.data_manager.save_data(self.title_slug, phase_name, section_plans_output)
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

        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached research notes", is_done=True)
            return loaded_data

        num_sections = len(section_plans.section_plans)
        self.printer.update_item(phase_name, f"🔄 Researching {num_sections} sections...")
        
        # Log section details for debugging
        section_ids = [str(plan.section_id) for plan in section_plans.section_plans]
        self.printer.update_item("section_debug", f"📋 Processing sections: {', '.join(section_ids)}", is_done=True, hide_checkmark=True)
        
        if app_config.RESEARCH_STRATEGY == "batch":
            # Original batch approach - research all sections at once
            self.printer.update_item("research_strategy", "📚 Using batch research strategy", is_done=True, hide_checkmark=True)
            try:
                result = await Runner.run(research_agent, input=section_plans.model_dump_json(), context=self.config, max_turns=100)
                research_notes_output = result.final_output_as(ResearchNotes)
                
                # Validate research completeness
                researched_section_ids = [note.section_id for note in research_notes_output.notes_by_section]
                expected_section_ids = [str(plan.section_id) for plan in section_plans.section_plans]
                
                missing_sections = set(expected_section_ids) - set(researched_section_ids)
                if missing_sections:
                    self.printer.update_item("research_warning", f"⚠️ Missing research for sections: {', '.join(missing_sections)}", is_done=True, hide_checkmark=True)
                
                # Detailed completion report
                sections_with_findings = sum(1 for note in research_notes_output.notes_by_section if note.findings)
                sections_without_findings = len(research_notes_output.notes_by_section) - sections_with_findings
                
                self.data_manager.save_data(self.title_slug, phase_name, research_notes_output)
                self.printer.update_item(
                    phase_name,
                    f"✅ Research complete - {len(research_notes_output.notes_by_section)} sections processed, {sections_with_findings} with findings, {sections_without_findings} without findings",
                    is_done=True,
                )
                
                if sections_without_findings > 0:
                    self.printer.update_item("research_gaps", f"⚠️ {sections_without_findings} sections have no research findings", is_done=True, hide_checkmark=True)
                
                return research_notes_output
            except ValueError as e:
                if "Invalid JSON" in str(e):
                    self.printer.update_item(phase_name, f"❌ Research failed: Agent returned invalid JSON format. Error: {str(e)}", is_done=True)
                    self.printer.update_item("json_error_help", "💡 The research agent needs to return valid JSON. Try running again.", is_done=True, hide_checkmark=True)
                else:
                    self.printer.update_item(phase_name, f"❌ Research failed: {str(e)}", is_done=True)
                return None
            except Exception as e:
                self.printer.update_item(phase_name, f"❌ Research failed: {str(e)}", is_done=True)
                return None
        else:
            # Individual approach - research sections one by one (default and more reliable)
            self.printer.update_item("research_strategy", "🔍 Using individual section research strategy (recommended)", is_done=True, hide_checkmark=True)
            
            # Import section-specific agent for even better reliability
            from app.agents.section_research_agent import agent as section_research_agent
            
            all_section_notes = []
            sections_with_findings = 0
            sections_without_findings = 0
            failed_sections = []
            
            for i, section_plan in enumerate(section_plans.section_plans):
                section_id_str = str(section_plan.section_id)
                self.printer.update_item(f"research_section_{section_id_str}", f"🔍 Researching section {i+1}/{num_sections}: {section_plan.title}...", is_done=False)
                
                retry_count = 0
                max_retries = app_config.RESEARCH_MAX_RETRIES
                section_researched = False
                current_section_plan = section_plan
                
                while retry_count <= max_retries and not section_researched:
                    try:
                        # Use the section-specific agent for single section research
                        result = await Runner.run(
                            section_research_agent, 
                            input=current_section_plan.model_dump_json(),
                            context=self.config, 
                            max_turns=15  # Focused turns for single section
                        )
                        section_note = result.final_output_as(SectionResearchNotes)
                        
                        if section_note:
                            all_section_notes.append(section_note)
                            section_researched = True
                            
                            if section_note.findings:
                                sections_with_findings += 1
                                self.printer.update_item(f"research_section_{section_id_str}", f"✅ Section {i+1}: Found {len(section_note.findings)} sources", is_done=True, hide_checkmark=True)
                            else:
                                sections_without_findings += 1
                                self.printer.update_item(f"research_section_{section_id_str}", f"⚠️ Section {i+1}: No findings (no queries or search failed)", is_done=True, hide_checkmark=True)
                        else:
                            raise ValueError("No research notes returned for section")
                            
                    except Exception as e:
                        retry_count += 1
                        if retry_count <= max_retries:
                            # Try research recovery before final retry
                            if retry_count == max_retries:
                                self.printer.update_item(f"research_section_{section_id_str}", f"🛠️ Section {i+1}: Attempting research recovery...", is_done=False)
                                current_section_plan = await self._attempt_research_recovery(current_section_plan, str(e))
                                if current_section_plan:
                                    self.printer.update_item(f"research_section_{section_id_str}", f"🔄 Section {i+1}: Final retry with improved queries", is_done=False)
                                else:
                                    # Recovery failed, proceed to final failure
                                    break
                            else:
                                self.printer.update_item(f"research_section_{section_id_str}", f"🔄 Section {i+1}: Retry {retry_count}/{max_retries} after error", is_done=False)
                        else:
                            # Final failure - handle individual section failure
                            sections_without_findings += 1
                            failed_sections.append(section_id_str)
                            self.printer.update_item(f"research_section_{section_id_str}", f"❌ Section {i+1}: Failed after {max_retries} retries and recovery attempt", is_done=True, hide_checkmark=True)
                            
                            # Create empty notes for failed section
                            empty_note = SectionResearchNotes(
                                section_id=section_id_str,
                                findings=[],
                                summary=f"Research failed after {max_retries} retries and recovery attempt: {str(e)[:100]}"
                            )
                            all_section_notes.append(empty_note)
                            section_researched = True  # Move to next section
            
            # Create the final ResearchNotes object
            try:
                final_research_notes = ResearchNotes(notes_by_section=all_section_notes)
                
                # Save the research notes
                self.data_manager.save_data(self.title_slug, phase_name, final_research_notes)
                
                # Summary message
                self.printer.update_item(
                    phase_name,
                    f"✅ Research complete - {len(all_section_notes)} sections processed, {sections_with_findings} with findings, {sections_without_findings} without findings",
                    is_done=True,
                )
                
                if failed_sections:
                    self.printer.update_item("research_failures", f"⚠️ Failed sections: {', '.join(failed_sections)}", is_done=True, hide_checkmark=True)
                
                return final_research_notes
                
            except Exception as e:
                self.printer.update_item(phase_name, f"❌ Research compilation failed: {str(e)}", is_done=True)
                return None

    async def _scrape_web_content(self, original_research_notes: ResearchNotes | None) -> ResearchNotes | None:
        phase_name = "scrape_web_content"

        if not original_research_notes:
            self.printer.update_item(phase_name, "⏭️ Skipped - no research notes available", is_done=True)
            return None

        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, ResearchNotes)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached scraped content", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🔄 Analyzing URLs for scraping...")

        # Extract URLs and check if any exist
        urls_to_scrape = self.web_scraping_service._extract_urls_from_research(original_research_notes)
        
        if not urls_to_scrape:
            self.printer.update_item(phase_name, "⚠️ No URLs found to scrape - using original notes", is_done=True)
            self.data_manager.save_data(self.title_slug, phase_name, original_research_notes)
            return original_research_notes
        
        self.printer.update_item(phase_name, f"🌐 Scraping {len(urls_to_scrape)} unique URLs...")

        try:
            # Use the web scraping service to extract and scrape URLs
            notes_to_augment = await self.web_scraping_service.extract_and_scrape_urls(original_research_notes)
            
            if notes_to_augment:
                self.data_manager.save_data(self.title_slug, phase_name, notes_to_augment)
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

        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, SythesizedArticle)
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

            self.data_manager.save_data(self.title_slug, phase_name, final_article)
            
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

        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, FinalArticle)
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
                input=json.dumps(agent_input, indent=2),
                context=self.config
            )
            final_article_output = result.final_output_as(FinalArticle)
            
            self.data_manager.save_data(self.title_slug, phase_name, final_article_output)
            
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

        loaded_data = self.data_manager.load_data(self.title_slug, phase_name, FinalArticleWithGemini)
        if loaded_data:
            self.printer.update_item(phase_name, "📁 Using cached Gemini enhanced article", is_done=True)
            return loaded_data

        self.printer.update_item(phase_name, "🤖 Enhancing article with Gemini...")
        
        try:
            enhanced_markdown = await asyncio.to_thread(
                gemini_enhancer.generate, 
                final_article.full_text_markdown,
                self.config.title,      # Pass title
                self.config.description, # Pass description
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
            
            self.data_manager.save_data(self.title_slug, phase_name, gemini_article_output)
            
            self.printer.update_item(
                phase_name,
                "✅ Gemini enhancement complete",
                is_done=True,
            )
            return gemini_article_output

        except Exception as e:
            self.printer.update_item(phase_name, f"❌ Gemini enhancement failed: {str(e)}", is_done=True)
            return None

    async def _attempt_research_recovery(self, failed_section_plan: any, failure_reason: str) -> any:
        """
        Attempt to recover from failed research by analyzing the section plan and generating improved queries.
        
        Args:
            failed_section_plan: The section plan that failed research
            failure_reason: The error message explaining why research failed
            
        Returns:
            Improved section plan with new queries, or None if recovery fails
        """
        try:
            # Prepare input for recovery agent
            recovery_input = {
                "section_id": failed_section_plan.section_id,
                "title": failed_section_plan.title,
                "key_points": failed_section_plan.key_points,
                "research_queries": getattr(failed_section_plan, 'research_queries', None),
                "failure_reason": failure_reason
            }
            
            # Run recovery agent
            result = await Runner.run(
                research_recovery_agent,
                input=json.dumps(recovery_input, indent=2),
                context=self.config,
                max_turns=5  # Quick recovery process
            )
            
            # Get improved section plan
            from app.agents.research_recovery_agent import ImprovedSectionPlan
            improved_plan = result.final_output_as(ImprovedSectionPlan)
            
            if improved_plan and improved_plan.research_queries:
                # Convert back to original SectionPlan format
                from app.models.article_schemas import SectionPlan
                recovered_plan = SectionPlan(
                    section_id=improved_plan.section_id,
                    title=improved_plan.title,
                    key_points=improved_plan.key_points,
                    research_queries=improved_plan.research_queries
                )
                
                # Log the recovery attempt
                section_id_str = str(failed_section_plan.section_id)
                self.printer.update_item(
                    f"recovery_{section_id_str}", 
                    f"🔧 Recovery: Generated {len(improved_plan.research_queries)} new queries - {improved_plan.improvement_rationale[:100]}...", 
                    is_done=True, 
                    hide_checkmark=True
                )
                
                return recovered_plan
            else:
                return None
                
        except Exception as e:
            section_id_str = str(failed_section_plan.section_id)
            self.printer.update_item(
                f"recovery_failed_{section_id_str}", 
                f"❌ Recovery failed: {str(e)[:100]}", 
                is_done=True, 
                hide_checkmark=True
            )
            return None


def _read_multiline_input(prompt: str) -> str:
    """Reads multiline input from the console until an empty line is entered."""
    print(prompt)
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)

if __name__ == "__main__":
    config = ArticleCreationWorkflowConfig(
        title=input("Enter the article title: "),
        description=_read_multiline_input("Enter the article description (end with an empty line):"),
        article_layout=_read_multiline_input("Enter the article layout (leave empty for auto-generated layout, end with an empty line):"),
        wordcount=int(input("Enter the target word count: "))
    )
    workflow = ArticleCreationWorkflow(config)
    asyncio.run(workflow.run())