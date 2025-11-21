"""
Batch Generate Templates from PDFs

This script automatically creates JSON templates from all PDF files
in the data/templates/pdfs/ folder.

Usage:
    cd backend
    python create_templates_from_pdfs.py
"""

import os
import json
import sys

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ml_recognition_service import MLRecognitionService
from config import Config


def batch_create_templates():
    """Create JSON templates from all PDFs in pdfs folder"""
    
    print("=" * 80)
    print("📄 BATCH TEMPLATE GENERATOR")
    print("=" * 80)
    
    # Get directories from config (supports external storage)
    pdfs_dir = Config.get_templates_pdfs_dir()
    output_dir = Config.get_templates_dir()
    
    print(f"\n📁 PDF Directory: {pdfs_dir}")
    print(f"📁 Output Directory: {output_dir}\n")
    
    # Check directories exist
    if not os.path.exists(pdfs_dir):
        print(f"❌ Error: PDFs directory not found: {pdfs_dir}")
        return
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✅ Created output directory: {output_dir}\n")
    
    # Initialize ML service
    print("🤖 Initializing ML Recognition Service...")
    ml_service = MLRecognitionService()
    print("✅ Service initialized\n")
    
    # Get all PDF files
    pdf_files = sorted([f for f in os.listdir(pdfs_dir) if f.lower().endswith('.pdf')])
    
    if not pdf_files:
        print(f"❌ No PDF files found in {pdfs_dir}")
        return
    
    print(f"📄 Found {len(pdf_files)} PDF files\n")
    print("🔄 Generating templates...\n")
    
    created_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(pdfs_dir, pdf_file)
        
        # Create template name from filename
        template_name = pdf_file.replace('.pdf', '').replace('template_', 'tpl_')
        template_id = template_name.lower().replace(' ', '_')
        
        # Check if template already exists
        output_file = os.path.join(output_dir, f"{template_id}.json")
        
        if os.path.exists(output_file):
            print(f"[{i}/{len(pdf_files)}] ⏭️  Skipping: {pdf_file}")
            print(f"           Template already exists: {template_id}.json\n")
            skipped_count += 1
            continue
        
        print(f"[{i}/{len(pdf_files)}] 🔄 Processing: {pdf_file}")
        print(f"           Template ID: {template_id}")
        
        # Auto-generate template
        try:
            result = ml_service.auto_generate_template(pdf_path, template_name)
            
            if result.get('success'):
                template = result['template']
                
                # Save to JSON file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                
                print(f"           ✅ Created: {template_id}.json")
                print(f"           📊 Fields: {len(template.get('fields', []))}")
                print(f"           📐 Size: {template.get('width', 612)} x {template.get('height', 792)}\n")
                created_count += 1
            else:
                print(f"           ❌ Failed: {result.get('error', 'Unknown error')}")
                print(f"           💡 Message: {result.get('message', 'N/A')}\n")
                failed_count += 1
                
        except Exception as e:
            print(f"           ❌ Exception: {str(e)}\n")
            failed_count += 1
    
    # Summary
    print("=" * 80)
    print("📊 GENERATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully created: {created_count} templates")
    print(f"⏭️  Skipped (existing):  {skipped_count} templates")
    print(f"❌ Failed:              {failed_count} templates")
    print(f"📄 Total PDFs:          {len(pdf_files)}")
    print("=" * 80)
    
    if created_count > 0:
        print(f"\n🎉 Generated {created_count} new templates!")
        print(f"📁 Location: {output_dir}")
        print(f"\n💡 Next Steps:")
        print(f"   1. Review generated templates")
        print(f"   2. Go to http://localhost:9000/train.html")
        print(f"   3. Load all templates and retrain the model")
        print(f"   4. Expect 90%+ accuracy with {created_count + 2} real templates!")
    elif skipped_count == len(pdf_files):
        print(f"\n✅ All templates already exist!")
        print(f"📁 Location: {output_dir}")
        print(f"\n💡 You can proceed to retrain the model with existing templates")
    else:
        print(f"\n⚠️  Some templates failed to generate")
        print(f"   Check the error messages above for details")


if __name__ == "__main__":
    try:
        batch_create_templates()
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
