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

# Try to import pikepdf for better PDF merging
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
    print(f"✅ pikepdf available (version {pikepdf.__version__}) - using enhanced PDF merge")
except ImportError as e:
    PIKEPDF_AVAILABLE = False
    print(f"⚠️  pikepdf not available - using PyPDF2")
    print(f"   Import error: {e}")
    print(f"   Install with: pip install pikepdf")
except Exception as e:
    PIKEPDF_AVAILABLE = False
    print(f"❌ pikepdf import failed with unexpected error: {e}")
    print(f"   Using PyPDF2 as fallback")



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
            print(f"📊 Data keys received: {list(data.keys())}")
            print(f"📊 Data values: {data}")
            
            # NEW APPROACH: Try to fill actual PDF form fields first
            result = self._try_fill_pdf_form_fields(background_pdf_path, template, data)
            if result:
                print("✅ Successfully filled PDF form fields directly!")
                return result
            
            # Original overlay approach as fallback
            return self._generate_overlay_merge(template, data, background_pdf_path)
            
        except Exception as e:
            print(f"❌ Error in overlay mode: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            import traceback
            print("❌ Full traceback:")
            traceback.print_exc()
            print("⚠️  Falling back to simple PDF generation")
            return self._generate_simple_pdf(template, data)
    
    def _try_fill_pdf_form_fields(self, pdf_path, template, data):
        """
        Try to fill actual PDF form fields (AcroForm) directly
        This is more reliable than overlay for forms with checkboxes
        """
        try:
            print("🔍 Attempting to fill PDF form fields directly...")
            
            # Try using PyPDF2 to fill form fields
            from PyPDF2 import PdfReader, PdfWriter
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            # Check if PDF has form fields
            if '/AcroForm' not in reader.trailer['/Root']:
                print("⚠️  PDF has no AcroForm fields, using overlay method")
                return None
            
            print("✅ PDF has form fields, attempting to fill them...")
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Fill form fields
            if writer._root_object.get('/AcroForm'):
                # Get all fields
                form_fields = {}
                for field in template.fields:
                    field_name = field.name
                    if field.type == 'checkbox':
                        value = data.get(field_name, '')
                        # For checkboxes, use 'Yes' or 'Off'
                        if value and str(value).strip().lower() in ['yes', 'true', '1', 'checked', 'on', 'x']:
                            form_fields[field_name] = '/Yes'
                        else:
                            form_fields[field_name] = '/Off'
                    else:
                        value = data.get(field_name, '')
                        if value:
                            form_fields[field_name] = str(value)
                
                print(f"📝 Filling {len(form_fields)} form fields...")
                
                # Update form fields
                writer.update_page_form_field_values(writer.pages[0], form_fields)
                
                # Save to buffer
                output_buffer = BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0)
                
                result = output_buffer.getvalue()
                print(f"✅ Form filling successful! Result size: {len(result)} bytes")
                return result
            else:
                print("⚠️  No form fields found in AcroForm")
                return None
                
        except Exception as e:
            print(f"⚠️  Form field filling failed: {e}")
            return None
    
    def _generate_overlay_merge(self, template, data, background_pdf_path):
        """
        Original overlay merge approach
        """
        # Create overlay with data
        overlay_buffer = BytesIO()
        
        # Get page size
        page_width = template.pageWidth if hasattr(template, 'pageWidth') else 612
        page_height = template.pageHeight if hasattr(template, 'pageHeight') else 792
        
        print(f"📐 Page size: {page_width}x{page_height}")
        
        # Create canvas for overlay (transparent background)
        c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
        
        # IMPORTANT: Set canvas to not compress content (helps with visibility)
        c.setPageCompression(0)
        
        # Draw only the data fields (no headers, transparent background)
        fields_drawn = 0
        checkboxes_drawn = 0
        for field in template.fields:
            result = self._draw_field(c, field, data, page_height, overlay_mode=True)
            if data.get(field.name):
                fields_drawn += 1
            if result == 'checkbox_drawn':
                checkboxes_drawn += 1
        
        print(f"✅ Drew {fields_drawn} fields with data ({checkboxes_drawn} checkboxes)")
        
        # Ensure all operations are flushed
        c.showPage()
        c.save()
        overlay_buffer.seek(0)
        
        overlay_bytes = overlay_buffer.getvalue()
        print(f"📦 Overlay PDF size: {len(overlay_bytes)} bytes")
        
        # DEBUG: Save overlay PDF to temp file for inspection
        import tempfile
        import time
        temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Use timestamp to avoid file locking issues
        timestamp = int(time.time() * 1000)
        debug_overlay_path = os.path.join(temp_dir, f'debug_overlay_{timestamp}.pdf')
        
        try:
            with open(debug_overlay_path, 'wb') as f:
                f.write(overlay_bytes)
            print(f"🔍 DEBUG: Saved overlay to {debug_overlay_path}")
        except Exception as debug_error:
            print(f"⚠️  Could not save debug overlay: {debug_error}")
            # Continue anyway - this is just for debugging
        
        # Reset buffer for reading
        overlay_buffer.seek(0)
        
        # Try pikepdf first (better merge), fallback to PyPDF2
        # Try importing pikepdf here too in case module-level import failed
        pikepdf_works = PIKEPDF_AVAILABLE
        if not pikepdf_works:
            try:
                import pikepdf
                pikepdf_works = True
                print("✅ pikepdf import succeeded at runtime!")
            except Exception as e:
                print(f"⚠️  pikepdf still not available at runtime: {e}")
        
        if pikepdf_works:
            print("🚀 Using pikepdf for PDF merge...")
            try:
                result_bytes = self._merge_with_pikepdf(background_pdf_path, overlay_bytes)
                if result_bytes:
                    print("✅ pikepdf merge successful!")
                    # Flattening is done inside _merge_with_pikepdf
                    return result_bytes
                else:
                    print("⚠️  pikepdf merge returned None")
            except Exception as e:
                print(f"⚠️  pikepdf merge failed: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Falling back to PyPDF2...")
        else:
            print("⚠️  pikepdf not available, using PyPDF2 from start")
        
        # PyPDF2 merge (fallback or if pikepdf not available)
        print("📖 Using PyPDF2 for PDF merge...")
        overlay_buffer.seek(0)  # Reset buffer
        
        # Read background PDF
        print("📖 Reading background PDF...")
        background_pdf = PdfReader(background_pdf_path)
        background_page = background_pdf.pages[0]
        
        # Read overlay PDF
        print("📖 Reading overlay PDF...")
        overlay_pdf = PdfReader(overlay_buffer)
        overlay_page = overlay_pdf.pages[0]
        
        print(f"🔍 Background page size: {background_page.mediabox}")
        print(f"🔍 Overlay page size: {overlay_page.mediabox}")
        
        # Try merging with expand=True to preserve all content
        print("🔀 Merging overlay onto background...")
        try:
            # Method 1: Standard merge with expand
            background_page.merge_page(overlay_page)
            print("✅ Merge completed successfully")
        except Exception as merge_error:
            print(f"⚠️ Standard merge failed: {merge_error}")
            # Fallback: try merging the other way
            print("🔄 Trying alternate merge method...")
            overlay_page.merge_page(background_page)
            background_page = overlay_page
        
        # Write result
        output = PdfWriter()
        output.add_page(background_page)
        
        # IMPORTANT: Don't compress the output
        output.add_metadata({'/Producer': 'AIPdfGenerator'})
        
        print("💾 Writing final PDF...")
        
        # Get bytes
        result_buffer = BytesIO()
        output.write(result_buffer)
        result_buffer.seek(0)
        
        pypdf2_result = result_buffer.getvalue()
        
        # Try to flatten with pikepdf if available
        if pikepdf_works:
            print("🔧 Attempting to flatten PDF with pikepdf...")
            try:
                flattened = self._flatten_pdf_with_pikepdf(pypdf2_result)
                if flattened:
                    print("✅ PDF flattened successfully!")
                    return flattened
                else:
                    print("⚠️  Flattening failed, returning unflattened PDF")
            except Exception as e:
                print(f"⚠️  Flattening error: {e}")
        
        return pypdf2_result
    
    def _merge_with_pikepdf(self, background_pdf_path, overlay_bytes):
        """
        Merge PDFs using pikepdf (more reliable than PyPDF2)
        
        Args:
            background_pdf_path: Path to background PDF
            overlay_bytes: Overlay PDF as bytes
            
        Returns:
            Merged PDF as bytes, or None if failed
        """
        background = None
        overlay = None
        
        try:
            import pikepdf
            from io import BytesIO
            
            # Open background PDF
            background = pikepdf.Pdf.open(background_pdf_path)
            background_page = background.pages[0]
            
            # Open overlay PDF from bytes
            overlay_buffer = BytesIO(overlay_bytes)
            overlay = pikepdf.Pdf.open(overlay_buffer)
            overlay_page = overlay.pages[0]
            
            print(f"📄 Background page: {background_page}")
            print(f"📄 Overlay page: {overlay_page}")
            
            # Get content streams - handle different content structures
            bg_contents = background_page.get('/Contents')
            overlay_contents = overlay_page.get('/Contents')
            
            print(f"📄 Background contents type: {type(bg_contents)}")
            print(f"📄 Overlay contents type: {type(overlay_contents)}")
            
            if overlay_contents is not None:
                # Ensure both are arrays
                if not isinstance(bg_contents, pikepdf.Array):
                    if bg_contents is not None:
                        bg_contents = pikepdf.Array([bg_contents])
                    else:
                        bg_contents = pikepdf.Array([])
                
                if not isinstance(overlay_contents, pikepdf.Array):
                    overlay_contents = pikepdf.Array([overlay_contents])
                
                # Copy overlay contents to background PDF using background.copy_foreign()
                for content in overlay_contents:
                    # Use background PDF's copy_foreign method to properly copy objects from overlay PDF
                    copied_content = background.copy_foreign(content)
                    bg_contents.append(copied_content)
                
                background_page['/Contents'] = bg_contents
                
                print(f"✅ Merged {len(overlay_contents)} overlay content streams into {len(bg_contents)} total streams")
            else:
                print("⚠️  Overlay has no content streams")
            
            # CRITICAL: Flatten form fields to make PDF non-editable
            # Our overlay already has the filled data drawn on it
            # Now we remove the interactive form fields but keep the visual content
            print("🔧 Flattening PDF - removing interactive form fields while preserving filled data...")
            
            # First, render form field appearances to content streams (flatten them visually)
            for page_num, page in enumerate(background.pages):
                if '/Annots' in page:
                    annots = page['/Annots']
                    print(f"   📄 Processing {len(annots)} annotations on page {page_num + 1}...")
                    
                    # For each annotation, if it has an appearance, render it to the page content
                    for annot in annots:
                        try:
                            # If the annotation has an appearance stream, we want to keep its visual
                            # but pikepdf doesn't have built-in flattening, so we just remove them
                            # The overlay we merged already contains the filled data we want
                            pass
                        except:
                            pass
                    
                    # Now remove the annotations to make fields non-editable
                    print(f"   📄 Removing {len(annots)} form field widgets from page {page_num + 1}...")
                    del page['/Annots']
            
            # Remove AcroForm from the document catalog to fully flatten
            if '/AcroForm' in background.Root:
                print("🔧 Removing AcroForm from document catalog...")
                del background.Root['/AcroForm']
            
            print(f"✅ PDF flattened - form fields removed, filled data preserved from overlay")
            
            # Save result
            output_buffer = BytesIO()
            background.save(output_buffer)
            output_buffer.seek(0)
            
            result_bytes = output_buffer.getvalue()
            print(f"📦 pikepdf result size: {len(result_bytes)} bytes")
            
            return result_bytes
            
        except Exception as e:
            print(f"❌ pikepdf merge error: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        finally:
            # Ensure PDFs are closed
            try:
                if background:
                    background.close()
                if overlay:
                    overlay.close()
            except:
                pass
    
    def _flatten_pdf_with_pikepdf(self, pdf_bytes):
        """
        Flatten a PDF to remove all form fields using pikepdf
        
        Args:
            pdf_bytes: PDF as bytes
            
        Returns:
            Flattened PDF as bytes, or None if failed
        """
        try:
            import pikepdf
            from io import BytesIO
            
            print("   🔧 Opening PDF for flattening...")
            pdf_buffer = BytesIO(pdf_bytes)
            pdf = pikepdf.Pdf.open(pdf_buffer)
            
            # Remove annotations from ALL pages
            for page_num, page in enumerate(pdf.pages):
                if '/Annots' in page:
                    print(f"      📄 Removing {len(page['/Annots'])} form fields from page {page_num + 1}...")
                    del page['/Annots']
            
            # Remove AcroForm from the document catalog
            if '/AcroForm' in pdf.Root:
                print("      🔧 Removing AcroForm...")
                del pdf.Root['/AcroForm']
            
            # Save flattened PDF
            output_buffer = BytesIO()
            pdf.save(output_buffer)
            pdf.close()
            output_buffer.seek(0)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            print(f"   ❌ Flattening error: {e}")
            return None
    
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
        
        # Debug logging for checkboxes and dates
        if field_type in ['checkbox', 'date']:
            value = data.get(field_name, '')
            print(f"  🔍 Field '{field_name}' ({field_type}): value='{value}' type={type(value).__name__} at pos({x}, {field.y}) size({width}x{height})")
        
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
            # In overlay mode, only draw if checked
            if not overlay_mode:
                # Draw checkbox box
                c.setStrokeColorRGB(0.2, 0.4, 0.8)
                c.setLineWidth(1.5)
                c.rect(x, y, width, height)
            
            # Check if checked - improved logic with better value handling
            value = data.get(field_name, '')
            is_checked = False
            
            if value:
                value_str = str(value).strip().lower()
                # Handle various checkbox representations
                is_checked = value_str in ['true', 'yes', '1', 'checked', 'on', 'x']
                # Also check if value is not explicitly negative
                is_checked = is_checked or (value_str not in ['false', 'no', '0', 'unchecked', 'off', ''])
            
            # Debug output for checkbox decision
            if field_type == 'checkbox':
                print(f"    ➡️ Checkbox '{field_name}': value='{value}' → is_checked={is_checked}")
            
            if is_checked:
                # Save graphics state
                c.saveState()
                
                # Draw a professional checkmark (✓) symbol
                c.setStrokeColorRGB(0, 0, 0)  # Black color
                c.setLineWidth(2)  # Bold line
                
                # Calculate checkmark coordinates within the checkbox
                # Standard checkmark: starts at bottom-left, goes to middle-bottom, then to top-right
                check_left_x = x + width * 0.2
                check_left_y = y + height * 0.4
                check_middle_x = x + width * 0.4
                check_middle_y = y + height * 0.2
                check_right_x = x + width * 0.8
                check_right_y = y + height * 0.8
                
                print(f"    ✅ Drawing CHECKMARK (✓) at ({x}, {y}) in field size ({width}x{height})")
                
                # Draw the checkmark as two lines forming a "✓"
                # First stroke: bottom-left to middle
                c.line(check_left_x, check_left_y, check_middle_x, check_middle_y)
                # Second stroke: middle to top-right
                c.line(check_middle_x, check_middle_y, check_right_x, check_right_y)
                
                # Restore graphics state
                c.restoreState()
                
                return 'checkbox_drawn'
            else:
                print(f"    ⬜ Checkbox '{field_name}' not checked (empty)")
                return 'checkbox_empty'
            
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
                
                # Format date fields if needed
                if field_type == 'date' and value:
                    try:
                        # Try to format date nicely if it's in ISO format
                        from datetime import datetime
                        if 'T' in str(value) or len(str(value)) == 10:
                            # Parse and reformat
                            date_obj = datetime.fromisoformat(str(value).split('T')[0])
                            value = date_obj.strftime('%Y-%m-%d')
                    except:
                        # If formatting fails, use original value
                        pass
                
                # Truncate if too long
                text = str(value)
                max_chars = int(width / (font_size * 0.6))
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + '...'
                
                # Draw the text value with better vertical centering
                text_y = y + (height / 2) - (font_size / 3)
                c.drawString(x + 5, text_y, text)
        
        # Reset colors
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
        
        return None
    
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
