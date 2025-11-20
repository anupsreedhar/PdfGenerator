"""
PDF Generation Service using ReportLab
Supports overlaying data on existing PDF templates
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import os


class PDFService:
    """
    Service for generating PDFs from templates
    Supports overlay mode to use original PDF as background
    """
    
    def __init__(self):
        """Initialize PDF service"""
        self.template_cache = {}
    
    def generate_pdf(self, template, data, background_pdf_path=None):
        """
        Generate PDF from template and data
        
        Args:
            template: Template object with fields
            data: Dict of field values
            background_pdf_path: Optional path to PDF to use as background
            
        Returns:
            bytes: PDF file as bytes
        """
        print(f"🔧 generate_pdf called")
        print(f"📄 Template: {template.name}")
        print(f"📁 Background PDF path: {background_pdf_path}")
        print(f"✅ Background exists: {os.path.exists(background_pdf_path) if background_pdf_path else 'N/A'}")
        
        # If background PDF provided, use overlay mode
        if background_pdf_path and os.path.exists(background_pdf_path):
            print("🎨 Using OVERLAY MODE")
            return self._generate_pdf_with_overlay(template, data, background_pdf_path)
        
        # Otherwise, generate simple PDF
        print("📝 Using SIMPLE MODE (no background)")
        return self._generate_simple_pdf(template, data)
    
    def _generate_simple_pdf(self, template, data):
        """
        Generate simple PDF (original behavior)
        """
        # Create BytesIO buffer
        buffer = BytesIO()
        
        # Get page size
        page_width = template.pageWidth if hasattr(template, 'pageWidth') else 612
        page_height = template.pageHeight if hasattr(template, 'pageHeight') else 792
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        
        # Set title
        c.setTitle(template.name)
        
        # Add template name as header
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, page_height - 30, f"Template: {template.name}")
        c.setFont("Helvetica", 8)
        c.drawString(40, page_height - 45, f"Generated: {self._get_timestamp()}")
        
        # Draw fields
        for field in template.fields:
            self._draw_field(c, field, data, page_height)
        
        # Save PDF
        c.showPage()
        c.save()
        
        # Get PDF bytes
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_pdf_with_overlay(self, template, data, background_pdf_path):
        """
        Generate PDF by overlaying data on existing PDF template
        
        This preserves the original PDF's design, images, and layout
        """
        try:
            print(f"🎨 Overlay Mode: Using background PDF: {background_pdf_path}")
            print(f"📝 Overlaying {len(template.fields)} fields")
            print(f"📊 Data keys: {list(data.keys())}")
            print(f"📊 Data values sample:")
            for key, value in list(data.items())[:10]:  # Show first 10
                print(f"   {key}: '{value}' (type: {type(value).__name__})")
            
            # Create overlay with data
            overlay_buffer = BytesIO()
            
            # Get page size
            page_width = template.pageWidth if hasattr(template, 'pageWidth') else 612
            page_height = template.pageHeight if hasattr(template, 'pageHeight') else 792
            
            print(f"📐 Page size: {page_width}x{page_height}")
            
            # Create canvas for overlay (transparent background)
            c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
            
            # Draw only the data fields (no headers, transparent background)
            fields_drawn = 0
            for field in template.fields:
                self._draw_field(c, field, data, page_height, overlay_mode=True)
                if data.get(field.name):
                    fields_drawn += 1
            
            print(f"✅ Drew {fields_drawn} fields with data")
            
            c.save()
            overlay_buffer.seek(0)
            
            # Read background PDF
            background_pdf = PdfReader(background_pdf_path)
            background_page = background_pdf.pages[0]
            
            # CRITICAL FIX: Remove form field annotations from background
            # Form fields render ON TOP of overlay content, hiding our checkmarks
            if '/Annots' in background_page:
                annot_count = len(background_page['/Annots'].get_object() if hasattr(background_page['/Annots'], 'get_object') else background_page['/Annots'])
                del background_page['/Annots']
                print(f"🗑️  Removed {annot_count} form field annotations from background (prevents overlay conflicts)")
            
            # Read overlay PDF
            overlay_pdf = PdfReader(overlay_buffer)
            overlay_page = overlay_pdf.pages[0]
            
            # Merge: background + overlay
            background_page.merge_page(overlay_page)
            
            # Write result
            output = PdfWriter()
            output.add_page(background_page)
            
            # Get bytes
            result_buffer = BytesIO()
            output.write(result_buffer)
            result_buffer.seek(0)
            
            return result_buffer.getvalue()
            
        except Exception as e:
            print(f"Error in overlay mode: {e}")
            print("Falling back to simple PDF generation")
            return self._generate_simple_pdf(template, data)
    
    def _draw_field(self, c, field, data, page_height, overlay_mode=False):
        """
        Draw a single field on the PDF
        
        Args:
            overlay_mode: If True, skip drawing boxes/backgrounds (for transparent overlay)
        """
        # Get field properties
        field_name = field.name
        field_type = field.type
        field_label = getattr(field, 'label', field_name)
        x = field.x
        # Convert Y coordinate (canvas origin is bottom-left, template origin is top-left)
        y = page_height - field.y - field.height
        width = field.width
        height = field.height
        font_size = getattr(field, 'fontSize', 12)
        font_weight = getattr(field, 'fontWeight', 'normal')
        
        # Select font
        font_name = "Helvetica-Bold" if font_weight == "bold" else "Helvetica"
        
        # Handle table type
        if field_type == 'table':
            self._draw_table(c, field, data, page_height, overlay_mode)
            return
        
        # Handle different field types
        if field_type == 'label':
            # In overlay mode, skip static labels (they're on the background)
            if overlay_mode:
                return
            # Static label - just draw the text
            c.setFont(font_name, font_size)
            c.drawString(x, y + (height / 2) - (font_size / 3), field_label)
            
        elif field_type == 'checkbox':
            # Check if checked
            value = data.get(field_name, '')
            is_checked = False
            if value:
                value_str = str(value).lower().strip()
                is_checked = value_str in ['true', 'yes', '1', 'checked', 'on', 'x']
            
            # Debug logging
            print(f"🔲 Checkbox '{field_name}': value='{value}', is_checked={is_checked}, overlay={overlay_mode}, pos=({x},{y}), size={width}x{height}")
            
            if not overlay_mode:
                # Draw checkbox box (only in non-overlay mode)
                c.setStrokeColorRGB(0.2, 0.4, 0.8)
                c.setLineWidth(1.5)
                c.rect(x, y, width, height)
            
            if is_checked:
                # SOLUTION: Draw MULTIPLE visible indicators for maximum visibility
                
                # Set opacity to ensure visibility over background
                c.saveState()  # Save current graphics state
                
                # METHOD 1: Filled black square (most visible)
                c.setFillColorRGB(0, 0, 0)  # Pure black
                c.setStrokeColorRGB(0, 0, 0)
                c.setFillAlpha(1.0)  # Fully opaque
                c.setStrokeAlpha(1.0)
                
                # Draw a filled rectangle that's slightly smaller than the checkbox
                inner_padding = 2
                c.rect(
                    x + inner_padding, 
                    y + inner_padding, 
                    width - 2*inner_padding, 
                    height - 2*inner_padding, 
                    fill=1, 
                    stroke=0
                )
                
                # METHOD 2: Also draw checkmark for clarity
                c.setLineWidth(max(3, min(width, height) // 5))  # Scale line width with checkbox size
                
                # Checkmark geometry (larger)
                padding = 0.1
                check_x1 = x + width * (padding + 0.1)
                check_y1 = y + height * 0.5
                check_x2 = x + width * 0.45
                check_y2 = y + height * (padding + 0.1)
                check_x3 = x + width * (1 - padding - 0.05)
                check_y3 = y + height * (1 - padding - 0.05)
                
                # Draw white checkmark on black background
                c.setStrokeColorRGB(1, 1, 1)  # White checkmark
                c.line(check_x1, check_y1, check_x2, check_y2)
                c.line(check_x2, check_y2, check_x3, check_y3)
                
                c.restoreState()  # Restore graphics state
                
                print(f"   ✓ Drew FILLED checkbox + checkmark at ({x:.1f}, {y:.1f}) - {width}x{height}")
            else:
                print(f"   ☐ Checkbox not checked, skipping")
            
            if not overlay_mode:
                # Draw label next to checkbox
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(x + width + 5, y + (height / 2) - 3, field_label)
            
        else:
            # Text, number, date fields
            if not overlay_mode:
                # Draw field box
                c.setStrokeColorRGB(0.2, 0.4, 0.8)
                c.setLineWidth(1)
                c.setFillColorRGB(0.9, 0.95, 1.0)
                c.rect(x, y, width, height, fill=1)
                
                # Draw label above field
                c.setFont("Helvetica", 8)
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.drawString(x, y + height + 3, field_label + ":")
            
            # Draw value inside field (ALWAYS draw in both modes)
            value = data.get(field_name, '')
            if value:
                c.setFont(font_name, font_size)
                c.setFillColorRGB(0, 0, 0)  # Black text
                
                # Truncate if too long
                text = str(value)
                max_chars = int(width / (font_size * 0.6))
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + '...'
                
                # Draw the text value
                c.drawString(x + 5, y + (height / 2) - (font_size / 3), text)
        
        # Reset colors
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
    
    def _draw_table(self, c, field, data, page_height, overlay_mode=False):
        """
        Draw a table on the PDF
        
        Args:
            overlay_mode: If True, skip drawing table grid (for transparent overlay)
        """
        # Get table properties
        x = field.x
        y = page_height - field.y - field.height
        
        rows = getattr(field, 'tableRows', 3)
        columns = getattr(field, 'tableColumns', 3)
        headers = getattr(field, 'tableHeaders', [])
        cell_width = getattr(field, 'cellWidth', 100)
        cell_height = getattr(field, 'cellHeight', 25)
        
        table_width = cell_width * columns
        has_headers = len(headers) > 0
        total_rows = rows + (1 if has_headers else 0)
        table_height = cell_height * total_rows
        
        # Get table data
        table_data = data.get(field.name, [])
        
        # Draw table border
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2)
        c.rect(x, y, table_width, table_height)
        
        # Draw horizontal lines
        c.setLineWidth(1)
        for i in range(1, total_rows):
            line_y = y + (i * cell_height)
            line_width = 2 if (has_headers and i == 1) else 1
            c.setLineWidth(line_width)
            c.line(x, line_y, x + table_width, line_y)
        
        # Draw vertical lines
        c.setLineWidth(1)
        for i in range(1, columns):
            line_x = x + (i * cell_width)
            c.line(line_x, y, line_x, y + table_height)
        
        # Draw headers
        if has_headers:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.9, 0.95, 1.0)
            c.rect(x, y + table_height - cell_height, table_width, cell_height, fill=1)
            c.setFillColorRGB(0, 0, 0)
            
            for col in range(min(columns, len(headers))):
                header_x = x + (col * cell_width) + 5
                header_y = y + table_height - cell_height + cell_height / 2 - 3
                c.drawString(header_x, header_y, str(headers[col]))
        
        # Draw data cells
        c.setFont("Helvetica", 9)
        start_row = 1 if has_headers else 0
        
        if isinstance(table_data, list):
            for row_idx in range(min(rows, len(table_data))):
                row_data = table_data[row_idx]
                visual_row = row_idx + start_row
                
                if isinstance(row_data, list):
                    for col_idx in range(min(columns, len(row_data))):
                        cell_value = str(row_data[col_idx]) if row_data[col_idx] else ''
                        cell_x = x + (col_idx * cell_width) + 5
                        cell_y = y + table_height - (visual_row + 1) * cell_height + cell_height / 2 - 3
                        
                        # Truncate if too long
                        max_chars = int((cell_width - 10) / 5)
                        if len(cell_value) > max_chars:
                            cell_value = cell_value[:max_chars - 3] + '...'
                        
                        c.drawString(cell_x, cell_y, cell_value)
                elif isinstance(row_data, dict):
                    for col_idx, header in enumerate(headers[:columns]):
                        cell_value = str(row_data.get(header, ''))
                        cell_x = x + (col_idx * cell_width) + 5
                        cell_y = y + table_height - (visual_row + 1) * cell_height + cell_height / 2 - 3
                        
                        # Truncate if too long
                        max_chars = int((cell_width - 10) / 5)
                        if len(cell_value) > max_chars:
                            cell_value = cell_value[:max_chars - 3] + '...'
                        
                        c.drawString(cell_x, cell_y, cell_value)
        
        # Reset colors
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
