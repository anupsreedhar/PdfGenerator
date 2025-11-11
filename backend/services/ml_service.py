"""
ML Training Service using TensorFlow
"""

import tensorflow as tf
import numpy as np
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid


class MLService:
    """
    Service for ML model training and template generation
    """
    
    def __init__(self):
        """Initialize ML service"""
        self.model = None
        self.model_dir = "ml_models"
        self.training_tasks = {}
        
        # Create model directory
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Try to load existing model
        self._try_load_model()
    
    def train_model(self, templates: List[Dict], config: Dict) -> Dict:
        """
        Train ML model on templates
        
        Args:
            templates: List of template dictionaries
            config: Training configuration
            
        Returns:
            dict: Training results
        """
        print(f"🧠 Starting ML training with {len(templates)} templates...")
        
        start_time = datetime.now()
        
        # Generate synthetic templates if needed
        if config.get('generate_synthetic') and len(templates) < config.get('min_templates', 10):
            print(f"📊 Generating synthetic templates...")
            templates = self._generate_synthetic_templates(templates, config['min_templates'])
        
        # Extract features from templates
        print("🔍 Extracting features...")
        X, y = self._extract_features(templates)
        
        # Build model
        print("🏗️ Building neural network...")
        self.model = self._build_model(X.shape[1])
        
        # Train model
        print(f"🎯 Training for {config['epochs']} epochs...")
        history = self.model.fit(
            X, y,
            epochs=config['epochs'],
            batch_size=config['batch_size'],
            validation_split=0.2,
            verbose=0
        )
        
        # Save model
        model_path = os.path.join(self.model_dir, "template_model.keras")
        self.model.save(model_path)
        print(f"💾 Model saved to {model_path}")
        
        # Save metadata
        end_time = datetime.now()
        training_time = (end_time - start_time).total_seconds()
        
        metadata = {
            "trained_at": end_time.isoformat(),
            "template_count": len(templates),
            "epochs": config['epochs'],
            "batch_size": config['batch_size'],
            "training_time": f"{training_time:.2f}s",
            "final_loss": float(history.history['loss'][-1]),
            "final_val_loss": float(history.history['val_loss'][-1]) if 'val_loss' in history.history else None,
            "accuracy": f"{(1 - history.history['loss'][-1]) * 100:.2f}%"
        }
        
        metadata_path = os.path.join(self.model_dir, "model_info.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("✅ Training complete!")
        
        return metadata
    
    def create_training_task(self, templates: List[Dict], config: Dict) -> str:
        """
        Create a background training task
        """
        task_id = str(uuid.uuid4())
        self.training_tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Initializing...",
            "result": None,
            "error": None
        }
        return task_id
    
    async def train_async(self, task_id: str, templates: List[Dict], config: Dict):
        """
        Train model asynchronously
        """
        try:
            self.training_tasks[task_id]["status"] = "running"
            self.training_tasks[task_id]["progress"] = 10
            self.training_tasks[task_id]["message"] = "Training started..."
            
            result = self.train_model(templates, config)
            
            self.training_tasks[task_id]["status"] = "complete"
            self.training_tasks[task_id]["progress"] = 100
            self.training_tasks[task_id]["result"] = result
            
        except Exception as e:
            self.training_tasks[task_id]["status"] = "error"
            self.training_tasks[task_id]["error"] = str(e)
    
    def get_training_status(self, task_id: str) -> Optional[Dict]:
        """
        Get training task status
        """
        return self.training_tasks.get(task_id)
    
    def is_model_loaded(self) -> bool:
        """
        Check if model is loaded
        """
        return self.model is not None
    
    def get_model_info(self) -> Dict:
        """
        Get model information
        """
        info_path = os.path.join(self.model_dir, "model_info.json")
        
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                return json.load(f)
        
        return {
            "status": "not_trained",
            "message": "No model found"
        }
    
    def generate_template(self, template_type: str) -> Dict:
        """
        Generate a new template using the trained model
        """
        if not self.model:
            raise Exception("Model not loaded. Please train the model first.")
        
        # Generate random input
        random_input = np.random.randn(1, 100)  # Adjust size based on your model
        
        # Predict
        prediction = self.model.predict(random_input)
        
        # Convert prediction to template
        template = self._prediction_to_template(prediction, template_type)
        
        return template
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _try_load_model(self):
        """
        Try to load existing model
        """
        model_path = os.path.join(self.model_dir, "template_model.keras")
        
        if os.path.exists(model_path):
            try:
                self.model = tf.keras.models.load_model(model_path)
                print(f"✅ Loaded existing model from {model_path}")
            except Exception as e:
                print(f"⚠️ Failed to load model: {e}")
    
    def _generate_synthetic_templates(self, templates: List[Dict], target_count: int) -> List[Dict]:
        """
        Generate synthetic templates based on existing ones
        """
        synthetic = list(templates)
        
        while len(synthetic) < target_count:
            # Pick random template
            base = np.random.choice(templates)
            
            # Create variation
            new_template = self._create_template_variation(base)
            synthetic.append(new_template)
        
        return synthetic
    
    def _create_template_variation(self, base_template: Dict) -> Dict:
        """
        Create a variation of a template
        """
        import copy
        variation = copy.deepcopy(base_template)
        
        # Modify fields slightly
        for field in variation.get('fields', []):
            # Add random offset to position
            field['x'] += np.random.randint(-20, 20)
            field['y'] += np.random.randint(-20, 20)
            
            # Vary size slightly
            field['width'] = int(field['width'] * np.random.uniform(0.8, 1.2))
            field['height'] = int(field['height'] * np.random.uniform(0.8, 1.2))
        
        variation['name'] = f"{base_template['name']}_variant_{np.random.randint(1000, 9999)}"
        
        return variation
    
    def _extract_features(self, templates: List[Dict]):
        """
        Extract features from templates for training
        """
        features = []
        labels = []
        
        for template in templates:
            # Extract field count, positions, sizes
            num_fields = len(template.get('fields', []))
            
            # Create feature vector
            feature_vector = [num_fields]
            
            for field in template.get('fields', [])[:10]:  # Max 10 fields
                feature_vector.extend([
                    field.get('x', 0) / 612,  # Normalize
                    field.get('y', 0) / 792,
                    field.get('width', 0) / 612,
                    field.get('height', 0) / 792,
                ])
            
            # Pad to fixed size
            while len(feature_vector) < 41:  # 1 + 10*4
                feature_vector.append(0)
            
            features.append(feature_vector)
            
            # Label is template type (simplified)
            labels.append(num_fields / 20.0)  # Normalize
        
        return np.array(features), np.array(labels)
    
    def _build_model(self, input_size: int):
        """
        Build neural network model
        """
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(input_size,)),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def _prediction_to_template(self, prediction, template_type: str) -> Dict:
        """
        Convert model prediction to template
        """
        # Simplified template generation
        num_fields = int(prediction[0] * 20)  # Denormalize
        
        fields = []
        for i in range(num_fields):
            fields.append({
                "name": f"field_{i}",
                "type": "text",
                "label": f"Field {i}",
                "x": 50 + (i % 2) * 300,
                "y": 100 + (i // 2) * 80,
                "width": 200,
                "height": 30
            })
        
        return {
            "name": f"Generated_{template_type}",
            "fields": fields,
            "pageWidth": 612,
            "pageHeight": 792
        }
