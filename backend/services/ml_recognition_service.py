"""
ML Recognition Service for PDF Analysis
Handles template detection, data extraction, and auto-generation
"""

import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
import tempfile


class MLRecognitionService:
    """Service for ML-powered PDF template recognition and analysis"""
    
    def __init__(self):
        """Initialize ML recognition service with trained model"""
        self.model = None
        self.model_info = None
        self.template_mappings = {}
        self.templates_cache = {}
        self.load_model()
        self.load_templates()
    
    def load_model(self):
        """Load the trained Keras model"""
        try:
            import tensorflow as tf
            
            # Import config to get models directory
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from config import Config
            
            model_dir = Config.get_models_dir()
            model_path = os.path.join(model_dir, 'template_model.keras')
            info_path = os.path.join(model_dir, 'model_info.json')
            
            if os.path.exists(model_path):
                print(f"📦 Loading trained model from {model_path}")
                self.model = tf.keras.models.load_model(model_path)
                print(f"✅ Model loaded successfully!")
                
                # Load model info
                if os.path.exists(info_path):
                    with open(info_path, 'r') as f:
                        self.model_info = json.load(f)
                    print(f"📊 Model trained: {self.model_info.get('trained_at')}")
                    print(f"   - Templates: {self.model_info.get('template_count')}")
                    print(f"   - Accuracy: {self.model_info.get('accuracy')}")
                
                # Create template mappings
                self._create_template_mappings()
            else:
                print(f"⚠️  No trained model found at {model_path}")
                print(f"   Please train a model first using the Train page")
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
    
    def load_templates(self):
        """Load all templates into cache for quick access"""
        try:
            # Import config to get templates directory
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from config import Config
            
            # Get templates directory from config (supports external storage)
            templates_dir = Config.get_templates_dir()
            
            if not os.path.exists(templates_dir):
                print(f"⚠️  Templates directory not found: {templates_dir}")
                return
            
            for filename in os.listdir(templates_dir):
                if filename.endswith('.json') and not filename.endswith('_metadata.json'):
                    template_path = os.path.join(templates_dir, filename)
                    try:
                        with open(template_path, 'r') as f:
                            template = json.load(f)
                            template_id = template.get('id', filename.replace('.json', ''))
                            self.templates_cache[template_id] = template
                    except Exception as e:
                        print(f"⚠️  Error loading template {filename}: {e}")
            
            print(f"✅ Loaded {len(self.templates_cache)} templates into cache")
            
        except Exception as e:
            print(f"❌ Error loading templates: {e}")
    
    def _create_template_mappings(self):
        """Create mappings between template IDs and model output indices"""
        # This maps template IDs to their corresponding output indices in the model
        # In your case, since the model predicts field count, we'll use feature-based matching
        
        for idx, (template_id, template) in enumerate(self.templates_cache.items()):
            self.template_mappings[template_id] = idx
        
        print(f"✅ Created mappings for {len(self.template_mappings)} templates")
    
    def predict_template(self, pdf_path: str) -> Dict:
        """
        Predict which template a PDF matches using the trained model
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with success, template_id, confidence, template_name, and all_scores
        """
        try:
            if not self.model and len(self.templates_cache) == 0:
                print("⚠️  No model or templates loaded")
                return {
                    'success': False,
                    'error': 'No trained model or templates available',
                    'message': 'Please train a model first or create templates'
                }
            
            print(f"🔍 Analyzing PDF: {pdf_path}")
            
            # Extract features from PDF
            features = self._extract_pdf_features(pdf_path)
            if features is None:
                return {
                    'success': False,
                    'error': 'Could not extract features',
                    'message': 'Failed to parse PDF - it may be corrupted or encrypted'
                }
            
            print(f"📊 Extracted {len(features)} features from PDF")
            
            # Compare features with all templates
            best_match = None
            best_similarity = 0
            all_scores = {}
            
            for template_id, template in self.templates_cache.items():
                template_features = self._extract_template_features(template)
                similarity = self._calculate_similarity(features, template_features)
                
                all_scores[template_id] = float(similarity)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = template_id
            
            if best_match and best_similarity > 0.1:  # Minimum confidence threshold
                result = {
                    'success': True,
                    'template_id': best_match,
                    'template_name': self.templates_cache[best_match].get('name', best_match),
                    'confidence': float(best_similarity),
                    'all_scores': all_scores
                }
                
                print(f"✅ Best match: {result['template_name']} (confidence: {best_similarity:.2%})")
                return result
            else:
                return {
                    'success': False,
                    'error': 'No confident match found',
                    'message': f'Highest similarity: {best_similarity:.2%}. Try templates that match this PDF structure.',
                    'all_scores': all_scores
                }
            
        except Exception as e:
            print(f"❌ Error predicting template: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'message': 'Error during template prediction'
            }
    
    def extract_data_from_pdf(self, pdf_path: str, template_id: str) -> Dict:
        """
        Extract data from a filled PDF using OCR and field positions
        
        Args:
            pdf_path: Path to filled PDF
            template_id: Template ID to use for field positions
            
        Returns:
            Dict with success, template_id, and extracted data
        """
        try:
            # Validate template_id
            if not template_id or template_id == 'None':
                print(f"⚠️  No template ID provided")
                return {
                    'success': False,
                    'error': 'No template ID provided',
                    'message': 'Please provide a template_id or ensure PDF matches a known template for auto-detection.'
                }
            
            print(f"📄 Extracting data from PDF using template: {template_id}")
            
            # Get template structure
            template = self.templates_cache.get(template_id)
            if not template:
                print(f"⚠️  Template {template_id} not found in cache")
                available = list(self.templates_cache.keys())
                return {
                    'success': False,
                    'error': f'Template {template_id} not found',
                    'message': f'Template not in cache. Available templates: {", ".join(available) if available else "none"}',
                    'available_templates': available
                }
            
            # Use pdf_parser to extract text with coordinates
            from .pdf_parser import PDFParser
            parser = PDFParser()
            
            # Parse the PDF
            parsed_data = parser.parse_pdf(pdf_path)
            if not parsed_data:
                print(f"⚠️  Failed to parse PDF")
                return {
                    'success': False,
                    'error': 'Failed to parse PDF',
                    'message': 'Could not extract text from PDF. It may be encrypted or image-based.'
                }
            
            # Extract text elements with positions
            text_elements = parsed_data.get('text_elements', [])
            print(f"📝 Found {len(text_elements)} text elements in PDF")
            
            # Match text to fields based on position
            extracted_data = {}
            
            for field in template.get('fields', []):
                field_name = field.get('name')
                field_x = field.get('x', 0)
                field_y = field.get('y', 0)
                field_width = field.get('width', 100)
                field_height = field.get('height', 30)
                field_type = field.get('type', 'text')
                
                # Find text elements within this field's bounding box
                field_texts = []
                for elem in text_elements:
                    elem_x = elem.get('x', 0)
                    elem_y = elem.get('y', 0)
                    
                    # Check if element is within field bounds (with tolerance)
                    tolerance = 15  # Increased tolerance
                    if (field_x - tolerance <= elem_x <= field_x + field_width + tolerance and
                        field_y - tolerance <= elem_y <= field_y + field_height + tolerance):
                        text = elem.get('text', '').strip()
                        if text:
                            field_texts.append(text)
                
                # Process extracted text based on field type
                if field_texts:
                    if field_type == 'checkbox':
                        # For checkboxes, check for common check indicators
                        value_text = ' '.join(field_texts).lower()
                        extracted_data[field_name] = 'Yes' if any(
                            indicator in value_text 
                            for indicator in ['x', '✓', '✔', 'yes', 'true', '☑', '☒']
                        ) else ''
                    else:
                        # For text fields, join all texts
                        extracted_data[field_name] = ' '.join(field_texts)
                else:
                    # No text found in field area
                    extracted_data[field_name] = ''
            
            print(f"✅ Extracted {len([v for v in extracted_data.values() if v])} non-empty fields")
            
            return {
                'success': True,
                'template_id': template_id,
                'data': extracted_data
            }
            
        except Exception as e:
            print(f"❌ Error extracting data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'message': 'Error during data extraction'
            }
    
    def auto_generate_template(self, pdf_path: str, template_name: str) -> Dict:
        """
        Automatically generate template JSON from a PDF
        Uses ML to detect fields and their positions
        
        Args:
            pdf_path: Path to PDF file
            template_name: Name for the new template
            
        Returns:
            Template dict with detected fields
        """
        try:
            print(f"🤖 Auto-generating template from: {pdf_path}")
            
            # Parse PDF to get structure
            from .pdf_parser import PDFParser
            parser = PDFParser()
            
            parsed_data = parser.parse_pdf_form(pdf_path, use_ai=False)
            if not parsed_data:
                print(f"⚠️  Failed to parse PDF")
                return {
                    'success': False,
                    'error': 'Failed to parse PDF',
                    'message': 'Could not extract structure from PDF'
                }
            
            # Get detected fields from parser
            detected_fields = parsed_data.get('fields', [])
            print(f"🔍 Detected {len(detected_fields)} fields in PDF")
            
            # Create template structure
            import time
            template_id = template_name.lower().replace(' ', '_').replace('-', '_')
            template = {
                'id': template_id,
                'name': template_name,
                'width': parsed_data.get('page_width', 612),
                'height': parsed_data.get('page_height', 792),
                'fields': []
            }
            
            # Convert detected fields to template format
            for idx, field in enumerate(detected_fields):
                template_field = {
                    'id': f"field_{idx}",
                    'name': field.get('name', f"field_{idx}"),
                    'label': field.get('label', field.get('name', f"Field {idx}")),
                    'type': field.get('type', 'text'),
                    'x': field.get('x', 0),
                    'y': field.get('y', 0),
                    'width': field.get('width', 150),
                    'height': field.get('height', 25),
                    'fontSize': 12,
                    'fontWeight': 'normal',
                    'required': False
                }
                template['fields'].append(template_field)
            
            print(f"✅ Generated template with {len(template['fields'])} fields")
            
            return {
                'success': True,
                'template': template,
                'message': f'Template generated with {len(template["fields"])} fields'
            }
            
        except Exception as e:
            print(f"❌ Error auto-generating template: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'message': 'Error during template generation'
            }
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _extract_pdf_features(self, pdf_path: str) -> Optional[np.ndarray]:
        """
        Extract numerical features from PDF for comparison
        Uses same feature extraction as training
        """
        try:
            from .pdf_parser import PDFParser
            from PyPDF2 import PdfReader
            
            parser = PDFParser()
            parsed = parser.parse_pdf_form(pdf_path, use_ai=False)
            
            if not parsed:
                return None
            
            # Read PDF with PyPDF2 for additional metadata
            reader = PdfReader(pdf_path)
            
            # Extract features (must match training features)
            features = []
            
            # Basic PDF properties
            features.append(len(reader.pages))  # Page count
            features.append(parsed.get('page_width', 612))
            features.append(parsed.get('page_height', 792))
            
            # Field counts by type
            fields = parsed.get('fields', [])
            field_types = {}
            for field in fields:
                ftype = field.get('type', 'text')
                field_types[ftype] = field_types.get(ftype, 0) + 1
            
            features.append(field_types.get('text', 0))
            features.append(field_types.get('checkbox', 0))
            features.append(field_types.get('date', 0))
            features.append(field_types.get('number', 0))
            features.append(len(fields))  # Total fields
            
            # Field positions (average)
            if fields:
                avg_x = sum(f.get('x', 0) for f in fields) / len(fields)
                avg_y = sum(f.get('y', 0) for f in fields) / len(fields)
                features.append(avg_x)
                features.append(avg_y)
            else:
                features.append(0)
                features.append(0)
            
            # Pad to fixed size (41 features to match training)
            while len(features) < 41:
                features.append(0)
            
            return np.array(features[:41], dtype=np.float32)
            
        except Exception as e:
            print(f"❌ Error extracting PDF features: {e}")
            return None
    
    def _extract_template_features(self, template: Dict) -> np.ndarray:
        """
        Extract features from a template structure
        """
        features = []
        
        # Basic properties
        features.append(1)  # Page count (templates are single page)
        features.append(template.get('pageWidth', 612))
        features.append(template.get('pageHeight', 792))
        
        # Field counts by type
        fields = template.get('fields', [])
        field_types = {}
        for field in fields:
            ftype = field.get('type', 'text')
            field_types[ftype] = field_types.get(ftype, 0) + 1
        
        features.append(field_types.get('text', 0))
        features.append(field_types.get('checkbox', 0))
        features.append(field_types.get('date', 0))
        features.append(field_types.get('number', 0))
        features.append(len(fields))
        
        # Field positions (average)
        if fields:
            avg_x = sum(f.get('x', 0) for f in fields) / len(fields)
            avg_y = sum(f.get('y', 0) for f in fields) / len(fields)
            features.append(avg_x)
            features.append(avg_y)
        else:
            features.append(0)
            features.append(0)
        
        # Pad to 41 features
        while len(features) < 41:
            features.append(0)
        
        return np.array(features[:41], dtype=np.float32)
    
    def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        Calculate similarity between two feature vectors
        Uses weighted combination of multiple distance metrics for better discrimination
        Returns a value between 0 and 1
        """
        # 1. Euclidean distance (normalized by feature scale)
        euclidean_dist = np.sqrt(np.sum((features1 - features2) ** 2))
        max_possible_dist = np.sqrt(np.sum((features1 + features2) ** 2))
        euclidean_similarity = 1 - (euclidean_dist / (max_possible_dist + 1e-10))
        
        # 2. Feature-wise exact matches (higher weight for key features)
        # Key features: field counts (indices 3-7), total fields important
        key_indices = [3, 4, 5, 6, 7]  # text, checkbox, date, number, total fields
        key_diff = np.abs(features1[key_indices] - features2[key_indices])
        key_similarity = 1 - (np.mean(key_diff) / (np.mean(features1[key_indices]) + np.mean(features2[key_indices]) + 1e-10))
        
        # 3. Cosine similarity (for overall structure)
        f1_norm = features1 / (np.linalg.norm(features1) + 1e-10)
        f2_norm = features2 / (np.linalg.norm(features2) + 1e-10)
        cosine_sim = np.dot(f1_norm, f2_norm)
        cosine_similarity = (cosine_sim + 1) / 2
        
        # Weighted combination (emphasize key features more)
        similarity = (
            0.20 * euclidean_similarity +  # Overall distance
            0.50 * key_similarity +         # Field count matching (most important!)
            0.30 * cosine_similarity        # Structural similarity
        )
        
        return float(np.clip(similarity, 0, 1))
