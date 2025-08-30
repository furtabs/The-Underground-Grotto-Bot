from PIL import Image, ImageDraw, ImageFont
import random
import io
import math
import colorsys
import discord

def generate_wheel_gif(boardList):
    """Generates a spinning GIF and a final static wheel image with vibrant colors."""
    size = 400  # Image size
    num_slices = len(boardList)
    angle_per_slice = 360 / num_slices
    
    # Generate vibrant colors
    colors = generate_vibrant_colors(num_slices)
    
    frames = []
    selected_index = random.randint(0, num_slices - 1)
    selected_item = boardList[selected_index]
    
    for frame_angle in range(0, 360 * 3 + 15, 15):  # Spin animation
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Fully transparent background
        draw = ImageDraw.Draw(image)
        
        # Draw wheel slices
        for i in range(num_slices):
            start_angle = i * angle_per_slice + frame_angle  # Rotate with the wheel
            end_angle = start_angle + angle_per_slice
            draw.pieslice((0, 0, size, size), start=start_angle, end=end_angle, fill=colors[i])
        
        # Add text to slices (after all slices are drawn)
        for i in range(num_slices):
            start_angle = i * angle_per_slice + frame_angle
            end_angle = start_angle + angle_per_slice
            text = boardList[i]
            mid_angle = math.radians((start_angle + end_angle) / 2)
            add_text_to_slice(draw, text, mid_angle, size, colors[i])
        
        # Draw arrow at the top
        draw_arrow(draw, size)
        frames.append(image)
    
    # Create final static image with winning board at the top
    final_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Fully transparent background
    final_draw = ImageDraw.Draw(final_image)
    
    # Calculate the rotation needed to position the selected item at the top
    # Top position is at 270 degrees in PIL's coordinate system (0 at 3 o'clock, goes clockwise)
    top_position = 270
    
    # Calculate the current angle of the selected item
    selected_mid_angle = selected_index * angle_per_slice + angle_per_slice / 2
    
    # Calculate rotation needed to move selected item to top
    rotation_angle = top_position - selected_mid_angle
    
    # Draw final wheel with selected board at the top
    for i in range(num_slices):
        # Apply the rotation to position the selected item at the top
        start_angle = i * angle_per_slice + rotation_angle
        end_angle = start_angle + angle_per_slice
        final_draw.pieslice((0, 0, size, size), start=start_angle, end=end_angle, fill=colors[i])
    
    # Re-add text to final image
    for i in range(num_slices):
        start_angle = i * angle_per_slice + rotation_angle
        end_angle = start_angle + angle_per_slice
        text = boardList[i]
        mid_angle = math.radians((start_angle + end_angle) / 2)
        add_text_to_slice(final_draw, text, mid_angle, size, colors[i])
    
    # Redraw arrow in final image
    draw_arrow(final_draw, size)
    
    # Convert GIF and final image to BytesIO
    gif_io = io.BytesIO()
    frames[0].save(gif_io, format="GIF", save_all=True, append_images=frames[1:], duration=50, loop=0)
    gif_io.seek(0)
    
    final_img_io = io.BytesIO()
    final_image.save(final_img_io, "PNG")
    final_img_io.seek(0)
    
    return selected_item, gif_io, final_img_io

def generate_vibrant_colors(num_colors):
    """Generate vibrant, distinct colors for the wheel slices."""
    colors = []
    
    # Vibrant base colors (RGB tuples)
    vibrant_palette = [
        (255, 0, 0),      # Bright Red
        (0, 0, 255),      # Bright Blue
        (0, 200, 0),      # Bright Green
        (255, 255, 0),    # Yellow
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Cyan
        (255, 165, 0),    # Orange
        (128, 0, 128),    # Purple
        (255, 105, 180),  # Hot Pink
        (0, 128, 128),    # Teal
        (255, 215, 0),    # Gold
        (0, 191, 255)     # Deep Sky Blue
    ]
    
    # If we have fewer slices than colors, randomly select from the palette
    if num_colors <= len(vibrant_palette):
        return random.sample(vibrant_palette, num_colors)
    
    # If we need more colors, use HSV color model to generate evenly distributed hues
    for i in range(num_colors):
        # Distribute hues evenly around the color wheel
        h = i / num_colors
        # Use high saturation and value for vibrant colors
        s = 0.9 + random.uniform(-0.1, 0.1)  # High saturation with slight variation
        v = 0.9 + random.uniform(-0.1, 0.1)  # High value with slight variation
        
        # Convert HSV to RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        # Convert to 0-255 range
        rgb = (int(r * 255), int(g * 255), int(b * 255))
        colors.append(rgb)
    
    # Shuffle to avoid predictable color sequence
    random.shuffle(colors)
    return colors

def add_text_to_slice(draw, text, angle_rad, size, bg_color):
    """Positions text correctly inside each wedge with appropriate contrast."""
    try:
        # Try different common font locations
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
    
    # Calculate text position based on angle
    center_x, center_y = size // 2, size // 2
    radius = size // 2.7  # Position text at optimal distance from center
    
    # Position text along the radius
    text_x = center_x + int(radius * math.cos(angle_rad))
    text_y = center_y + int(radius * math.sin(angle_rad))
    
    # Calculate text rotation angle (in degrees)
    # Add 90 degrees so text is tangent to the circle
    rotation_angle = math.degrees(angle_rad) + 90
    
    # Determine text color based on background brightness for contrast
    r, g, b = bg_color
    brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    text_color = "black" if brightness > 0.5 else "white"
    
    # Create a temporary image for rotated text with extra padding
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create temp image for text with larger padding
    padding = 40
    txt_img = Image.new('RGBA', (text_width + padding, text_height + padding), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((padding // 2, padding // 2), text, fill=text_color, font=font)
    
    # Rotate the text image - negative angle to rotate correctly
    txt_img = txt_img.rotate(-rotation_angle, expand=True, resample=Image.BICUBIC)
    
    # Calculate position to paste (centered)
    paste_x = text_x - txt_img.width // 2
    paste_y = text_y - txt_img.height // 2
    
    # Paste the rotated text onto the main image
    draw._image.paste(txt_img, (paste_x, paste_y), txt_img)

def draw_arrow(draw, size):
    """Draws an arrow at the top of the wheel."""
    arrow_size = 20
    arrow_x = size // 2
    arrow_y = 10
    draw.polygon(
        [(arrow_x - arrow_size, arrow_y), (arrow_x + arrow_size, arrow_y), (arrow_x, arrow_y + arrow_size)],
        fill="black"
    )