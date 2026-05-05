"""
Image generation tool using Gemini 3 Pro Image Preview (Nano Banana Pro).
Generates images from text prompts and saves them to storage.
Uses the same storage system as user uploads (UPLOAD_DIR) so it works with volume mounts.

Note: This is a TOOL, not an agent. It's called by agents (like the Synthesizer) when they need
to generate images. The model is fixed to gemini-3-pro-image-preview and cannot be changed
per-agent - this ensures consistent high-quality image generation.
"""
import os
import json
import uuid
import io
import time
import re
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from PIL import Image
from ...storage import UPLOAD_DIR, save_file, generate_unique_filename

# Get Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def generate_image(
    prompt: str,
    aspect_ratio: Optional[str] = "1:1",
    image_size: Optional[str] = "1K"
) -> str:
    """
    Generate an image from a text prompt using Gemini 3 Pro Image Preview model.

    Args:
        prompt: Text description of the image to generate
        aspect_ratio: Aspect ratio for the image (default: "1:1")
                     Options: "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
        image_size: Image size/resolution (default: "1K")
                    Options: "1K", "2K", "4K"

    Returns:
        JSON string with file information including:
        - file_path: Relative path to the saved image
        - filename: Generated filename
        - original_filename: Original filename for display
        - content_type: MIME type (image/png)
        - file_size: Size in bytes
    """
    # Enhance prompt with corporate styling guidelines
    corporate_styling_prefix = """Generate a professional, corporate-style strategic visualization diagram.

CRITICAL: Create ONLY the diagram/chart/visualization itself on a clean background. DO NOT add scene context like boardrooms, office settings, presentations, screens, or people viewing the content.

Design Guidelines:
- Create the actual diagram/chart/infographic directly (not a picture of it in a scene)
- Use clean, professional design aesthetic similar to Atlassian Design System or Material Design
- Professional color palettes (blues, grays, muted tones)
- Minimal decorative elements
- Data-focused charts and diagrams
- Suitable for executive presentations
- Avoid overly playful or casual elements
- Infographic style acceptable for strategic concepts
- Clear typography and hierarchy
- Clean white or subtle gradient background

Visualization Request: """

    # Combine corporate styling with user's prompt
    enhanced_prompt = corporate_styling_prefix + prompt

    # Single attempt - don't retry to avoid contributing to rate limiting
    # Return clear error messages so user/agent can decide when to retry
    try:
        # Generate image using Gemini 3 Pro Image Preview (Nano Banana Pro)
        # Model: gemini-3-pro-image-preview
        # Pricing: $2.00 input / $0.134 per generated image
        # Docs: https://ai.google.dev/gemini-api/docs/models#gemini-3-pro-image-preview
        # Following the official example pattern: https://ai.google.dev/gemini-api/docs/image-generation
        
        # Try to use ImageConfig if available, otherwise use dict or defaults
        # Handle case where ImageConfig may not exist in older library versions
        response = None
        config_error = None
        
        # First, try using typed config classes (preferred method)
        # Use getattr to safely check if classes exist without raising AttributeError
        ImageConfig = getattr(types, 'ImageConfig', None)
        GenerateContentConfig = getattr(types, 'GenerateContentConfig', None)
        
        if ImageConfig is not None and GenerateContentConfig is not None:
            try:
                response = client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=enhanced_prompt,
                    config=GenerateContentConfig(
                        image_config=ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=image_size
                        )
                    )
                )
            except Exception as e:
                # If typed config fails, try fallback methods
                config_error = e
                response = None
        
        # Note: Skip dict-based config fallback - GenerateContentConfig uses Pydantic validation
        # and doesn't accept image_config as a dict. If typed config fails, use defaults.
        
        # Fallback 2: Use defaults (no config)
        if response is None:
            if config_error:
                print(f"[WARNING] ImageConfig not available, using defaults: {config_error}")
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=enhanced_prompt
            )
        
        # Extract image from response
        # Official structure: response.candidates[0].content.parts[0].inline_data.data
        # Based on Google's official documentation and debug output showing data exists
        image = None
        
        # Get parts from response - try candidates structure first (standard)
        parts = None
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                parts = candidate.content.parts
        elif hasattr(response, 'parts'):
            parts = response.parts
        
        if not parts:
            raise ValueError("No parts found in response")
        
        # Extract image from parts - direct approach matching debug code that works
        for part in parts:
            # Try inline_data (snake_case - Python SDK standard)
            if hasattr(part, 'inline_data'):
                try:
                    inline_data = part.inline_data
                    if inline_data and hasattr(inline_data, 'data'):
                        # This is exactly what the debug code does - direct access
                        data = inline_data.data
                        mime_type = None
                        if hasattr(inline_data, 'mime_type'):
                            mime_type = inline_data.mime_type
                        
                        if data:
                            image_bytes = None
                            
                            # Handle bytes - try direct first, then base64 decode if needed
                            if isinstance(data, bytes) and len(data) > 0:
                                # First, try opening directly
                                try:
                                    test_img = Image.open(io.BytesIO(data))
                                    test_img.load()  # Force load to verify it's valid
                                    image_bytes = data
                                    print(f"[DEBUG] Data is valid image bytes ({len(data)} bytes)")
                                except Exception:
                                    # If direct fails, try base64 decoding
                                    print(f"[DEBUG] Direct bytes failed, trying base64 decode...")
                                    try:
                                        import base64
                                        # Try decoding - data might be base64-encoded bytes
                                        try:
                                            # First try as if it's a base64 string encoded in bytes
                                            decoded = base64.b64decode(data.decode('utf-8', errors='ignore'))
                                        except:
                                            # If that fails, try treating bytes as base64 directly
                                            decoded = base64.b64decode(data)
                                        
                                        if len(decoded) > 0:
                                            # Verify it's a valid image
                                            test_img = Image.open(io.BytesIO(decoded))
                                            test_img.load()
                                            image_bytes = decoded
                                            print(f"[DEBUG] Successfully decoded base64 data ({len(decoded)} bytes)")
                                    except Exception as decode_error:
                                        print(f"[DEBUG] Base64 decode failed: {decode_error}")
                                        print(f"[DEBUG] Data preview (first 200 chars): {data[:200] if len(data) > 200 else data}")
                            
                            # Handle string (base64 encoded)
                            elif isinstance(data, str):
                                import base64
                                try:
                                    decoded = base64.b64decode(data)
                                    if len(decoded) > 0:
                                        test_img = Image.open(io.BytesIO(decoded))
                                        test_img.load()
                                        image_bytes = decoded
                                        print(f"[DEBUG] Successfully decoded base64 string ({len(decoded)} bytes)")
                                except Exception as e:
                                    print(f"[DEBUG] Failed to decode base64 string: {e}")
                            
                            # If we have valid image bytes, create the image
                            if image_bytes:
                                image = Image.open(io.BytesIO(image_bytes))
                                print(f"[DEBUG] Successfully created PIL Image (mime_type: {mime_type})")
                                break
                except Exception as e:
                    print(f"[DEBUG] Error extracting from inline_data: {e}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            
            # Try inlineData (camelCase)
            if not image and hasattr(part, 'inlineData'):
                try:
                    inline_data = part.inlineData
                    if inline_data and hasattr(inline_data, 'data'):
                        data = inline_data.data
                        mime_type = None
                        if hasattr(inline_data, 'mime_type'):
                            mime_type = inline_data.mime_type
                        elif hasattr(inline_data, 'mimeType'):
                            mime_type = inline_data.mimeType
                        
                        image_bytes = None
                        
                        if isinstance(data, bytes) and len(data) > 0:
                            try:
                                test_img = Image.open(io.BytesIO(data))
                                test_img.load()
                                image_bytes = data
                                print(f"[DEBUG] inlineData: Data is valid image bytes ({len(data)} bytes)")
                            except Exception:
                                print(f"[DEBUG] inlineData: Direct bytes failed, trying base64 decode...")
                                try:
                                    import base64
                                    try:
                                        decoded = base64.b64decode(data.decode('utf-8', errors='ignore'))
                                    except:
                                        decoded = base64.b64decode(data)
                                    
                                    if len(decoded) > 0:
                                        test_img = Image.open(io.BytesIO(decoded))
                                        test_img.load()
                                        image_bytes = decoded
                                        print(f"[DEBUG] inlineData: Successfully decoded base64 ({len(decoded)} bytes)")
                                except Exception as e:
                                    print(f"[DEBUG] inlineData: Base64 decode failed: {e}")
                        elif isinstance(data, str):
                            import base64
                            try:
                                decoded = base64.b64decode(data)
                                if len(decoded) > 0:
                                    test_img = Image.open(io.BytesIO(decoded))
                                    test_img.load()
                                    image_bytes = decoded
                                    print(f"[DEBUG] inlineData: Successfully decoded base64 string ({len(decoded)} bytes)")
                            except Exception as e:
                                print(f"[DEBUG] inlineData: Failed to decode base64 string: {e}")
                        
                        if image_bytes:
                            image = Image.open(io.BytesIO(image_bytes))
                            print(f"[DEBUG] Successfully created PIL Image from inlineData (mime_type: {mime_type})")
                            break
                except Exception as e:
                    print(f"[DEBUG] Error extracting from inlineData: {e}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            
            # Try as_image() method
            if not image and hasattr(part, 'as_image'):
                try:
                    image = part.as_image()
                    if image:
                        print(f"[DEBUG] Successfully extracted image using as_image()")
                        break
                except Exception as e:
                    print(f"[DEBUG] as_image() failed: {e}")
        
        if not image:
            # Return error if no image found with detailed debug info
            debug_info = {
                "response_type": str(type(response)),
                "response_attrs": [attr for attr in dir(response) if not attr.startswith('_')],
                "has_parts": hasattr(response, 'parts'),
                "has_candidates": hasattr(response, 'candidates'),
            }
            
            try:
                if hasattr(response, 'parts'):
                    debug_info["parts_count"] = len(response.parts) if response.parts else 0
                    if response.parts:
                        debug_info["parts_types"] = [str(type(p)) for p in response.parts[:3]]  # First 3 parts
            except Exception as e:
                debug_info["parts_error"] = str(e)
            
            try:
                if hasattr(response, 'candidates'):
                    debug_info["candidates_count"] = len(response.candidates) if response.candidates else 0
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        debug_info["candidate_attrs"] = [attr for attr in dir(candidate) if not attr.startswith('_')]
                        if hasattr(candidate, 'content'):
                            content = candidate.content
                            debug_info["content_attrs"] = [attr for attr in dir(content) if not attr.startswith('_')]
                            if hasattr(content, 'parts'):
                                try:
                                    parts_list = content.parts
                                    debug_info["parts_count"] = len(parts_list) if parts_list else 0
                                    if parts_list and len(parts_list) > 0:
                                        first_part = parts_list[0]
                                        debug_info["first_part_type"] = str(type(first_part))
                                        debug_info["first_part_attrs"] = [attr for attr in dir(first_part) if not attr.startswith('_')]
                                        # Try to get inline_data info
                                        if hasattr(first_part, 'inline_data'):
                                            try:
                                                inline_data = first_part.inline_data
                                                debug_info["has_inline_data"] = True
                                                debug_info["inline_data_type"] = str(type(inline_data))
                                                if isinstance(inline_data, dict):
                                                    debug_info["inline_data_keys"] = list(inline_data.keys())
                                                elif hasattr(inline_data, 'data'):
                                                    debug_info["inline_data_has_data"] = True
                                                    debug_info["inline_data_data_type"] = str(type(inline_data.data))
                                            except Exception as e:
                                                debug_info["inline_data_error"] = str(e)
                                        elif hasattr(first_part, 'inlineData'):
                                            try:
                                                inline_data = first_part.inlineData
                                                debug_info["has_inlineData"] = True
                                                debug_info["inlineData_type"] = str(type(inline_data))
                                            except Exception as e:
                                                debug_info["inlineData_error"] = str(e)
                                except Exception as e:
                                    debug_info["parts_access_error"] = str(e)
            except Exception as e:
                debug_info["candidates_error"] = str(e)
            
            # Also check if response has a text attribute (might indicate non-image response)
            try:
                if hasattr(response, 'text'):
                    debug_info["has_text"] = True
                    debug_info["text_preview"] = str(response.text)[:200] if response.text else None
            except:
                pass
            
            return json.dumps({
                "error": "No image data found in response. The API may not have generated an image, or the response structure is unexpected.",
                "success": False,
                "debug_info": debug_info,
                "hint": "Check debug_info to see the actual response structure. You may need to update the google-genai SDK: pip install --upgrade google-genai"
            })
        
        # Convert PIL Image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        file_content = image_bytes.getvalue()
        
        # Generate unique filename using storage utility
        original_filename = f"generated_image_{uuid.uuid4().hex[:8]}.png"
        filename = generate_unique_filename(original_filename)
        
        # Save to uploads directory (uses volume mount if configured)
        file_path = save_file(file_content, filename)
        
        # Get file size
        file_size = len(file_content)
        
        # Return file information as JSON
        result = {
            "success": True,
            "file_path": file_path,
            "filename": filename,
            "original_filename": original_filename,
            "content_type": "image/png",
            "file_size": file_size,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }
        
        return json.dumps(result)
            
    except Exception as e:
        error_str = str(e)
        
        # Check if it's a rate limit or service unavailable error
        is_rate_limit = (
            "429" in error_str or 
            "TooManyRequests" in error_str or
            "RESOURCE_EXHAUSTED" in error_str or 
            "quota" in error_str.lower()
        )
        
        is_service_unavailable = (
            "503" in error_str or 
            "UNAVAILABLE" in error_str or
            "overloaded" in error_str.lower() or
            "try again later" in error_str.lower()
        )
        
        if is_rate_limit:
            return json.dumps({
                "error": "Rate limit exceeded (429). The Gemini API has rate limits. Please wait a few minutes before trying again.",
                "success": False,
                "retryable": True,
                "error_code": "RATE_LIMIT"
            })
        elif is_service_unavailable:
            return json.dumps({
                "error": "Service unavailable (503). The Gemini API is currently overloaded. Please try again in a few minutes.",
                "success": False,
                "retryable": True,
                "error_code": "SERVICE_UNAVAILABLE"
            })
        else:
            # Other errors - return immediately without retrying
            return json.dumps({
                "error": f"Failed to generate image: {str(e)}",
                "success": False,
                "retryable": False
            })
