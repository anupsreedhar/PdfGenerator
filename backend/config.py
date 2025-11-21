"""
Configuration Management for AI PDF Generator
Centralized configuration for paths, storage, and system settings
"""

import os
from typing import Optional


class Config:
    """Application configuration with support for external storage paths"""
    
    # ========================================================================
    # STORAGE CONFIGURATION
    # ========================================================================
    
    # Option 1: Use environment variable for external template storage
    # Set this in your system environment: TEMPLATE_STORAGE_PATH=C:\MyCompany\Templates
    EXTERNAL_TEMPLATES_DIR = os.getenv('TEMPLATE_STORAGE_PATH', None)
    
    # Option 2: Use a hardcoded external path (uncomment and set your path)
    # EXTERNAL_TEMPLATES_DIR = r"C:\MyCompany\Templates"
    # EXTERNAL_TEMPLATES_DIR = r"D:\SharedDrive\PDFTemplates"
    # EXTERNAL_TEMPLATES_DIR = r"\\NetworkServer\Shared\Templates"
    
    # Fallback to local path if no external path is configured
    @staticmethod
    def get_templates_dir() -> str:
        """Get the templates directory path (external or local)"""
        if Config.EXTERNAL_TEMPLATES_DIR and os.path.exists(Config.EXTERNAL_TEMPLATES_DIR):
            templates_dir = Config.EXTERNAL_TEMPLATES_DIR
            print(f"📁 Using EXTERNAL templates directory: {templates_dir}")
        else:
            # Default to local data/templates
            base_dir = os.path.dirname(__file__)
            templates_dir = os.path.abspath(os.path.join(base_dir, '..', 'data', 'templates'))
            
            if Config.EXTERNAL_TEMPLATES_DIR:
                print(f"⚠️  External path configured but not found: {Config.EXTERNAL_TEMPLATES_DIR}")
                print(f"📁 Falling back to LOCAL templates directory: {templates_dir}")
            else:
                print(f"📁 Using LOCAL templates directory: {templates_dir}")
        
        # Create directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)
        
        return templates_dir
    
    @staticmethod
    def get_templates_pdfs_dir() -> str:
        """Get the PDF templates subdirectory"""
        templates_dir = Config.get_templates_dir()
        pdfs_dir = os.path.join(templates_dir, 'pdfs')
        os.makedirs(pdfs_dir, exist_ok=True)
        return pdfs_dir
    
    # ========================================================================
    # MODEL STORAGE CONFIGURATION
    # ========================================================================
    
    # Option: Store ML models externally as well
    EXTERNAL_MODELS_DIR = os.getenv('MODEL_STORAGE_PATH', None)
    
    @staticmethod
    def get_models_dir() -> str:
        """Get the ML models directory path"""
        if Config.EXTERNAL_MODELS_DIR and os.path.exists(Config.EXTERNAL_MODELS_DIR):
            models_dir = Config.EXTERNAL_MODELS_DIR
            print(f"📦 Using EXTERNAL models directory: {models_dir}")
        else:
            base_dir = os.path.dirname(__file__)
            models_dir = os.path.abspath(os.path.join(base_dir, 'ml_models'))
            
            if Config.EXTERNAL_MODELS_DIR:
                print(f"⚠️  External models path configured but not found: {Config.EXTERNAL_MODELS_DIR}")
                print(f"📦 Falling back to LOCAL models directory: {models_dir}")
            else:
                print(f"📦 Using LOCAL models directory: {models_dir}")
        
        os.makedirs(models_dir, exist_ok=True)
        return models_dir
    
    # ========================================================================
    # TEMP FILES CONFIGURATION
    # ========================================================================
    
    @staticmethod
    def get_temp_dir() -> str:
        """Get temporary files directory"""
        base_dir = os.path.dirname(__file__)
        temp_dir = os.path.abspath(os.path.join(base_dir, 'temp'))
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    # ========================================================================
    # SERVER CONFIGURATION
    # ========================================================================
    
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', 9000))
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @staticmethod
    def set_external_templates_dir(path: str) -> bool:
        """
        Programmatically set external templates directory
        
        Args:
            path: Absolute path to external templates directory
            
        Returns:
            bool: True if path is valid and set successfully
        """
        if os.path.isabs(path):
            os.makedirs(path, exist_ok=True)
            Config.EXTERNAL_TEMPLATES_DIR = path
            print(f"✅ External templates directory set to: {path}")
            return True
        else:
            print(f"❌ Invalid path (must be absolute): {path}")
            return False
    
    @staticmethod
    def print_config():
        """Print current configuration"""
        print("\n" + "=" * 80)
        print("📋 AI PDF GENERATOR - CONFIGURATION")
        print("=" * 80)
        print(f"📁 Templates Directory: {Config.get_templates_dir()}")
        print(f"📄 PDFs Directory:      {Config.get_templates_pdfs_dir()}")
        print(f"📦 Models Directory:    {Config.get_models_dir()}")
        print(f"🗂️  Temp Directory:      {Config.get_temp_dir()}")
        print(f"🌐 Server:              {Config.HOST}:{Config.PORT}")
        print("=" * 80 + "\n")


# ========================================================================
# EXAMPLE USAGE
# ========================================================================

if __name__ == "__main__":
    """
    Example usage of Config class
    
    You can test different configurations by running:
        python config.py
    
    To set external path via environment variable (Windows):
        set TEMPLATE_STORAGE_PATH=C:\MyCompany\Templates
        python app.py
    
    To set external path via environment variable (Linux/Mac):
        export TEMPLATE_STORAGE_PATH=/opt/company/templates
        python app.py
    """
    
    print("\n🧪 Configuration Test\n")
    
    # Print current config
    Config.print_config()
    
    # Example: Set external path programmatically
    # Config.set_external_templates_dir(r"C:\ExternalStorage\Templates")
    # Config.print_config()
