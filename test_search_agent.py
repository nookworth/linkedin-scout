#!/usr/bin/env python3
"""
Quick test script to see what the SearchAgent generates
"""

import asyncio
from src.linkedin_scout.agents.search_agent import SearchAgent
from src.linkedin_scout.types import SearchCriteria, AIConfig, ConnectionDegree


async def test_search_agent():
    """Test the SearchAgent with your example criteria"""
    
    # Set up AI config - using available model
    ai_config = AIConfig(
        model="qwen2.5vl:7b",
        endpoint="http://localhost:11434",
        temperature=0.1,
        max_tokens=1000,
        timeout=30
    )
    
    # Create search agent
    agent = SearchAgent(ai_config)
    
    # Create your test criteria
    criteria = SearchCriteria(
        name="test-search",
        companies=["Anduril", "Anthropic", "Figma"],
        job_titles=["software engineer", "engineering manager", "recruiter"],
        connection_degree=ConnectionDegree.SECOND
    )
    
    print("Testing SearchAgent with criteria:")
    print(f"Companies: {criteria.companies}")
    print(f"Job titles: {criteria.job_titles}")
    print(f"Connection degree: {criteria.connection_degree}")
    print("\n" + "="*50 + "\n")
    
    try:
        # Test the optimize_search_query function
        result = await agent.optimize_search_query(criteria)
        
        if result.success:
            print("✅ SearchAgent generated query successfully!")
            print(f"Model used: {result.metadata.get('model', 'unknown')}")
            print("\nGenerated output:")
            print("-" * 30)
            
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    print(f"{key}: {value}")
            else:
                print(result.data)
                
        else:
            print("❌ SearchAgent failed:")
            print(f"Error: {result.error}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        print("Make sure Ollama is running with the llama3.2:3b model")


if __name__ == "__main__":
    asyncio.run(test_search_agent())