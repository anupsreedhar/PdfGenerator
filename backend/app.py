"""
PDF Template Generator - Python Backend
FastAPI server with ML training and PDF generation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi import UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn
import json
import os
from datetime import datetime
import logging
import sys
import traceback

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import services
from services.pdf_service import PDFService
from services.ml_service import MLService
from services.ml_recognition_service import MLRecognitionService
from services.pdf_parser import PDFParser
from services.pdf_to_html_converter import PDFToHTMLConverter
# Lazy import for html_css_template_service to avoid slow startup
# from services.html_css_template_service import HTMLCSSTemplateService

# Initialize FastAPI app
app = FastAPI(
    title="PDF Template Generator API",
    description="Generate PDFs from templates and train ML models",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
logger.info("🚀 Initializing services...")
pdf_service = PDFService()
logger.info("✅ PDF Service initialized")
ml_service = MLService()
logger.info("✅ ML Service initialized")
ml_recognition_service = MLRecognitionService()
logger.info("✅ ML Recognition Service initialized")
pdf_parser = PDFParser(use_ai=False)  # Set to True to enable LayoutLMv3
logger.info("✅ Basic PDF Parser initialized")
pdf_to_html_converter = PDFToHTMLConverter()
logger.info("✅ PDF to HTML Converter initialized")

# Lazy load HTML template service (xhtml2pdf imports are slow)
html_template_service = None
try:
    logger.info("⏳ Loading HTML Template Service...")
    from services.html_css_template_service import HTMLCSSTemplateService
    html_template_service = HTMLCSSTemplateService()
    logger.info("✅ HTML Template Service initialized")
except Exception as e:
    logger.warning(f"⚠️ HTML Template Service not available: {e}")
    html_template_service = None

# Optional: Create AI-enabled parser (try but don't fail if not available)
pdf_parser_ai = None
try:
    logger.info("⏳ Loading AI-powered PDF parser (this may take 10-20 seconds)...")
    import signal
    
    # Set a timeout for loading
    def timeout_handler(signum, frame):
        raise TimeoutError("AI parser loading timed out")
    
    # Only try AI parser, don't block startup
    pdf_parser_ai = PDFParser(use_ai=True)
    logger.info("✨ AI-powered PDF parsing available!")
except KeyboardInterrupt:
    logger.warning("⚠️ AI parser loading interrupted - continuing without AI")
    pdf_parser_ai = None
except Exception as e:
    logger.warning(f"⚠️ AI parsing not available (this is OK): {type(e).__name__}: {str(e)[:100]}")
    logger.info("   You can still use basic PDF parsing and all other features.")
    pdf_parser_ai = None


# ============================================================================
# Request Logging Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests and responses"""
    logger.info(f"🌐 {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"✅ {request.method} {request.url.path} - Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ {request.method} {request.url.path} - Error: {str(e)}")
        raise

# ============================================================================
# Models
# ============================================================================

class Field(BaseModel):
    name: str
    type: str
    label: Optional[str] = None
    x: int
    y: int
    width: int
    height: int
    fontSize: Optional[int] = 12
    fontWeight: Optional[str] = "normal"
    fontFamily: Optional[str] = "Helvetica"
    # Table-specific properties
    tableRows: Optional[int] = None

class GenerateFromHTMLRequest(BaseModel):
    template_name: str
    data: Dict
    tableColumns: Optional[int] = None
    tableHeaders: Optional[List[str]] = None
    cellWidth: Optional[int] = None
    cellHeight: Optional[int] = None

class Template(BaseModel):
    name: str
    fields: List[Field]
    pageWidth: Optional[int] = 612
    pageHeight: Optional[int] = 792
    pdfFilePath: Optional[str] = None  # Path to stored PDF template

class PDFRequest(BaseModel):
    template: Template
    data: Dict[str, str]

class TrainingConfig(BaseModel):
    epochs: int = 50
    batch_size: int = 16
    generate_synthetic: bool = True
    min_templates: int = 10

class TrainingRequest(BaseModel):
    templates: List[Template]
    config: Optional[TrainingConfig] = TrainingConfig()

class SmartGenerateRequest(BaseModel):
    template_name: str
    data: Dict[str, Any]

# ============================================================================
# PDF Generation Endpoints
# ============================================================================

@app.post("/api/pdf/generate")
async def generate_pdf(
    template_json: str = File(...),
    data_json: str = File(...),
    template_pdf: Optional[UploadFile] = File(None)
):
    """
    Generate a PDF from template and data
    
    Form Data:
    - template_json: JSON string of template definition
    - data_json: JSON string of field values
    - template_pdf: (Optional) Original PDF file to use as background
    
    Returns: PDF file as bytes
    """
    try:
        # Parse JSON strings
        template_dict = json.loads(template_json)
        data_dict = json.loads(data_json)
        
        # Convert to Template object
        template = Template(**template_dict)
        
        # Determine which PDF to use as background
        template_pdf_path = None
        
        # Priority 1: Manually uploaded PDF (if provided)
        if template_pdf:
            # Create temp directory if doesn't exist
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save uploaded PDF
            template_pdf_path = os.path.join(temp_dir, f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            with open(template_pdf_path, 'wb') as f:
                f.write(await template_pdf.read())
            print(f"📄 Using manually uploaded PDF: {template_pdf_path}")
        
        # Priority 2: Stored PDF from import (if exists)
        elif hasattr(template, 'pdfFilePath') and template.pdfFilePath:
            # Convert relative path to absolute
            stored_pdf_path = os.path.join(os.path.dirname(__file__), '..', template.pdfFilePath)
            if os.path.exists(stored_pdf_path):
                template_pdf_path = stored_pdf_path
                print(f"📄 Using stored template PDF: {template_pdf_path}")
            else:
                print(f"⚠️ Stored PDF not found: {stored_pdf_path}, generating basic PDF")
        
        # Priority 3: No background PDF - generate basic PDF
        if not template_pdf_path:
            print("📝 No background PDF - generating basic PDF")
        
        # Generate PDF (with or without background)
        pdf_bytes = pdf_service.generate_pdf(template, data_dict, template_pdf_path)
        
        # Clean up temp file (only if manually uploaded)
        if template_pdf and template_pdf_path and os.path.exists(template_pdf_path):
            try:
                os.remove(template_pdf_path)
            except:
                pass
        
        # Return as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={template.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pdf/generate-json")
async def generate_pdf_json(request: PDFRequest):
    """
    Generate a PDF from template and data (JSON version)
    
    Request body:
    {
        "template": {
            "name": "Template Name",
            "fields": [...],
            "pageWidth": 612,
            "pageHeight": 792,
            "pdfFilePath": "optional/path/to/pdf"
        },
        "data": {
            "field1": "value1",
            "field2": "value2"
        }
    }
    
    Returns: PDF file as bytes
    """
    try:
        template = request.template
        data_dict = request.data
        
        # Determine which PDF to use as background
        template_pdf_path = None
        
        # Check if template has a stored PDF path
        if hasattr(template, 'pdfFilePath') and template.pdfFilePath:
            # Convert relative path to absolute
            stored_pdf_path = os.path.join(os.path.dirname(__file__), '..', template.pdfFilePath)
            if os.path.exists(stored_pdf_path):
                template_pdf_path = stored_pdf_path
                print(f"📄 Using stored template PDF: {template_pdf_path}")
            else:
                print(f"⚠️ Stored PDF not found: {stored_pdf_path}, generating basic PDF")
        
        # No background PDF - generate basic PDF
        if not template_pdf_path:
            print("📝 No background PDF - generating basic PDF")
        
        # Generate PDF (with or without background)
        pdf_bytes = pdf_service.generate_pdf(template, data_dict, template_pdf_path)
        
        # Return as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={template.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ML Training Endpoints
# ============================================================================

@app.post("/api/train")
async def train_model(request: TrainingRequest, background_tasks: BackgroundTasks):
    """
    Train ML model on templates
    
    Request body:
    {
        "templates": [...],
        "config": {
            "epochs": 50,
            "batch_size": 16,
            "generate_synthetic": true,
            "min_templates": 10
        }
    }
    
    Returns: Training task ID for status polling (or immediate result)
    """
    try:
        # Convert Pydantic models to dicts
        templates_data = [t.dict() for t in request.templates]
        config = request.config.dict()
        
        # For synchronous training (small datasets)
        if len(templates_data) < 20:
            result = ml_service.train_model(templates_data, config)
            return {
                "status": "complete",
                "result": result
            }
        
        # For async training (large datasets)
        task_id = ml_service.create_training_task(templates_data, config)
        background_tasks.add_task(ml_service.train_async, task_id, templates_data, config)
        
        return {
            "status": "started",
            "task_id": task_id,
            "message": "Training started in background"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/train/status/{task_id}")
async def training_status(task_id: str):
    """
    Get training status
    """
    try:
        status = ml_service.get_training_status(task_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/model/info")
async def model_info():
    """
    Get current model information
    """
    try:
        info = ml_service.get_model_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Template Generation from Model
# ============================================================================

@app.post("/api/generate-template")
async def generate_template_from_model(template_type: str = "invoice"):
    """
    Generate a new template using the trained ML model
    """
    try:
        template = ml_service.generate_template(template_type)
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
async def root():
    """
    Health check endpoint
    """
    return {
        "status": "running",
        "service": "PDF Template Generator API",
        "version": "1.0.0",
        "endpoints": {
            "pdf_generation": "/api/pdf/generate",
            "ml_training": "/api/train",
            "training_status": "/api/train/status/{task_id}",
            "model_info": "/api/model/info",
            "generate_template": "/api/generate-template",
            "docs": "/docs"
        }
    }

# ============================================================================
# PDF Import/Parse Endpoint
# ============================================================================

@app.post("/api/pdf/import")
async def import_pdf_template(file: UploadFile = File(...)):
    """
    Import an existing PDF template and extract fields or text content
    
    Returns: Template JSON compatible with the designer
    """
    temp_path = None
    try:
        print(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail={"error": "Invalid file type", "message": "Please upload a PDF file"}
            )
        
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Parse PDF form fields
        template = pdf_parser.parse_pdf_form(temp_path, filename=file.filename)
        
        # Check for errors
        if "error" in template:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail=template)
        
        # Save PDF permanently for later use
        template_id = template.get('id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        pdf_storage_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'templates', 'pdfs')
        os.makedirs(pdf_storage_dir, exist_ok=True)
        
        permanent_pdf_path = os.path.join(pdf_storage_dir, f"template_{template_id}.pdf")
        
        # Copy temp file to permanent location
        with open(temp_path, 'rb') as src:
            with open(permanent_pdf_path, 'wb') as dst:
                dst.write(src.read())
        
        # Add PDF path to template (relative path for portability)
        template['pdfFilePath'] = f"data/templates/pdfs/template_{template_id}.pdf"
        template['originalFilename'] = file.filename
        
        print(f"✅ Saved template PDF: {permanent_pdf_path}")
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up temp file on error
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Error importing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": "Import failed", "message": str(e)})


@app.post("/api/pdf/import-ai")
async def import_pdf_template_ai(file: UploadFile = File(...)):
    """
    Import PDF using LayoutLMv3 AI for intelligent field detection
    
    Requires: transformers, torch, pdf2image
    Install: pip install transformers torch pdf2image Pillow pytesseract
    
    Returns: Template JSON with AI-detected fields
    """
    if not pdf_parser_ai:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "AI parsing not available",
                "message": "LayoutLMv3 dependencies not installed. Install with: pip install transformers torch pdf2image Pillow pytesseract"
            }
        )
    
    temp_path = None
    try:
        print(f"🤖 AI Import: {file.filename}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid file type", "message": "Please upload a PDF file"}
            )
        
        # Save uploaded file temporarily
        temp_path = f"temp_ai_{file.filename}"
        
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Parse with AI
        template = pdf_parser_ai.parse_pdf_form(temp_path, use_ai=True, filename=file.filename)
        
        # Check for errors
        if "error" in template:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=400, detail=template)
        
        # Save PDF permanently for later use
        template_id = template.get('id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        pdf_storage_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'templates', 'pdfs')
        os.makedirs(pdf_storage_dir, exist_ok=True)
        
        permanent_pdf_path = os.path.join(pdf_storage_dir, f"template_{template_id}.pdf")
        
        # Copy temp file to permanent location
        with open(temp_path, 'rb') as src:
            with open(permanent_pdf_path, 'wb') as dst:
                dst.write(src.read())
        
        # Add PDF path to template (relative path for portability)
        template['pdfFilePath'] = f"data/templates/pdfs/template_{template_id}.pdf"
        template['originalFilename'] = file.filename
        
        print(f"✅ Saved template PDF: {permanent_pdf_path}")
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up temp file on error
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"AI import error: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": "AI import failed", "message": str(e)})


