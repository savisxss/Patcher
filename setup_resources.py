import os
import base64
import io
from PIL import Image, ImageDraw

def create_resource_dir():
    """Create the resources directory if it doesn't exist."""
    if not os.path.exists("resources"):
        os.makedirs("resources")
        print("Created resources directory")

def create_icon():
    """Create a placeholder icon if it doesn't exist."""
    icon_path = os.path.join("resources", "patcher_icon.ico")
    png_path = os.path.join("resources", "patcher_icon.png")
    
    if os.path.exists(icon_path) and os.path.exists(png_path):
        print("Icons already exist")
        return
    
    # Create a simple icon
    img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a blue rectangle
    draw.rectangle([40, 40, 216, 216], fill=(65, 134, 232))
    
    # Draw white lines like a document
    for y in range(80, 200, 30):
        draw.line([(80, y), (176, y)], fill=(255, 255, 255), width=10)
    
    # Draw a green check mark
    draw.line([(100, 160), (120, 180)], fill=(0, 200, 0), width=15)
    draw.line([(120, 180), (170, 110)], fill=(0, 200, 0), width=15)
    
    # Save as PNG
    img.save(png_path)
    print(f"Created {png_path}")
    
    # Convert to icon format
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    with open(icon_path, 'wb') as icon_file:
        # ICO format header for multiple sizes
        icon_file.write(b'\x00\x00')  # Reserved
        icon_file.write(b'\x01\x00')  # ICO format
        icon_file.write(len(icon_sizes).to_bytes(2, byteorder='little'))  # Number of images
        
        offset = 6 + 16 * len(icon_sizes)  # Start of image data
        image_data = []
        
        # Write image directory entries
        for size in icon_sizes:
            scaled_img = img.resize(size, Image.LANCZOS)
            img_bytes = io.BytesIO()
            scaled_img.save(img_bytes, format='PNG')
            img_data = img_bytes.getvalue()
            img_size = len(img_data)
            
            # Width, Height
            icon_file.write(size[0].to_bytes(1, byteorder='little'))
            icon_file.write(size[1].to_bytes(1, byteorder='little'))
            
            # Color palette - 0 for PNG
            icon_file.write(b'\x00')
            
            # Reserved
            icon_file.write(b'\x00')
            
            # Color planes - 1 for PNG
            icon_file.write(b'\x01\x00')
            
            # Bits per pixel - 32 for PNG with alpha
            icon_file.write(b'\x20\x00')
            
            # Image size in bytes
            icon_file.write(img_size.to_bytes(4, byteorder='little'))
            
            # Image offset in file
            icon_file.write(offset.to_bytes(4, byteorder='little'))
            
            offset += img_size
            image_data.append(img_data)
        
        # Write the image data
        for img_data in image_data:
            icon_file.write(img_data)
    
    print(f"Created {icon_path}")

if __name__ == "__main__":
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Installing Pillow for image creation...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image, ImageDraw
    
    create_resource_dir()
    create_icon()
    print("Resource setup complete")