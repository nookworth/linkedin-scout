import json
from typing import Dict, List, Any, Optional
from linkedin_scout.agents.base import BaseAgent
from linkedin_scout.types import AIResponse, SearchCriteria, Contact


class ProfileEvaluator(BaseAgent):
    """AI agent for evaluating LinkedIn profiles against search criteria"""
    
    async def process(self, input_data: Dict[str, Any]) -> AIResponse:
        """Process profile data to evaluate relevance"""
        if "profile" not in input_data or "criteria" not in input_data:
            return AIResponse(
                success=False,
                error="Missing 'profile' or 'criteria' in input data"
            )
            
        profile = input_data["profile"]
        criteria: SearchCriteria = input_data["criteria"]
        user_context = input_data.get("user_context", {})
        
        return await self.evaluate_profile(profile, criteria, user_context)
    
    async def evaluate_profile(self, profile: Dict[str, Any], criteria: SearchCriteria, user_context: Dict[str, Any]) -> AIResponse:
        """Evaluate if a LinkedIn profile matches search criteria and user context"""
        
        system_prompt = """You are an expert at evaluating LinkedIn profiles for networking potential. 
Analyze the profile against the search criteria and user context to determine relevance.

Return your response as valid JSON:
{
    "should_include": true/false,
    "relevance_score": 0.0-1.0,
    "matching_criteria": ["criterion1", "criterion2"],
    "reasons": ["reason1", "reason2"],
    "potential_connection_points": ["shared experience", "complementary skills"]
}"""

        context = {
            "profile_name": profile.get("name", "Unknown"),
            "profile_title": profile.get("title", "Unknown"),
            "profile_company": profile.get("company", "Unknown"),
            "profile_location": profile.get("location", "Unknown"),
            "profile_summary": profile.get("summary", ""),
            "target_companies": criteria.companies or [],
            "target_job_titles": criteria.job_titles or [],
            "target_keywords": criteria.keywords or [],
            "exclude_keywords": criteria.exclude_keywords or [],
            "user_background": user_context.get("background", ""),
            "user_interests": user_context.get("interests", []),
            "user_current_role": user_context.get("current_role", "")
        }
        
        prompt = self._create_structured_prompt(
            task="Evaluate LinkedIn profile for networking relevance",
            context=context,
            format_instructions="Analyze this profile against the search criteria and user context. Consider job title match, company relevance, shared background, and networking potential. Be selective - only include profiles with strong potential for meaningful connections."
        )
        
        response = await self.generate(prompt, system_prompt)
        
        if response.success:
            try:
                parsed_data = json.loads(response.data)
                return AIResponse(
                    success=True,
                    data=parsed_data,
                    metadata=response.metadata
                )
            except json.JSONDecodeError:
                # Fallback with basic evaluation
                return AIResponse(
                    success=True,
                    data={
                        "should_include": True,
                        "relevance_score": 0.5,
                        "matching_criteria": ["basic match"],
                        "reasons": ["Could not parse detailed analysis"],
                        "potential_connection_points": ["Similar role"]
                    },
                    metadata=response.metadata
                )
        
        return response
    
    async def generate_justification(self, profile: Dict[str, Any], evaluation: Dict[str, Any], user_context: Dict[str, Any]) -> AIResponse:
        """Generate a brief justification for why this profile should be included"""
        
        system_prompt = """You are writing brief, personalized justifications for LinkedIn connection requests.
Create a concise 1-2 sentence explanation of why this person would be a valuable connection.

Return as JSON:
{
    "justification": "Brief explanation of connection value",
    "connection_angle": "Specific reason for reaching out"
}"""

        context = {
            "profile_name": profile.get("name", "Unknown"),
            "profile_title": profile.get("title", "Unknown"),
            "profile_company": profile.get("company", "Unknown"),
            "relevance_score": evaluation.get("relevance_score", 0.5),
            "matching_criteria": evaluation.get("matching_criteria", []),
            "potential_connection_points": evaluation.get("potential_connection_points", []),
            "user_current_role": user_context.get("current_role", ""),
            "user_interests": user_context.get("interests", [])
        }
        
        prompt = self._create_structured_prompt(
            task="Generate connection justification",
            context=context,
            format_instructions="Write a brief, specific justification for why this person would be valuable to connect with. Focus on mutual interests, complementary skills, or shared experiences."
        )
        
        return await self.generate(prompt, system_prompt)
    