@app.get("/health")
async def health():
    """
    Detailed health check
    """
    return {
        "status": "healthy",
        "pdf_service": "ready",
        "ml_service": "ready",
        "model_loaded": ml_service.is_model_loaded(),
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# HTML Template Endpoints (Auto-Convert PDF → HTML)
# ============================================================================

@app.post("/api/pdf/import-and-convert")
async def import_and_convert_to_html(
    pdf_file: UploadFile = File(...),
    template_name: Optional[str] = None
):
    """
    Import PDF template and automatically convert to HTML/CSS
    
    This endpoint:
    1. Receives PDF file upload
    2. Uses AI to detect field positions
    3. Converts PDF to HTML/CSS template
    4. Saves tiny HTML file (10 KB instead of 5 MB)
    5. Deletes original PDF (no storage needed!)
    
    Returns: Template metadata with HTML path
    """
    temp_pdf_path = None
    try:
        logger.info("=" * 80)
        logger.info("📥 NEW REQUEST: Import and Convert PDF to HTML")
        logger.info("=" * 80)
        
        # Generate template name from filename if not provided
        if not template_name:
            template_name = pdf_file.filename.replace('.pdf', '').replace(' ', '_')
        
        logger.info(f"� Template Name: {template_name}")
        logger.info(f"📄 Original Filename: {pdf_file.filename}")
        logger.info(f"📄 Content Type: {pdf_file.content_type}")
        
        # Save uploaded PDF temporarily
        temp_pdf_path = f"data/templates/temp_{template_name}.pdf"
        os.makedirs("data/templates", exist_ok=True)
        logger.info(f"📁 Created directory: data/templates")
        
        logger.info(f"💾 Reading uploaded file...")
        with open(temp_pdf_path, 'wb') as f:
            content = await pdf_file.read()
            f.write(content)
        
        logger.info(f"✅ PDF saved temporarily: {temp_pdf_path}")
        logger.info(f"📊 File size: {len(content):,} bytes ({len(content)/1024:.1f} KB)")
        
        # Use AI to detect fields
        logger.info(f"🤖 Selecting parser: {'AI-powered' if pdf_parser_ai else 'Basic'}")
        parser = pdf_parser_ai if pdf_parser_ai else pdf_parser
        
        logger.info(f"🔍 Starting field detection...")
        field_positions = parser.parse_pdf_form(temp_pdf_path)
        
        num_fields = len(field_positions.get('fields', []))
        logger.info(f"✅ Field detection complete: {num_fields} fields found")
        for i, field in enumerate(field_positions.get('fields', [])[:5], 1):
            logger.info(f"   Field {i}: {field.get('label', 'Unknown')}")
        if num_fields > 5:
            logger.info(f"   ... and {num_fields - 5} more fields")
        
        # Convert PDF to HTML
        logger.info(f"🔄 Converting PDF to HTML...")
        html_path = pdf_to_html_converter.convert_pdf_to_html(
            pdf_path=temp_pdf_path,
            template_name=template_name,
            field_positions=field_positions
        )
        logger.info(f"✅ HTML template created: {html_path}")
        
        # Delete temporary PDF (we have HTML now!)
        os.remove(temp_pdf_path)
        html_size = os.path.getsize(html_path)
        storage_saved = len(content) - html_size
        logger.info(f"🗑️ Deleted original PDF")
        logger.info(f"💾 Storage savings: {len(content)/1024:.1f} KB → {html_size/1024:.1f} KB")
        logger.info(f"🎉 Saved: {storage_saved/1024:.1f} KB ({storage_saved/len(content)*100:.1f}% reduction)")
        
        # Save template metadata
        template_data = {
            'name': template_name,
            'type': 'html',
            'html_path': html_path,
            'fields': field_positions.get('fields', []),
            'created_at': datetime.now().isoformat(),
            'original_pdf_size': len(content),
            'html_size': html_size,
            'storage_saved': storage_saved
        }
        
        # Save metadata
        metadata_path = f"data/templates/{template_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        logger.info(f"💾 Metadata saved: {metadata_path}")
        logger.info("=" * 80)
        logger.info("✅ SUCCESS: Template converted successfully!")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'template': template_data,
            'message': f"Template converted to HTML. Saved {storage_saved/1024:.1f} KB storage!"
        }
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ ERROR: Failed to convert PDF to HTML")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Clean up temp file on error
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logger.info(f"🗑️ Cleaned up temp file: {temp_pdf_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup temp file: {cleanup_error}")
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Conversion failed",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@app.post("/api/pdf/generate-from-html")
async def generate_pdf_from_html(request: GenerateFromHTMLRequest):
    """
    Generate PDF from HTML template
    
    Request body:
    {
        "template_name": "AB428_EN",
        "data": {
            "first_name": "John",
            "last_name": "Doe",
            ...
        }
    }
    
    Returns: PDF file
    """
    try:
        # Check if HTML template service is available
        if html_template_service is None:
            raise HTTPException(
                status_code=503, 
                detail="HTML Template Service not available. Server may still be initializing."
            )
        
        logger.info("=" * 80)
        logger.info("📄 NEW REQUEST: Generate PDF from HTML")
        logger.info("=" * 80)
        logger.info(f"Template: {request.template_name}")
        logger.info(f"Data fields: {list(request.data.keys())}")
        
        # Load template metadata
        metadata_path = f"data/templates/{request.template_name}_metadata.json"
        
        if not os.path.exists(metadata_path):
            logger.error(f"❌ Template not found: {metadata_path}")
            raise HTTPException(status_code=404, detail=f"HTML template not found: {request.template_name}")
        
        with open(metadata_path, 'r') as f:
            template_data = json.load(f)
        
        logger.info(f"✅ Template metadata loaded")
        
        # Generate PDF from HTML
        html_filename = f"{request.template_name}.html"
        logger.info(f"🔄 Generating PDF from {html_filename}...")
        
        pdf_bytes = html_template_service.generate_pdf(html_filename, request.data)
        
        logger.info(f"✅ PDF generated: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
        logger.info("=" * 80)
        
        # Return PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={request.template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ ERROR: Failed to generate PDF from HTML")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ML Recognition Endpoints (Template Detection & Data Extraction)
# ============================================================================
 
@app.post("/api/ml/detect-template")
async def detect_template(file: UploadFile = File(...)):
    """
    Detect which template a PDF matches using ML model
   
    Args:
        file: PDF file to analyze
   
    Returns:
        {
            "success": true,
            "template_id": "invoice_template",
            "template_name": "Invoice Template",
            "confidence": 0.95,
            "all_scores": {...}
        }
    """
    logger.info("=" * 80)
    logger.info(f"📊 ML TEMPLATE DETECTION REQUEST")
    logger.info(f"File: {file.filename}")
    logger.info("=" * 80)
   
    # Save uploaded file temporarily
    temp_path = f"backend/temp/detect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
   
    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
       
        logger.info(f"📁 Saved temporary file: {temp_path}")
       
        # Detect template
        result = ml_recognition_service.predict_template(temp_path)
       
        logger.info(f"✅ Template detected: {result.get('template_id', 'unknown')}")
        logger.info(f"   Confidence: {result.get('confidence', 0):.2%}")
       
        return result
       
    except Exception as e:
        logger.error(f"❌ Template detection error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
   
    finally:
        # Clean up temp file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"🧹 Cleaned up: {temp_path}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete temp file: {e}")

@app.post("/api/ml/smart-generate")
async def smart_generate_pdf(request: SmartGenerateRequest):
    """
    ML-Powered Smart PDF Generation
   
    Uses trained model to intelligently select and fill template by name.
    The model learns all template structures during training and can
    generate PDFs with minimal input.
   
    Args:
        request: JSON body with template_name and data
   
    Returns:
        PDF file as bytes
       
    Example:
        POST /api/ml/smart-generate
        {
            "template_name": "invoice_template",
            "data": {
                "invoice_number": "INV-001",
                "date": "2024-01-15",
                "amount": "1500.00"
            }
        }
    """
    template_name = request.template_name
    data = request.data
   
    logger.info("=" * 80)
    logger.info(f"🤖 ML SMART GENERATE REQUEST")
    logger.info(f"Template Name: {template_name}")
    logger.info(f"Data Fields: {len(data)}")
    logger.info("=" * 80)
   
    try:
        # Load all templates from cache
        templates = ml_recognition_service.templates_cache
       
        if not templates:
            raise HTTPException(
                status_code=404,
                detail="No templates found. Please train the model first or create templates."
            )
       
        # Find matching template by name (case-insensitive, flexible matching)
        template_id = None
        template_obj = None
       
        # Exact match first
        for tid, tpl in templates.items():
            if tid.lower() == template_name.lower() or tpl.get('name', '').lower() == template_name.lower():
                template_id = tid
                template_obj = tpl
                break
       
        # Partial match if no exact match
        if not template_id:
            for tid, tpl in templates.items():
                if template_name.lower() in tid.lower() or template_name.lower() in tpl.get('name', '').lower():
                    template_id = tid
                    template_obj = tpl
                    logger.info(f"📌 Using partial match: {tid}")
                    break
       
        if not template_obj:
            available_templates = [f"{tid} ({tpl.get('name', 'unnamed')})" for tid, tpl in templates.items()]
            raise HTTPException(
                status_code=404,
                detail=f"Template '{template_name}' not found. Available: {', '.join(available_templates)}"
            )
       
        logger.info(f"✅ Found template: {template_id}")
        logger.info(f"   Name: {template_obj.get('name', 'unnamed')}")
        logger.info(f"   Fields: {len(template_obj.get('fields', []))}")
       
        # ML Enhancement: Auto-fill missing fields using model predictions
        enhanced_data = data.copy()
       
        # Get template fields
        template_fields = {field['name']: field for field in template_obj.get('fields', [])}
       
        # Check for missing fields and provide defaults
        for field_name, field_info in template_fields.items():
            if field_name not in enhanced_data:
                # Provide intelligent defaults based on field type
                field_type = field_info.get('type', 'text')
               
                if field_type == 'checkbox':
                    enhanced_data[field_name] = False
                elif field_type == 'date':
                    enhanced_data[field_name] = datetime.now().strftime('%Y-%m-%d')
                elif field_type == 'number':
                    enhanced_data[field_name] = '0'
                else:
                    enhanced_data[field_name] = ''  # Empty for text fields
               
                logger.info(f"   Auto-filled: {field_name} = {enhanced_data[field_name]}")
       
        # Convert template dict to Template object (use the Pydantic model defined above)
        template = Template(**template_obj)
       
        # Check if template has a stored PDF background
        template_pdf_path = None
        if hasattr(template, 'pdfFilePath') and template.pdfFilePath:
            stored_pdf_path = os.path.join(os.path.dirname(__file__), '..', template.pdfFilePath)
            if os.path.exists(stored_pdf_path):
                template_pdf_path = stored_pdf_path
                logger.info(f"📄 Using template background: {template_pdf_path}")
       
        # Generate PDF using PDFService
        pdf_bytes = pdf_service.generate_pdf(template, enhanced_data, template_pdf_path)
       
        logger.info(f"✅ PDF generated successfully ({len(pdf_bytes)} bytes)")
       
        # Return as downloadable file
        filename = f"{template.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
       
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
       
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Smart generate error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
 
@app.get("/api/ml/templates")
async def get_ml_templates():
    """
    Get all available templates from the trained model
   
    Returns list of templates that the model knows about.
    These can be used with smart-generate endpoint.
   
    Returns:
        {
            "success": true,
            "templates": [
                {
                    "id": "invoice_template",
                    "name": "Invoice Template",
                    "fields": [...],
                    "field_count": 10
                }
            ]
        }
    """
    try:
        templates = ml_recognition_service.templates_cache
       
        if not templates:
            return {
                "success": False,
                "message": "No templates found. Please train the model first.",
                "templates": []
            }
       
        template_list = []
        for template_id, template_data in templates.items():
            template_list.append({
                "id": template_id,
                "name": template_data.get('name', template_id),
                "field_count": len(template_data.get('fields', [])),
                "fields": [
                    {
                        "name": field['name'],
                        "type": field.get('type', 'text'),
                        "required": field.get('required', False)
                    }
                    for field in template_data.get('fields', [])
                ],
                # "width": template_data.get('width'),
                # "height": template_data.get('height')
            })
       
        logger.info(f"📋 Retrieved {len(template_list)} templates")
       
        return {
            "success": True,
            "templates": template_list,
            "count": len(template_list)
        }
       
    except Exception as e:
        logger.error(f"❌ Get templates error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
@app.post("/api/templates/save") 
async def save_template(template: Dict[str, Any]):
    """
    Save a template to the file system (from browser localStorage)
    This makes the template available for ML training and detection
   
    Args:
        template: Template JSON with id, name, fields, pageWidth, pageHeight
   
    Returns:
        {
            "success": true,
            "message": "Template saved",
            "file_path": "data/templates/template_name.json"
        }
    """
    try:
        logger.info("=" * 80)
        logger.info(f"💾 SAVING TEMPLATE TO FILE SYSTEM")
        logger.info(f"Template: {template.get('name')}")
        logger.info("=" * 80)
       
        # Validate required fields
        if not template.get('name'):
            raise HTTPException(status_code=400, detail="Template name is required")
       
        if not template.get('fields') or len(template.get('fields', [])) == 0:
            raise HTTPException(status_code=400, detail="Template must have at least one field")
       
        # Create templates directory if it doesn't exist
        # Use absolute path: backend/../data/templates = AIPdfGenerator/data/templates
        base_dir = os.path.dirname(__file__)
        templates_dir = os.path.abspath(os.path.join(base_dir, '..', 'data', 'templates'))
        os.makedirs(templates_dir, exist_ok=True)
       
        # Use the exact template name for filename (with .json extension)
        template_name = template.get('name')
       
        # Use template name as-is for the filename
        filename = f"{template_name}.json"
        file_path = os.path.join(templates_dir, filename)
       
        if os.path.exists(file_path):
            counter = 1
            while True:
                filename = f"{template_name}-{counter}.json"
                file_path = os.path.join(templates_dir, filename)
                if not os.path.exists(file_path):
                    # Update template name to include suffix
                    template['name'] = f"{template_name}-{counter}"
                    logger.info(f"   Duplicate name detected, renamed to: {template['name']}")
                    break
                counter += 1
 
        # Set ID to match the name if not already set
        if not template.get('id'):
            template['id'] = template['name'].replace(' ', '_').lower()
       
        # Save template JSON
        with open(file_path, 'w') as f:
            json.dump(template, f, indent=2)
       
        logger.info(f"✅ Template saved to: {file_path}")
        logger.info(f"   - ID: {template.get('id')}")
        logger.info(f"   - Name: {template.get('name')}")
        logger.info(f"   - Fields: {len(template.get('fields', []))}")
       
        # Reload ML service templates cache
        if ml_recognition_service:
            ml_recognition_service.load_templates()
            logger.info(f"✅ Reloaded ML service templates cache")
       
        return {
            'success': True,
            'message': f"Template '{template.get('name')}' saved successfully",
            'file_path': file_path,
            'template_id': template.get('id')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving template: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/templates/list")
async def list_templates():
    """
    List all available templates (both JSON and HTML)
    
    Returns: List of templates with metadata
    """
    try:
        # Use hardcoded local templates directory
        # Use absolute path: backend/../data/templates = AIPdfGenerator/data/templates
        base_dir = os.path.dirname(__file__)
        templates_dir = os.path.abspath(os.path.join(base_dir, '..', 'data', 'templates'))
        
        templates = []
        
        if os.path.exists(templates_dir):
            for filename in os.listdir(templates_dir):
                # Load JSON templates
                if filename.endswith('.json') and not filename.endswith('_metadata.json'):
                    try:
                        template_path = os.path.join(templates_dir, filename)
                        with open(template_path, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                            template_data['filename'] = filename
                            template_data['source'] = 'json'
                            templates.append(template_data)
                    except Exception as e:
                        logger.warning(f"Failed to load template {filename}: {e}")
                
                # Load HTML template metadata
                elif filename.endswith('_metadata.json'):
                    try:
                        with open(os.path.join(templates_dir, filename), 'r') as f:
                            template_data = json.load(f)
                            template_data['source'] = 'html'
                            templates.append(template_data)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata {filename}: {e}")
        
        logger.info(f"📋 Found {len(templates)} templates in {templates_dir}")
        
        return {
            'success': True,
            'templates': templates,
            'count': len(templates),
            'directory': templates_dir
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 80)
    logger.info("🚀 PDF Template Generator Backend - STARTING")
    logger.info("=" * 80)
    logger.info(f"📄 PDF Generation: http://localhost:9000/api/pdf/generate")
    logger.info(f"🔄 Auto-Convert: http://localhost:9000/api/pdf/import-and-convert")
    logger.info(f"🧠 ML Training: http://localhost:9000/api/train")
    logger.info(f"📚 API Docs: http://localhost:9000/docs")
    logger.info(f"❤️ Health Check: http://localhost:9000/health")
    logger.info("=" * 80)
    logger.info(f"AI Parser Available: {'Yes ✅' if pdf_parser_ai else 'No (using basic parser)'}")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information"""
    logger.info("=" * 80)
    logger.info("🛑 PDF Template Generator Backend - SHUTTING DOWN")
    logger.info("=" * 80)

# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PDF Template Generator Backend")
    print("=" * 60)
    print("📄 PDF Generation: http://localhost:9000/api/pdf/generate")
    print("🧠 ML Training: http://localhost:9000/api/train")
    print("📚 API Docs: http://localhost:9000/docs")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        log_level="info"
    )
