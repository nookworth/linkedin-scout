"""
Company Search Controller - Orchestrates company-based LinkedIn searches
"""

import asyncio
from typing import List, Dict, Any
from linkedin_scout.browser import CompanyNavigator
from linkedin_scout.agents.search_agent import ProfileEvaluator
from linkedin_scout.types import BrowserConfig, AIConfig, SearchCriteria, Contact
import logging

logger = logging.getLogger(__name__)


class CompanySearchController:
    """Orchestrates LinkedIn searches using company → people → filter approach"""
    
    def __init__(self, browser_config: BrowserConfig, ai_config: AIConfig):
        self.browser_config = browser_config
        self.ai_config = ai_config
        self.profile_evaluator = ProfileEvaluator(ai_config)
        
    async def search_companies(
        self, 
        companies: List[str],
        job_titles: List[str],
        criteria: SearchCriteria,
        user_context: Dict[str, Any] = None,
        results_per_company: int = 20,
        total_limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for contacts across multiple companies
        
        Args:
            companies: List of company names to search
            job_titles: List of job titles to filter by
            criteria: Search criteria object
            user_context: User background info for relevance scoring
            results_per_company: Max results per company
            total_limit: Overall result limit
            
        Returns:
            List of qualified contacts with justifications
        """
        all_contacts = []
        user_context = user_context or {}
        
        async with CompanyNavigator(self.browser_config) as navigator:
            
            for company in companies:
                logger.info(f"Searching company: {company}")
                
                # Check if we've hit total limit
                if len(all_contacts) >= total_limit:
                    break
                    
                try:
                    company_contacts = await self._search_single_company(
                        navigator=navigator,
                        company=company,
                        job_titles=job_titles,
                        criteria=criteria,
                        user_context=user_context,
                        limit=min(results_per_company, total_limit - len(all_contacts))
                    )
                    
                    all_contacts.extend(company_contacts)
                    logger.info(f"Found {len(company_contacts)} contacts at {company}")
                    
                    # Rate limiting between companies
                    if len(companies) > 1:
                        await asyncio.sleep(self.browser_config.rate_limit_delay / 1000)
                        
                except Exception as e:
                    logger.error(f"Failed to search {company}: {e}")
                    continue
                    
        logger.info(f"Search completed. Total contacts found: {len(all_contacts)}")
        return all_contacts[:total_limit]
        
    async def _search_single_company(
        self,
        navigator: CompanyNavigator,
        company: str,
        job_titles: List[str],
        criteria: SearchCriteria,
        user_context: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search a single company for relevant contacts"""
        
        company_contacts = []
        
        # Navigate to company people page
        if not await navigator.navigate_to_company_people(company):
            logger.warning(f"Could not navigate to {company} people page")
            return company_contacts
            
        # Search each job title
        for job_title in job_titles:
            if len(company_contacts) >= limit:
                break
                
            try:
                logger.info(f"Filtering by job title: {job_title}")
                
                # Apply job title filter
                await navigator.filter_by_job_title(job_title)
                
                # Extract profiles
                remaining_limit = limit - len(company_contacts)
                raw_profiles = await navigator.extract_profiles(remaining_limit)
                
                # Evaluate and filter profiles using AI
                qualified_profiles = await self._evaluate_profiles(
                    raw_profiles=raw_profiles,
                    criteria=criteria,
                    user_context=user_context,
                    company=company
                )
                
                company_contacts.extend(qualified_profiles)
                logger.info(f"Found {len(qualified_profiles)} qualified profiles for {job_title}")
                
            except Exception as e:
                logger.error(f"Failed to process {job_title} at {company}: {e}")
                continue
                
        return company_contacts
        
    async def _evaluate_profiles(
        self,
        raw_profiles: List[Dict[str, Any]],
        criteria: SearchCriteria,
        user_context: Dict[str, Any],
        company: str
    ) -> List[Dict[str, Any]]:
        """Use AI to evaluate and filter profiles"""
        
        qualified_contacts = []
        
        for profile in raw_profiles:
            try:
                # Add company context to profile
                profile['company'] = company
                
                # Evaluate profile using AI
                evaluation_result = await self.profile_evaluator.evaluate_profile(
                    profile=profile,
                    criteria=criteria,
                    user_context=user_context
                )
                
                if not evaluation_result.success:
                    logger.warning(f"Profile evaluation failed: {evaluation_result.error}")
                    continue
                    
                evaluation_data = evaluation_result.data
                
                # Check if profile should be included
                if evaluation_data.get('should_include', False):
                    
                    # Generate justification
                    justification_result = await self.profile_evaluator.generate_justification(
                        profile=profile,
                        evaluation=evaluation_data,
                        user_context=user_context
                    )
                    
                    # Prepare final contact record
                    contact = {
                        'name': profile.get('name'),
                        'title': profile.get('title'),
                        'company': company,
                        'location': profile.get('location'),
                        'profile_url': profile.get('profile_url'),
                        'relevance_score': evaluation_data.get('relevance_score', 0.5),
                        'matching_criteria': evaluation_data.get('matching_criteria', []),
                        'reasons': evaluation_data.get('reasons', []),
                        'potential_connection_points': evaluation_data.get('potential_connection_points', [])
                    }
                    
                    # Add justification if available
                    if justification_result.success:
                        justification_data = justification_result.data
                        if isinstance(justification_data, str):
                            contact['justification'] = justification_data
                        else:
                            contact['justification'] = justification_data.get('justification', 'Qualified match')
                            contact['connection_angle'] = justification_data.get('connection_angle', 'Professional networking')
                    else:
                        contact['justification'] = f"Matches {', '.join(evaluation_data.get('matching_criteria', ['criteria']))}"
                        
                    qualified_contacts.append(contact)
                    
            except Exception as e:
                logger.error(f"Failed to evaluate profile: {e}")
                continue
                
        return qualified_contacts
        
    async def expand_similar_companies(self, companies: List[str], max_similar: int = 5) -> List[str]:
        """Use AI to suggest similar companies to search"""
        # This would use AI to expand the company list
        # For now, return original list
        # TODO: Implement company expansion using AI
        logger.info("Company expansion not yet implemented")
        return companies