"""
PDF Form Parser Service
Extracts form fields from existing PDF files (created with Adobe Acrobat)
"""

from PyPDF2 import PdfReader
from typing import Dict, List, Optional
import json


class PDFParser:
    """
    Service for parsing PDF form fields and converting to template JSON
    """
    
    def __init__(self):
        """Initialize PDF parser"""
        pass
    
    def parse_pdf_form(self, pdf_file_path: str) -> Dict:
        """
        Parse PDF form fields and convert to template JSON format
        
        Args:
            pdf_file_path: Path to PDF file or file bytes
            
        Returns:
            dict: Template JSON compatible with the designer
        """
        try:
            reader = PdfReader(pdf_file_path)
            
            # Get form fields
            if reader.get_form_text_fields() is None and not hasattr(reader, 'get_fields'):
                return {
                    "error": "No form fields found in PDF",
                    "message": "This PDF does not contain fillable form fields"
                }
            
            # Extract fields
            fields = []
            form_fields = reader.get_form_text_fields() or {}
            
            # Get page size
            first_page = reader.pages[0]
            page_width = float(first_page.mediabox.width)
            page_height = float(first_page.mediabox.height)
            
            # Try to get field annotations
            if '/Annots' in first_page:
                annotations = first_page['/Annots']
                
                for annotation in annotations:
                    try:
                        field_obj = annotation.get_object()
                        
                        # Check if it's a form field
                        if '/T' in field_obj:  # Field name
                            field_name = str(field_obj['/T'])
                            
                            # Get field rectangle (position and size)
                            if '/Rect' in field_obj:
                                rect = field_obj['/Rect']
                                x = float(rect[0])
                                y_bottom = float(rect[1])
                                width = float(rect[2]) - x
                                height = float(rect[3]) - y_bottom
                                
                                # Convert PDF coordinates (bottom-left origin) to our coordinates (top-left origin)
                                y = page_height - float(rect[3])
                                
                                # Determine field type
                                field_type = 'text'
                                if '/FT' in field_obj:
                                    ft = str(field_obj['/FT'])
                                    if ft == '/Tx':
                                        field_type = 'text'
                                    elif ft == '/Ch':
                                        field_type = 'select'
                                    elif ft == '/Btn':
                                        field_type = 'checkbox'
                                
                                # Get font size if available
                                font_size = 12
                                if '/DA' in field_obj:
                                    da = str(field_obj['/DA'])
                                    # Try to extract font size from DA string
                                    parts = da.split()
                                    for i, part in enumerate(parts):
                                        if part == 'Tf' and i > 0:
                                            try:
                                                font_size = float(parts[i-1])
                                            except:
                                                pass
                                
                                fields.append({
                                    "name": field_name.replace(' ', '_').lower(),
                                    "type": field_type,
                                    "label": field_name,
                                    "x": round(x),
                                    "y": round(y),
                                    "width": round(width),
                                    "height": round(height),
                                    "fontSize": round(font_size),
                                    "fontWeight": "normal",
                                    "fontFamily": "Arial"
                                })
                    except Exception as e:
                        print(f"Error parsing field: {e}")
                        continue
            
            # If no annotations found, try alternative method
            if not fields and form_fields:
                # Fallback: create fields with default positions
                y_pos = 100
                for field_name, field_value in form_fields.items():
                    fields.append({
                        "name": field_name.replace(' ', '_').lower(),
                        "type": "text",
                        "label": field_name,
                        "x": 50,
                        "y": y_pos,
                        "width": 200,
                        "height": 20,
                        "fontSize": 12,
                        "fontWeight": "normal",
                        "fontFamily": "Arial"
                    })
                    y_pos += 40
            
            template = {
                "name": "Imported PDF Template",
                "description": f"Imported from PDF with {len(fields)} fields",
                "fields": fields,
                "pageWidth": round(page_width),
                "pageHeight": round(page_height)
            }
            
            return template
            
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to parse PDF file"
            }
    
    def extract_field_names(self, pdf_file_path: str) -> List[str]:
        """
        Extract just the field names from a PDF
        
        Args:
            pdf_file_path: Path to PDF file
            
        Returns:
            list: List of field names
        """
        try:
            reader = PdfReader(pdf_file_path)
            form_fields = reader.get_form_text_fields() or {}
            return list(form_fields.keys())
        except Exception as e:
            return []
