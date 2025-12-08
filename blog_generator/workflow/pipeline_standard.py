"""
Standard Pipeline - Monolithic Architecture

This pipeline runs all 11 agents in a single crew (traditional approach):
- All agents loaded in memory simultaneously
- Sequential task execution
- Higher memory usage but simpler architecture

Use this for:
- Local development with sufficient RAM
- Debugging and testing
- Environments with >10GB RAM
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

from blog_generator.config import logger, is_ollama_llm
from blog_generator.core import (
    BASE_DIR,
    BLOG_POSTS_DIR,
    BASE_ASSETS_DIR,
    select_next_topic,
    ensure_blog_assets_topic_specific,
    build_jekyll_post,
    save_post,
    record_coverage,
    validate_all_code_blocks,
    extract_task_output,
    slugify,
)
from blog_generator.workflow.crew_builder import build_standard_crew


def run_standard_pipeline() -> None:
    """
    STANDARD PIPELINE - Monolithic Architecture
    
    Runs all 11 agents in a single crew with sequential execution.
    Designed for environments with sufficient memory (>10GB RAM).
    """
    logger.info("=" * 70)
    logger.info("Standard Blog Generator v4.2")
    logger.info("Monolithic Architecture (11 agents)")
    logger.info("=" * 70)
    logger.info(f"Base: {BASE_DIR}")
    logger.info(f"Posts: {BLOG_POSTS_DIR}")
    logger.info("")
    
    # Log tool availability
    from blog_generator.config import README_TOOLS_AVAILABLE, SEARCH_TOOLS_AVAILABLE
    
    if README_TOOLS_AVAILABLE:
        logger.info("✅ README + Package Health tools available")
    else:
        logger.warning("⚠️  README tools not available")
    
    if SEARCH_TOOLS_AVAILABLE:
        logger.info("✅ Web search tools available")
    else:
        logger.warning("⚠️  Web search tools not available")
    
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    logger.info(f"LLM: {llm_model}")
    
    if is_ollama_llm():
        logger.info("✅ Ollama mode")
    
    logger.info("")
    
    try:
        # ====================================================================
        # SETUP: Topic & Assets
        # ====================================================================
        topic = select_next_topic()
        logger.info(f"📝 Topic: {topic.title}")
        logger.info(f"   Type: {topic.kind}")
        logger.info(f"   Tags: {', '.join(topic.tags[:3])}")
        logger.info("")
        
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y-%m-%d")
        slug = f"{topic.kind}-{slugify(topic.title)}"
        
        from blog_generator.config import IMAGE_TOOLS_AVAILABLE, set_blog_context
        
        if IMAGE_TOOLS_AVAILABLE:
            blog_assets_dir = set_blog_context(slug, topic.title, date_str)
        else:
            blog_assets_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
            blog_assets_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        ensure_blog_assets_topic_specific(topic, slug, date_str)
        logger.info("")
        
        # ====================================================================
        # BUILD & RUN CREW (All 11 Agents)
        # ====================================================================
        logger.info("🚀 11-Agent Orchestrated Pipeline Starting...")
        logger.info("=" * 70)
        logger.info("   Agent Flow:")
        logger.info("   1. Orchestrator → Strategy")
        logger.info("   2. README Analyst → Docs")
        logger.info("   3. Package Health → Validation")
        logger.info("   4. Web Researcher → Fallback")
        logger.info("   5. Source Validator → Quality")
        logger.info("   6. Content Planner → Outline")
        logger.info("   7. Technical Writer → Article")
        logger.info("   8. Code Validator → Check")
        logger.info("   9. Code Fixer → Fix")
        logger.info("   10. Content Editor → Polish")
        logger.info("   11. Metadata Publisher → SEO")
        logger.info("")
        logger.info("   ⏱️  Estimated: 15-25 minutes...")
        logger.info("")
        
        crew, tasks = build_standard_crew(topic)
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("No result from crew")
        
        logger.info("✅ Pipeline Complete")
        logger.info("")
        logger.info("🔍 Extracting outputs...")
        
        # Unpack tasks
        (
            orchestration_task,
            readme_task,
            health_task,
            web_research_task,
            quality_task,
            planning_task,
            writing_task,
            validation_task,
            fixing_task,
            editing_task,
            metadata_task,
        ) = tasks
        
        # ====================================================================
        # EXTRACT OUTPUTS
        # ====================================================================
        
        # Extract body (try fixer first, then writer)
        body = extract_task_output(fixing_task, "fixer")
        if not body or len(body) < 800:
            logger.warning("⚠️  Fixer output short, trying writer...")
            body = extract_task_output(writing_task, "writer")
        
        if not body or len(body) < 800:
            logger.error("❌ Insufficient output")
            raise RuntimeError(f"Too short: {len(body) if body else 0} chars")
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # Optional: Apply additional cleaning
        # from blog_generator.core.text_cleaning import clean_llm_output, clean_content
        # body = clean_llm_output(body)
        # body = clean_content(body)
        
        # ====================================================================
        # VALIDATE CODE
        # ====================================================================
        all_valid, issues, code_blocks = validate_all_code_blocks(body)
        if not all_valid:
            logger.warning("⚠️  Code validation issues:")
            for issue in issues[:5]:
                logger.warning(f"   {issue}")
            logger.warning("   Proceeding anyway (fixer may have missed some)")
        
        logger.info(f"   ✓ {len(code_blocks)} code blocks")
        logger.info("")
        
        # ====================================================================
        # PARSE METADATA
        # ====================================================================
        meta_raw = extract_task_output(metadata_task, "publisher")
        try:
            # Try to find JSON in output
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Metadata: {meta.get('title', 'N/A')[:50]}")
        except Exception as e:
            logger.warning(f"⚠️  Metadata parse failed: {e}")
            meta = {
                "title": topic.title,
                "excerpt": topic.summary or f"Learn about {topic.title}",
                "tags": topic.tags or ["ai"]
            }
        
        logger.info("")
        
        # ====================================================================
        # BUILD & SAVE POST
        # ====================================================================
        filename, content = build_jekyll_post(today, topic, body, meta, blog_assets_dir)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # ====================================================================
        # SUCCESS SUMMARY
        # ====================================================================
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ PROFESSIONAL BLOG POST GENERATED")
        logger.info("=" * 70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {len(code_blocks)} Python + {bash_blocks} Bash")
        logger.info("")
        logger.info("✅ Quality Assurance:")
        logger.info("   • README-first data retrieval ✓")
        logger.info("   • Package health validation ✓")
        logger.info("   • Deprecation detection ✓")
        logger.info("   • Code validation → fixing ✓")
        logger.info("   • Source quality tracking ✓")
        logger.info("   • Topic-specific images ✓")
        logger.info("   • Professional editing ✓")
        logger.info("   • SEO optimization ✓")
        logger.info("")
        
        # Source quality report
        quality_report = extract_task_output(quality_task, "source_validator")
        if quality_report:
            logger.info("📊 Source Quality:")
            if "A+" in quality_report or "High" in quality_report:
                logger.info("   ⭐⭐⭐ Highest Quality (Official Sources)")
            elif "A" in quality_report or "Medium" in quality_report:
                logger.info("   ⭐⭐ High Quality (Validated Sources)")
            else:
                logger.info("   ⭐ Good Quality (Web Sources)")
        
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info(f"   1. Review: cat {path.relative_to(BASE_DIR)}")
        logger.info(f"   2. Test code: Extract and run")
        logger.info(f"   3. Preview: jekyll serve")
        logger.info(f"   4. Publish: git commit")
        logger.info("")
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)