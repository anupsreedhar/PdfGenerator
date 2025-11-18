"""
PDF Form Parser Service
Extracts form fields from existing PDF files (created with Adobe Acrobat)
or extracts text content from regular PDF templates

Now supports LayoutLMv3 for advanced AI-powered parsing!
"""

from PyPDF2 import PdfReader
from typing import Dict, List, Optional
import json
import re
import os


class PDFParser:
    """
    Service for parsing PDF form fields and converting to template JSON
    
    Supports:
    1. Adobe Acrobat forms (form fields extraction)
    2. Static PDFs (text-based heuristics)
    3. LayoutLMv3 AI parsing (optional, more accurate)
    """
    
    def __init__(self, use_ai: bool = False):
        """
        Initialize PDF parser
        
        Args:
            use_ai: If True, attempt to use LayoutLMv3 for better accuracy
        """
        self.use_ai = use_ai
        self.ai_parser = None
        
        if use_ai:
            try:
                from services.layoutlmv3_parser import LayoutLMv3Parser
                self.ai_parser = LayoutLMv3Parser()
                print("✨ LayoutLMv3 AI parser enabled!")
            except ImportError as e:
                print(f"⚠️ LayoutLMv3 dependencies not installed: {e}")
                print("   Install with: pip install transformers torch pdf2image")
                print("   Falling back to basic parsing...")
                self.use_ai = False
            except Exception as e:
                print(f"⚠️ Failed to initialize LayoutLMv3: {e}")
                print("   Falling back to basic parsing...")
                self.use_ai = False
    
    def parse_pdf_form(self, pdf_file_path: str, use_ai: bool = None) -> Dict:
        """
        Parse PDF and convert to template JSON format
        
        Priority:
        1. Try LayoutLMv3 AI parsing (if enabled and available)
        2. Check for Adobe Acrobat form fields
        3. Fall back to text-based heuristic parsing
        
        Args:
            pdf_file_path: Path to PDF file or file bytes
            use_ai: Override instance setting for AI parsing
            
        Returns:
            dict: Template JSON compatible with the designer
        """
        # Determine if we should use AI
        should_use_ai = use_ai if use_ai is not None else self.use_ai
        
        # Try AI parsing first if enabled
        if should_use_ai and self.ai_parser:
            try:
                print("🤖 Using LayoutLMv3 AI parser...")
                result = self.ai_parser.parse_pdf(pdf_file_path)
                if result and "error" not in result:
                    return result
                print("⚠️ AI parsing failed, falling back to traditional methods")
            except Exception as e:
                print(f"⚠️ AI parsing error: {e}")
        
        # Traditional parsing
        try:
            reader = PdfReader(pdf_file_path)
            
            # Get page size
            first_page = reader.pages[0]
            page_width = float(first_page.mediabox.width)
            page_height = float(first_page.mediabox.height)
            
            # Try to get form fields first
            form_fields = reader.get_form_text_fields()
            has_form_fields = form_fields is not None and len(form_fields) > 0
            
            if has_form_fields or (hasattr(first_page, '__contains__') and '/Annots' in first_page):
                # PDF has form fields - parse them
                return self._parse_form_fields(reader, page_width, page_height)
            else:
                # Regular PDF template - extract text and create base template
                return self._parse_text_content(reader, page_width, page_height, pdf_file_path)
        
        except Exception as e:
            return {
                "error": "PDF parsing failed",
                "message": str(e)
            }
    
    def _parse_text_content(self, reader: PdfReader, page_width: float, page_height: float, pdf_file_path: str) -> Dict:
        """
        Parse regular PDF template (without form fields)
        
        For static templates (no form fields), we return minimal field detection
        and let the user manually add fields in the designer.
        """
        try:
            first_page = reader.pages[0]
            
            # Extract text from the PDF
            text_content = first_page.extract_text() or ""
            
            # Parse text into potential field labels
            lines = text_content.split('\n')
            fields = []
            
            # Detect table structures
            table_info = self._detect_tables_from_text(lines)
            
            # Look for EXPLICIT field indicators only (with colons followed by underscores or dots)
            # This avoids treating static labels as fields
            field_patterns = [
                r'^([A-Z][a-zA-Z\s]+):\s*_+\s*$',  # "Label: ______" - explicit field
                r'^([A-Z][a-zA-Z\s]+):\s*\.+\s*$',  # "Label: ....." - explicit field
                r'^([A-Z][a-zA-Z\s]+):\s*\[.*\]\s*$',  # "Label: [____]" - explicit field
            ]
            
            y_position = 50
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line matches explicit field patterns only
                field_name = None
                for pattern in field_patterns:
                    match = re.match(pattern, line)
                    if match:
                        field_name = match.group(1)
                        break
                
                if field_name:
                    # Create a field for this label
                    clean_name = field_name.lower().replace(' ', '_')
                    
                    # Determine field type based on label
                    field_type = 'text'
                    if any(keyword in field_name.lower() for keyword in ['date', 'birth', 'dob']):
                        field_type = 'date'
                    elif any(keyword in field_name.lower() for keyword in ['amount', 'total', 'price', 'quantity']):
                        field_type = 'number'
                    elif any(keyword in field_name.lower() for keyword in ['check', 'agree', 'confirm']):
                        field_type = 'checkbox'
                    
                    fields.append({
                        "name": clean_name,
                        "type": field_type,
                        "label": field_name,
                        "x": 100,
                        "y": y_position,
                        "width": 200,
                        "height": 20,
                        "fontSize": 12,
                        "fontWeight": "normal",
                        "fontFamily": "Helvetica"
                    })
                    
                    y_position += 40
            
            # Add detected tables
            if table_info['tables']:
                for idx, table in enumerate(table_info['tables']):
                    fields.append({
                        "name": f"table_{idx + 1}",
                        "type": "table",
                        "label": f"Table {idx + 1}",
                        "x": 50,
                        "y": table['y_position'],
                        "width": 500,
                        "height": table['height'],
                        "fontSize": 10,
                        "fontWeight": "normal",
                        "fontFamily": "Helvetica",
                        "tableRows": table['rows'],
                        "tableColumns": table['columns'],
                        "tableHeaders": table['headers'],
                        "cellWidth": 100,
                        "cellHeight": 25
                    })
            
            # Build message
            message_parts = []
            static_text_preview = []
            
            # Show first few lines of static text for reference
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) < 100:
                    static_text_preview.append(line)
            
            if fields:
                non_table_fields = [f for f in fields if f['type'] != 'table']
                table_fields = [f for f in fields if f['type'] == 'table']
                
                if non_table_fields:
                    message_parts.append(f"Found {len(non_table_fields)} explicit field(s)")
                if table_fields:
                    message_parts.append(f"Detected {len(table_fields)} potential table(s)")
                
                message = ". ".join(message_parts) + ".\n\nYou can adjust positions and add more fields in the designer."
            else:
                message = "📄 This appears to be a static template.\n\n"
                if static_text_preview:
                    message += "Text content detected:\n" + "\n".join(static_text_preview[:3]) + "\n\n"
                message += "ℹ️ No fillable fields found. Use the designer to:\n"
                message += "• Add Text/Number/Date fields where data should go\n"
                message += "• Add Tables for structured data\n"
                message += "• Add Images (if needed)\n\n"
                message += "💡 Tip: Static labels (like 'Table of Contents') don't need fields - they're already in your PDF!"
            
            # If no fields found, create a message
            if not fields:
                return {
                    "name": "Imported PDF Template",
                    "fields": [],
                    "pageWidth": round(page_width),
                    "pageHeight": round(page_height),
                    "message": message,
                    "textContent": text_content[:800],  # More text for reference
                    "hasStaticContent": True
                }
            
            return {
                "name": "Imported PDF Template",
                "fields": fields,
                "pageWidth": round(page_width),
                "pageHeight": round(page_height),
                "message": message,
                "textContent": text_content[:500]
            }
            
        except Exception as e:
            return {
                "error": "Text extraction failed",
                "message": str(e)
            }
    
    def _parse_form_fields(self, reader: PdfReader, page_width: float, page_height: float) -> Dict:
        """
        Parse PDF with form fields (Adobe Acrobat forms)
        """
        try:
            # Get form fields
            form_fields = reader.get_form_text_fields() or {}
            
            # Get page
            first_page = reader.pages[0]
            
            # Extract fields
            fields = []
            
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
    
    def _detect_tables_from_text(self, lines: List[str]) -> Dict:
        """
        Attempt to detect table structures from text lines
        
        Heuristics:
        - Multiple consecutive lines with similar patterns (tabs or multiple spaces)
        - Lines with similar character counts
        - Repeated delimiter patterns (|, tabs, multiple spaces)
        
        Args:
            lines: List of text lines from PDF
            
        Returns:
            dict: Information about detected tables
        """
        tables = []
        current_table_lines = []
        y_position = 50
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Empty line might indicate end of table
                if len(current_table_lines) >= 3:  # At least header + 2 rows
                    # Process accumulated table
                    table_info = self._analyze_table_structure(current_table_lines)
                    if table_info:
                        table_info['y_position'] = y_position
                        tables.append(table_info)
                        y_position += table_info['height'] + 20
                    current_table_lines = []
                continue
            
            # Check if line looks like a table row
            # Common patterns: pipe-separated, tab-separated, or multiple spaces
            is_table_row = (
                line.count('|') >= 2 or  # Pipe-separated
                line.count('\t') >= 2 or  # Tab-separated
                len(re.findall(r'\s{3,}', line)) >= 2  # Multiple consecutive spaces
            )
            
            if is_table_row:
                current_table_lines.append(line)
            else:
                # Not a table row
                if len(current_table_lines) >= 3:
                    table_info = self._analyze_table_structure(current_table_lines)
                    if table_info:
                        table_info['y_position'] = y_position
                        tables.append(table_info)
                        y_position += table_info['height'] + 20
                current_table_lines = []
        
        # Check for remaining table at end
        if len(current_table_lines) >= 3:
            table_info = self._analyze_table_structure(current_table_lines)
            if table_info:
                table_info['y_position'] = y_position
                tables.append(table_info)
        
        return {'tables': tables}
    
    def _analyze_table_structure(self, table_lines: List[str]) -> Optional[Dict]:
        """
        Analyze a group of lines to determine table structure
        
        Args:
            table_lines: Lines that appear to be part of a table
            
        Returns:
            dict: Table structure info or None
        """
        if not table_lines:
            return None
        
        # Determine delimiter
        first_line = table_lines[0]
        delimiter = None
        
        if '|' in first_line:
            delimiter = '|'
        elif '\t' in first_line:
            delimiter = '\t'
        else:
            # Use multiple spaces as delimiter
            delimiter = re.compile(r'\s{2,}')
        
        # Count columns from first line
        if isinstance(delimiter, str):
            columns = len([c for c in first_line.split(delimiter) if c.strip()])
        else:
            columns = len([c for c in delimiter.split(first_line) if c.strip()])
        
        # Assume first line is header
        if isinstance(delimiter, str):
            headers = [c.strip() for c in first_line.split(delimiter) if c.strip()]
        else:
            headers = [c.strip() for c in delimiter.split(first_line) if c.strip()]
        
        rows = len(table_lines) - 1  # Exclude header
        
        if rows < 1 or columns < 2:
            return None
        
        return {
            'rows': max(rows, 3),  # At least 3 rows for data entry
            'columns': columns,
            'headers': headers if len(headers) == columns else None,
            'height': (rows + 1) * 25  # Estimate height
        }
