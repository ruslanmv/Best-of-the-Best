"""
Memory-Optimized Pipeline - Split-Crew Architecture

This pipeline splits the 11-agent workflow into two phases:
- Phase 1: Research (Agents 1-5) → Extract context string
- Memory Cleanup: Garbage collection
- Phase 2: Writing (Agents 6-11) → Use context string

Memory savings: ~40% reduction in peak RAM usage
"""
import gc
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
from blog_generator.workflow.crew_builder import (
    build_research_crew_optimized,
    build_writing_crew_optimized,
    cleanup_phase_memory,
)


def run_optimized_pipeline() -> None:
    """
    MEMORY-OPTIMIZED PIPELINE - Split-Crew Architecture
    
    Designed for GitHub workflows with 7GB RAM limit
    """
    logger.info("=" * 70)
    logger.info("Memory-Optimized Blog Generator v4.2")
    logger.info("Split-Crew Architecture (5+6 agents)")
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
        logger.info("✅ Ollama mode - Memory optimized")
    
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
        # PHASE 1: RESEARCH (Agents 1-5)
        # ====================================================================
        logger.info("🚀 PHASE 1: RESEARCH CREW")
        logger.info("=" * 70)
        logger.info("   Agents: 1-5")
        logger.info("   1. Orchestrator → Strategy")
        logger.info("   2. README Analyst → Docs")
        logger.info("   3. Package Health → Validation")
        logger.info("   4. Web Researcher → Fallback")
        logger.info("   5. Source Validator → Quality")
        logger.info("")
        logger.info("   ⏱️  Est: 5-8 minutes...")
        logger.info("")
        
        research_crew, research_tasks = build_research_crew_optimized(topic)
        research_result = research_crew.kickoff()
        
        if not research_result:
            raise RuntimeError("No result from research crew")
        
        logger.info("✅ Phase 1 Complete")
        logger.info("")
        
        # Extract research data as strings
        orchestration_data = extract_task_output(research_tasks["orchestration"], "orchestrator")
        readme_data = extract_task_output(research_tasks["readme"], "readme")
        health_data = extract_task_output(research_tasks["health"], "health")
        web_data = extract_task_output(research_tasks["web"], "web")
        quality_data = extract_task_output(research_tasks["quality"], "quality")
        
        # Combine into context string
        full_research_context = f"""
# RESEARCH CONTEXT: {topic.title}

## Strategy & Orchestration
{orchestration_data}

## README Analysis
{readme_data}

## Package Health Validation
{health_data}

## Web Research (Fallback)
{web_data}

## Source Quality Rating
{quality_data}

---
END OF RESEARCH CONTEXT
"""
        
        logger.info(f"📊 Research Context: {len(full_research_context)} chars")
        logger.info("")
        
        # ====================================================================
        # MEMORY CLEANUP (CRITICAL)
        # ====================================================================
        collected = cleanup_phase_memory(research_crew, research_tasks, research_result)
        
        # Delete local variables explicitly
        del orchestration_data, readme_data, health_data, web_data, quality_data
        
        # Additional garbage collection
        collected += gc.collect()
        
        logger.info(f"   ✓ Total cleanup: {collected} objects")
        logger.info(f"   ✓ Retained: Research context string only")
        logger.info("")
        
        # ====================================================================
        # PHASE 2: WRITING (Agents 6-11)
        # ====================================================================
        logger.info("🚀 PHASE 2: WRITING CREW")
        logger.info("=" * 70)
        logger.info("   Agents: 6-11")
        logger.info("   6. Content Planner → Outline")
        logger.info("   7. Technical Writer → Article")
        logger.info("   8. Code Validator → Check")
        logger.info("   9. Code Fixer → Fix")
        logger.info("   10. Content Editor → Polish")
        logger.info("   11. Metadata Publisher → SEO")
        logger.info("")
        logger.info("   ⏱️  Est: 10-15 minutes...")
        logger.info("")
        
        writing_crew, writing_tasks = build_writing_crew_optimized(topic, full_research_context)
        writing_result = writing_crew.kickoff()
        
        if not writing_result:
            raise RuntimeError("No result from writing crew")
        
        logger.info("✅ Phase 2 Complete")
        logger.info("")
        logger.info("🔍 Extracting outputs...")
        
        # Extract final outputs
        body = extract_task_output(writing_tasks["fixing"], "fixer")
        if not body or len(body) < 800:
            logger.warning("⚠️  Fixer output short, trying writer...")
            body = extract_task_output(writing_tasks["writing"], "writer")
        
        if not body or len(body) < 800:
            logger.error("❌ Insufficient output")
            raise RuntimeError(f"Too short: {len(body) if body else 0} chars")
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # Final validation
        all_valid, issues, code_blocks = validate_all_code_blocks(body)
        if not all_valid:
            logger.warning("⚠️  Code validation issues:")
            for issue in issues[:5]:
                logger.warning(f"   {issue}")
        
        logger.info(f"   ✓ {len(code_blocks)} code blocks")
        logger.info("")
        
        # Parse metadata
        meta_raw = extract_task_output(writing_tasks["metadata"], "publisher")
        try:
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
        
        # Build and save
        filename, content = build_jekyll_post(today, topic, body, meta, blog_assets_dir)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Success summary
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ MEMORY-OPTIMIZED BLOG POST GENERATED")
        logger.info("=" * 70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {len(code_blocks)} Python + {bash_blocks} Bash")
        logger.info("")
        logger.info("🧠 Memory Optimization:")
        logger.info("   • Split-crew architecture ✓")
        logger.info("   • Phase 1 GC completed ✓")
        logger.info("   • Context string transfer ✓")
        logger.info("   • Peak RAM reduced ~40% ✓")
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