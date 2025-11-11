"""
PDF Generation Service using ReportLab
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO


class PDFService:
    """
    Service for generating PDFs from templates
    """
    
    def __init__(self):
        """Initialize PDF service"""
        pass
    
    def generate_pdf(self, template, data):
        """
        Generate PDF from template and data
        
        Args:
            template: Template object with fields
            data: Dict of field values
            
        Returns:
            bytes: PDF file as bytes
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
    
    def _draw_field(self, c, field, data, page_height):
        """
        Draw a single field on the PDF
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
            self._draw_table(c, field, data, page_height)
            return
        
        # Handle different field types
        if field_type == 'label':
            # Static label - just draw the text
            c.setFont(font_name, font_size)
            c.drawString(x, y + (height / 2) - (font_size / 3), field_label)
            
        elif field_type == 'checkbox':
            # Draw checkbox box
            c.setStrokeColorRGB(0.2, 0.4, 0.8)
            c.setLineWidth(1.5)
            c.rect(x, y, width, height)
            
            # Check if checked
            value = data.get(field_name, '')
            if value and str(value).lower() in ['true', 'yes', '1', 'checked']:
                # Draw checkmark
                c.setStrokeColorRGB(0, 0.5, 0)
                c.setLineWidth(2)
                # Draw X
                c.line(x + 2, y + 2, x + width - 2, y + height - 2)
                c.line(x + width - 2, y + 2, x + 2, y + height - 2)
            
            # Draw label next to checkbox
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(x + width + 5, y + (height / 2) - 3, field_label)
            
        else:
            # Text, number, date fields
            # Draw field box
            c.setStrokeColorRGB(0.2, 0.4, 0.8)
            c.setLineWidth(1)
            c.setFillColorRGB(0.9, 0.95, 1.0)
            c.rect(x, y, width, height, fill=1)
            
            # Draw label above field
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(x, y + height + 3, field_label + ":")
            
            # Draw value inside field
            value = data.get(field_name, '')
            if value:
                c.setFont(font_name, font_size)
                c.setFillColorRGB(0, 0, 0)
                
                # Truncate if too long
                text = str(value)
                max_chars = int(width / (font_size * 0.6))
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + '...'
                
                c.drawString(x + 5, y + (height / 2) - (font_size / 3), text)
        
        # Reset colors
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
    
    def _draw_table(self, c, field, data, page_height):
        """
        Draw a table on the PDF
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
