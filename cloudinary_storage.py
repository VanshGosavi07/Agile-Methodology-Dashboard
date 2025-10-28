"""
Cloudinary Storage Integration for Agile Dashboard
Handles file uploads to Cloudinary and returns public URLs
"""

import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Cloudinary
def initialize_cloudinary():
    """Initialize Cloudinary with credentials from environment variables"""
    try:
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'day2zovp3'),
            api_key=os.getenv('CLOUDINARY_API_KEY', '995247322466511'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET'),
            secure=True
        )
        print("[Cloudinary] Successfully configured")
        return True
    except Exception as e:
        print(f"[Cloudinary] Configuration error: {str(e)}")
        return False


def upload_file_to_cloudinary(file, folder_name, user_id=None):
    """
    Upload a file to Cloudinary
    
    Args:
        file: FileStorage object from Flask request
        folder_name: Folder name in Cloudinary (e.g., 'profile_images', 'reports', 'csv_files')
        user_id: Optional user ID for organizing files
        
    Returns:
        tuple: (success, public_url or error_message)
    """
    try:
        initialize_cloudinary()
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Generate unique public_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_extension = os.path.splitext(filename)[1].replace('.', '')
        
        # Create folder path
        if user_id:
            public_id = f"{folder_name}/{user_id}/{timestamp}_{unique_id}"
        else:
            public_id = f"{folder_name}/{timestamp}_{unique_id}"
        
        # Reset file pointer to beginning
        file.seek(0)
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            public_id=public_id,
            resource_type='auto',  # auto-detect file type (image, video, raw)
            folder=folder_name
        )
        
        # Get secure URL
        secure_url = upload_result.get('secure_url')
        
        print(f"[Cloudinary] File uploaded successfully: {public_id}")
        print(f"[Cloudinary] Secure URL: {secure_url}")
        
        return True, secure_url
        
    except Exception as e:
        print(f"[Cloudinary] Upload error: {str(e)}")
        return False, str(e)


def upload_local_file_to_cloudinary(local_path, folder_name, user_id=None):
    """
    Upload a local file to Cloudinary
    
    Args:
        local_path: Path to local file
        folder_name: Folder name in Cloudinary
        user_id: Optional user ID for organizing files
        
    Returns:
        tuple: (success, public_url or error_message)
    """
    try:
        initialize_cloudinary()
        
        if not os.path.exists(local_path):
            return False, "File not found"
        
        # Get filename
        filename = os.path.basename(local_path)
        
        # Generate unique public_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        # Create folder path
        if user_id:
            public_id = f"{folder_name}/{user_id}/{timestamp}_{unique_id}"
        else:
            public_id = f"{folder_name}/{timestamp}_{unique_id}"
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            local_path,
            public_id=public_id,
            resource_type='auto',
            folder=folder_name
        )
        
        # Get secure URL
        secure_url = upload_result.get('secure_url')
        
        print(f"[Cloudinary] Local file uploaded: {public_id}")
        print(f"[Cloudinary] Secure URL: {secure_url}")
        
        return True, secure_url
        
    except Exception as e:
        print(f"[Cloudinary] Upload error: {str(e)}")
        return False, str(e)


def delete_file_from_cloudinary(file_url):
    """
    Delete a file from Cloudinary using its public URL
    
    Args:
        file_url: Public URL of the file
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        initialize_cloudinary()
        
        # Extract public_id from URL
        # URL format: https://res.cloudinary.com/cloud_name/image/upload/v123456/folder/file.jpg
        if 'cloudinary.com' in file_url:
            parts = file_url.split('/')
            # Find 'upload' index and get everything after version
            if 'upload' in parts:
                upload_idx = parts.index('upload')
                # Skip version (v123456) if present
                start_idx = upload_idx + 2 if parts[upload_idx + 1].startswith('v') else upload_idx + 1
                public_id_parts = parts[start_idx:]
                # Remove file extension
                public_id_parts[-1] = os.path.splitext(public_id_parts[-1])[0]
                public_id = '/'.join(public_id_parts)
                
                # Delete from Cloudinary
                result = cloudinary.uploader.destroy(public_id)
                
                if result.get('result') == 'ok':
                    print(f"[Cloudinary] File deleted: {public_id}")
                    return True
        
        return False
        
    except Exception as e:
        print(f"[Cloudinary] Delete error: {str(e)}")
        return False


def optimize_image_url(file_url, width=500, height=500, crop="auto"):
    """
    Get optimized image URL with transformations
    
    Args:
        file_url: Original Cloudinary URL
        width: Target width
        height: Target height
        crop: Crop mode (auto, fill, scale, etc.)
        
    Returns:
        str: Optimized URL
    """
    try:
        # Extract public_id from URL
        if 'cloudinary.com' in file_url:
            parts = file_url.split('/')
            if 'upload' in parts:
                upload_idx = parts.index('upload')
                start_idx = upload_idx + 2 if parts[upload_idx + 1].startswith('v') else upload_idx + 1
                public_id_parts = parts[start_idx:]
                public_id_parts[-1] = os.path.splitext(public_id_parts[-1])[0]
                public_id = '/'.join(public_id_parts)
                
                # Generate optimized URL
                optimized_url, _ = cloudinary_url(
                    public_id,
                    width=width,
                    height=height,
                    crop=crop,
                    gravity="auto",
                    fetch_format="auto",
                    quality="auto"
                )
                
                return optimized_url
        
        return file_url
        
    except Exception as e:
        print(f"[Cloudinary] Optimization error: {str(e)}")
        return file_url


# Helper functions for specific file types

def upload_profile_image(file, user_id):
    """Upload profile image to Cloudinary"""
    return upload_file_to_cloudinary(file, 'profile_images', user_id)


def upload_report_pdf(local_path, user_id=None):
    """Upload PDF report to Cloudinary"""
    return upload_local_file_to_cloudinary(local_path, 'reports', user_id)


def upload_csv_file(local_path, user_id=None):
    """Upload CSV file to Cloudinary"""
    return upload_local_file_to_cloudinary(local_path, 'csv_files', user_id)


def delete_profile_image(image_url):
    """Delete profile image from Cloudinary"""
    return delete_file_from_cloudinary(image_url)
