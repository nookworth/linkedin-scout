"""
JSON Export functionality for LinkedIn Scout results.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..types import Contact
from ..utils.logging_config import get_logger, log_error_with_context
from ..utils.error_handling import with_error_handling, ExportError


class JSONExporter:
    """Handles exporting LinkedIn Scout results to JSON format."""
    
    def __init__(self, export_dir: str = "./exports"):
        """
        Initialize JSON exporter.
        
        Args:
            export_dir: Directory to save exported files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        self.logger = get_logger("export.json")
    
    @with_error_handling(exceptions=[ExportError])
    async def export_contacts(
        self, 
        contacts: List[Contact], 
        filename: Optional[str] = None,
        justifications: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Export contacts to JSON format with justifications.
        
        Args:
            contacts: List of Contact objects to export
            filename: Optional filename (will generate if not provided)
            justifications: Dictionary mapping contact profile URLs to justifications
            
        Returns:
            Path to the exported file
        """
        if not contacts:
            raise ExportError("No contacts provided for export")
            
        self.logger.info(f"Starting JSON export for {len(contacts)} contacts")
            
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_scout_results_{timestamp}.json"
        
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename += '.json'
            
        filepath = self.export_dir / filename
        
        # Prepare data for JSON export
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_contacts": len(contacts),
                "export_format": "JSON",
                "linkedin_scout_version": "1.0.0"
            },
            "contacts": []
        }
        
        for contact in contacts:
            contact_data = contact.dict()
            
            # Convert datetime objects to ISO strings
            if contact_data.get('created_at') and contact.created_at:
                contact_data['created_at'] = contact.created_at.isoformat()
            if contact_data.get('updated_at') and contact.updated_at:
                contact_data['updated_at'] = contact.updated_at.isoformat()
            
            # Add justification if available
            if justifications:
                contact_data['justification'] = justifications.get(str(contact.profile_url), "")
            else:
                contact_data['justification'] = ""
            
            export_data["contacts"].append(contact_data)
        
        try:
            # Write JSON file
            self.logger.info(f"Writing JSON export to {filepath}")
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"JSON export completed successfully: {filepath}")
            return str(filepath)
            
        except Exception as e:
            log_error_with_context(
                self.logger,
                e,
                {
                    "contacts_count": len(contacts),
                    "filename": filename,
                    "filepath": str(filepath)
                }
            )
            raise ExportError(f"Failed to write JSON export: {str(e)}")
    
    def get_export_stats(self, filepath: str) -> Dict[str, Any]:
        """
        Get statistics about an exported JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Dictionary with export statistics
        """
        if not os.path.exists(filepath):
            return {"error": "File not found"}
        
        file_size = os.path.getsize(filepath)
        modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Load and count contacts
        try:
            with open(filepath, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                contact_count = len(data.get('contacts', []))
        except Exception as e:
            return {"error": f"Failed to read JSON file: {str(e)}"}
        
        return {
            "filepath": filepath,
            "file_size_bytes": file_size,
            "contact_count": contact_count,
            "modified_at": modified_time.isoformat(),
            "format": "JSON"
        }