"""
LinkedIn Scout CLI - Main entry point for the command-line interface.
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ..utils.logging_config import setup_logging, get_logger, log_error_with_context

# Initialize logging
logger = setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=False,  # We'll use Rich for console output
    enable_file=True
)

from ..search.company_search_controller import CompanySearchController
from ..types import SearchOptions, AIConfig, BrowserConfig, Config
from ..export.json_exporter import JSONExporter
from ..utils.session_manager import SessionManager

console = Console()
cli_logger = get_logger("cli")
app = typer.Typer(
    name="linkedin-scout",
    help="AI-powered LinkedIn contact discovery tool",
    rich_markup_mode="rich"
)


@app.command()
def search(
    total_results: int = typer.Option(
        50,
        "--total-results",
        "-t",
        help="Total number of results to return across all companies"
    ),
    companies: str = typer.Option(
        "microsoft,google,apple,amazon,meta",
        "--companies",
        "-c",
        help="Comma-separated list of companies to search"
    ),
    results_per_company: int = typer.Option(
        20,
        "--results-per-company",
        "-r",
        help="Maximum number of results per company"
    ),
    job_titles: str = typer.Option(
        "software engineer,data scientist,product manager,engineering manager",
        "--job-titles",
        "-j",
        help="Comma-separated list of job titles to search for"
    ),
    match_conditions: str = typer.Option(
        "",
        "--match-conditions",
        "-m",
        help="Additional matching criteria (comma-separated keywords)"
    ),
    user_context: str = typer.Option(
        "",
        "--user-context",
        "-u",
        help="Personal context for AI evaluation (background, interests, etc.)"
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Output file path (defaults to generated filename)"
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run without actually searching LinkedIn (for testing)"
    )
) -> None:
    """
    Search LinkedIn for potential connections based on specified criteria.
    
    This command will:
    1. Navigate to specified company pages on LinkedIn
    2. Filter profiles by job titles
    3. Use AI to evaluate profile relevance
    4. Export results with justifications
    """
    try:
        cli_logger.info(f"Starting LinkedIn Scout search with {total_results} total results")
        
        # Parse input parameters
        companies_list = [c.strip() for c in companies.split(",") if c.strip()]
        job_titles_list = [j.strip() for j in job_titles.split(",") if j.strip()]
        match_conditions_list = [m.strip() for m in match_conditions.split(",") if m.strip()]
        
        cli_logger.info(f"Search parameters - Companies: {len(companies_list)}, Job titles: {len(job_titles_list)}")
        
        # Display search configuration
        console.print("\n[bold blue]LinkedIn Scout - Search Configuration[/bold blue]")
        
        config_table = Table()
        config_table.add_column("Parameter", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Total Results", str(total_results))
        config_table.add_row("Companies", ", ".join(companies_list))
        config_table.add_row("Results per Company", str(results_per_company))
        config_table.add_row("Job Titles", ", ".join(job_titles_list))
        config_table.add_row("Output Format", "JSON")
        config_table.add_row("Headless Browser", str(headless))
        config_table.add_row("Dry Run", str(dry_run))
        
        if match_conditions_list:
            config_table.add_row("Match Conditions", ", ".join(match_conditions_list))
        
        console.print(config_table)
        
        if dry_run:
            console.print("\n[yellow]Dry run mode - no actual LinkedIn searches will be performed[/yellow]")
            return
            
        # Check session and credentials before proceeding
        session_manager = SessionManager()
        session_info = session_manager.get_session_info()
        
        cli_logger.info(f"Session status - Valid: {session_info['has_valid_session']}, Credentials: {session_info['has_credentials']}")
        
        if not session_info["has_credentials"] and not session_info["has_valid_session"]:
            error_msg = "LinkedIn credentials not configured"
            cli_logger.error(error_msg)
            console.print("\n[red]❌ LinkedIn credentials not configured[/red]")
            console.print("Please create a .env file with your LinkedIn credentials:")
            console.print("LINKEDIN_EMAIL=your-email@example.com")
            console.print("LINKEDIN_PASSWORD=your-password")
            console.print("\nSee .env.example for a template.")
            return
        
        # Confirm execution
        if not typer.confirm("\nProceed with LinkedIn search?"):
            cli_logger.info("Search cancelled by user")
            console.print("[yellow]Search cancelled by user[/yellow]")
            return
            
        # Run the search
        console.print("\n[bold green]Starting LinkedIn search...[/bold green]")
        cli_logger.info("Beginning search execution")
        
        try:
            asyncio.run(_run_search(
                total_results=total_results,
                companies_list=companies_list,
                results_per_company=results_per_company,
                job_titles_list=job_titles_list,
                match_conditions_list=match_conditions_list,
                user_context=user_context,
                output_file=output_file,
                headless=headless
            ))
            cli_logger.info("Search completed successfully")
        except Exception as search_error:
            log_error_with_context(
                cli_logger, 
                search_error, 
                {
                    "companies": len(companies_list),
                    "total_results": total_results,
                    "headless": headless
                }
            )
            console.print(f"\n[red]❌ Search failed: {str(search_error)}[/red]")
            console.print("[yellow]Check logs for detailed error information[/yellow]")
            raise
        
    except KeyboardInterrupt:
        cli_logger.info("Search interrupted by user (Ctrl+C)")
        console.print("\n[yellow]Search interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        log_error_with_context(cli_logger, e, {"function": "search_command"})
        console.print(f"\n[red]❌ Unexpected error: {str(e)}[/red]")
        console.print("[yellow]Check logs for detailed error information[/yellow]")
        sys.exit(1)


async def _run_search(
    total_results: int,
    companies_list: List[str],
    results_per_company: int,
    job_titles_list: List[str],
    match_conditions_list: List[str],
    user_context: str,
    output_file: Optional[str],
    headless: bool
) -> None:
    """Execute the LinkedIn search with the specified parameters."""
    
    search_logger = get_logger("search")
    
    try:
        search_logger.info("Initializing search configuration")
        
        # Create configurations
        ai_config = AIConfig()
        browser_config = BrowserConfig(headless=headless)
        config = Config(ai=ai_config, browser=browser_config)
        
        search_logger.info(f"Configuration - AI model: {ai_config.model}, Headless: {headless}")
        
        # Create search options
        search_options = SearchOptions(
            companies=companies_list,
            limit=total_results,
            results_per_company=results_per_company,
            user_context={
                "background": user_context,
                "job_titles_of_interest": job_titles_list,
                "match_conditions": match_conditions_list
            }
        )
        
        search_logger.info(f"Search options created - {len(companies_list)} companies, {total_results} total results")
        
        # Initialize search controller
        search_logger.info("Initializing search controller")
        controller = CompanySearchController(config)
        
        try:
            search_logger.info("Starting LinkedIn profile search")
            with console.status("[bold green]Searching LinkedIn profiles..."):
                # Execute search
                results = await controller.search_companies(search_options)
                
            search_logger.info(f"Search completed - found {len(results)} profiles")
            console.print(f"\n[bold green]✅ Found {len(results)} matching profiles[/bold green]")
        
            # Export results to JSON
            if not output_file:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"linkedin_scout_results_{timestamp}.json"
            
            search_logger.info(f"Starting export to {output_file}")
            
            # Initialize JSON exporter and export results
            exporter = JSONExporter(config.export_dir)
            
            # Get justifications from results (if available)
            justifications = {}
            for contact in results:
                if hasattr(contact, 'justification') and contact.justification:
                    justifications[str(contact.profile_url)] = contact.justification
            
            search_logger.info(f"Exporting {len(results)} contacts with {len(justifications)} justifications")
            
            with console.status("[bold green]Exporting results..."):
                export_path = await exporter.export_contacts(
                    results, 
                    output_file, 
                    justifications
                )
            
            search_logger.info(f"Export completed successfully to {export_path}")
            console.print(f"[bold green]✅ Results exported to: {export_path}[/bold green]")
        
        # Display summary
        if results:
            results_table = Table()
            results_table.add_column("Name", style="cyan")
            results_table.add_column("Title", style="green")
            results_table.add_column("Company", style="blue")
            results_table.add_column("Score", style="yellow")
            
            for contact in results[:10]:  # Show first 10 results
                score = f"{contact.relevance_score:.2f}" if contact.relevance_score else "N/A"
                results_table.add_row(
                    contact.full_name,
                    contact.title or "N/A",
                    contact.company,
                    score
                )
            
            console.print("\n[bold]Sample Results:[/bold]")
            console.print(results_table)
            
            if len(results) > 10:
                console.print(f"[dim]... and {len(results) - 10} more results[/dim]")
        
        except Exception as search_error:
            log_error_with_context(
                search_logger,
                search_error,
                {
                    "companies": companies_list,
                    "total_results": total_results,
                    "output_file": output_file
                }
            )
            console.print(f"\n[red]❌ Search execution failed: {str(search_error)}[/red]")
            raise
        
        finally:
            # Cleanup
            search_logger.info("Cleaning up search resources")
            try:
                await controller.cleanup()
                search_logger.info("Cleanup completed successfully")
            except Exception as cleanup_error:
                search_logger.warning(f"Cleanup warning: {str(cleanup_error)}")
    
    except Exception as config_error:
        log_error_with_context(
            search_logger,
            config_error,
            {"function": "_run_search", "phase": "configuration"}
        )
        console.print(f"\n[red]❌ Configuration error: {str(config_error)}[/red]")
        raise


@app.command()
def version() -> None:
    """Show the current version of LinkedIn Scout."""
    console.print("[bold blue]LinkedIn Scout v1.0.0[/bold blue]")


@app.command()
def config() -> None:
    """Show current configuration settings."""
    config = Config()
    
    console.print("\n[bold blue]LinkedIn Scout - Configuration[/bold blue]")
    
    config_table = Table()
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("AI Model", config.ai.model)
    config_table.add_row("AI Endpoint", config.ai.endpoint)
    config_table.add_row("Database URL", config.database_url)
    config_table.add_row("Browser Headless", str(config.browser.headless))
    config_table.add_row("Export Directory", config.export_dir)
    
    console.print(config_table)


@app.command()
def session() -> None:
    """Show LinkedIn session status and authentication info."""
    session_manager = SessionManager()
    session_info = session_manager.get_session_info()
    
    console.print("\n[bold blue]LinkedIn Scout - Session Status[/bold blue]")
    
    session_table = Table()
    session_table.add_column("Setting", style="cyan")
    session_table.add_column("Status", style="green")
    
    # Session status
    status_icon = "✅" if session_info["has_valid_session"] else "❌"
    session_table.add_row("Valid Session", f"{status_icon} {session_info['has_valid_session']}")
    
    # Credentials status  
    creds_icon = "✅" if session_info["has_credentials"] else "❌"
    session_table.add_row("Has Credentials", f"{creds_icon} {session_info['has_credentials']}")
    
    # Storage state
    storage_icon = "✅" if session_info["storage_state_exists"] else "❌"
    session_table.add_row("Session File Exists", f"{storage_icon} {session_info['storage_state_exists']}")
    
    console.print(session_table)
    
    # Show guidance if issues found
    if not session_info["has_credentials"]:
        console.print("\n[yellow]⚠️ LinkedIn credentials not configured[/yellow]")
        console.print("Create a .env file with:")
        console.print("LINKEDIN_EMAIL=your-email@example.com")
        console.print("LINKEDIN_PASSWORD=your-password")
    
    if not session_info["has_valid_session"] and session_info["has_credentials"]:
        console.print("\n[yellow]⚠️ No valid session found[/yellow]")
        console.print("Run a search to establish a LinkedIn session")


@app.command()
def clear_session() -> None:
    """Clear saved LinkedIn session data."""
    session_manager = SessionManager()
    session_manager.clear_session()
    console.print("[green]✅ LinkedIn session data cleared[/green]")


if __name__ == "__main__":
    app()