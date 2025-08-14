from flask import Flask, render_template, request, jsonify, Response
from PIL import Image
import cv2
import os
import io
import base64
import numpy as np

app = Flask(__name__)

ASCII_SETS = {
    'enhanced': " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    'standard': " .:-=+*#%@",
    'simple': " .oO@"
}

# Directional characters for edge detection
EDGE_CHARS = {
    'horizontal': '-',
    'vertical': '|',
    'diagonal_right': '/',
    'diagonal_left': '\\',
    'cross': '+',
    'corner': '*'
}

def get_char_brightness_map(char_set):
    char_map = {}
    num_chars = len(char_set)
    for i, char in enumerate(char_set):
        brightness = int((i / (num_chars - 1)) * 255)
        char_map[brightness] = char
    return char_map

def detect_edges(img_array, threshold=50):
    """
    Detect edges using Sobel operators and return edge map with directions.
    """
    # Sobel kernels for edge detection
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    
    # Pad the image to handle borders
    padded = np.pad(img_array, 1, mode='edge')
    
    # Initialize output arrays
    height, width = img_array.shape
    edge_magnitude = np.zeros((height, width))
    edge_direction = np.zeros((height, width))
    
    # Apply Sobel filters
    for y in range(height):
        for x in range(width):
            # Extract 3x3 region
            region = padded[y:y+3, x:x+3]
            
            # Calculate gradients
            grad_x = np.sum(region * sobel_x)
            grad_y = np.sum(region * sobel_y)
            
            # Calculate magnitude and direction
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            direction = np.arctan2(grad_y, grad_x)
            
            edge_magnitude[y, x] = magnitude
            edge_direction[y, x] = direction
    
    # Create edge mask based on threshold
    edge_mask = edge_magnitude > threshold
    
    return edge_mask, edge_direction, edge_magnitude

def get_directional_char(direction):
    """
    Convert edge direction to appropriate directional character.
    """
    # Convert direction from radians to degrees and normalize to 0-180
    angle = np.degrees(direction) % 180
    
    if angle < 22.5 or angle >= 157.5:
        return EDGE_CHARS['horizontal']
    elif 22.5 <= angle < 67.5:
        return EDGE_CHARS['diagonal_right']
    elif 67.5 <= angle < 112.5:
        return EDGE_CHARS['vertical']
    else:  # 112.5 <= angle < 157.5
        return EDGE_CHARS['diagonal_left']

def image_to_ascii(image, width=80, char_set='enhanced', sampling_factor=3, edge_detection=True, edge_threshold=50):
    if char_set not in ASCII_SETS:
        char_set = 'enhanced'
    
    ascii_chars = ASCII_SETS[char_set]
    
    aspect_ratio = image.height / image.width
    height = int(aspect_ratio * width * 0.55)
    
    # Process at higher resolution for better sampling
    high_res_width = width * sampling_factor
    high_res_height = height * sampling_factor
    
    # Resize to high resolution first
    high_res_image = image.resize((high_res_width, high_res_height), Image.LANCZOS)
    high_res_image = high_res_image.convert('L')
    
    # Convert to numpy array for efficient processing
    img_array = np.array(high_res_image)
    
    # Detect edges if enabled
    edge_mask = None
    edge_direction = None
    if edge_detection:
        edge_mask, edge_direction, edge_magnitude = detect_edges(img_array, edge_threshold)
    
    ascii_str = ''
    for y in range(height):
        for x in range(width):
            # Calculate the region in the high-res image for weighted averaging
            start_x = x * sampling_factor
            end_x = min((x + 1) * sampling_factor, high_res_width)
            start_y = y * sampling_factor
            end_y = min((y + 1) * sampling_factor, high_res_height)
            
            # Extract the block and apply weighted averaging
            block = img_array[start_y:end_y, start_x:end_x]
            
            # Check if this region contains significant edges
            if edge_detection and edge_mask is not None:
                edge_block = edge_mask[start_y:end_y, start_x:end_x]
                edge_dir_block = edge_direction[start_y:end_y, start_x:end_x]
                
                # If more than 30% of the block contains edges, use directional character
                edge_ratio = np.mean(edge_block)
                if edge_ratio > 0.3:
                    # Get the dominant edge direction in this block
                    if np.any(edge_block):
                        # Calculate weighted average of edge directions
                        edge_directions = edge_dir_block[edge_block]
                        if len(edge_directions) > 0:
                            # Use the median direction for stability
                            dominant_direction = np.median(edge_directions)
                            ascii_str += get_directional_char(dominant_direction)
                            continue
            
            # Use gaussian-weighted averaging for smoother results (fill regions)
            block_height, block_width = block.shape
            weights = np.zeros((block_height, block_width))
            
            # Create gaussian weight matrix
            center_y, center_x = block_height // 2, block_width // 2
            for by in range(block_height):
                for bx in range(block_width):
                    # Distance from center with sub-pixel positioning
                    dist_y = (by - center_y + 0.5) / block_height
                    dist_x = (bx - center_x + 0.5) / block_width
                    dist = np.sqrt(dist_y**2 + dist_x**2)
                    # Gaussian weight (sigma = 0.5 for moderate smoothing)
                    weights[by, bx] = np.exp(-(dist**2) / (2 * 0.5**2))
            
            # Normalize weights
            weights = weights / np.sum(weights)
            
            # Calculate weighted average
            weighted_pixel = np.sum(block * weights)
            
            # Map to character
            char_index = int(weighted_pixel * (len(ascii_chars) - 1) / 255)
            char_index = max(0, min(char_index, len(ascii_chars) - 1))
            ascii_str += ascii_chars[char_index]
        ascii_str += '\n'
    
    return ascii_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image file selected'})
    
    try:
        # Get optional parameters from form data
        width = int(request.form.get('width', 80))
        sampling_factor = int(request.form.get('sampling_factor', 3))
        char_set = request.form.get('char_set', 'enhanced')
        edge_detection = request.form.get('edge_detection', 'true').lower() == 'true'
        edge_threshold = int(request.form.get('edge_threshold', 50))
        
        image = Image.open(io.BytesIO(file.read()))
        ascii_art = image_to_ascii(image, width=width, char_set=char_set, sampling_factor=sampling_factor, 
                                 edge_detection=edge_detection, edge_threshold=edge_threshold)
        
        return jsonify({
            'success': True, 
            'ascii': ascii_art
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to process image: {str(e)}'})

@app.route('/webcam_frame', methods=['POST'])
def process_webcam_frame():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Get optional parameters
        width = data.get('width', 60)
        sampling_factor = data.get('sampling_factor', 3)
        char_set = data.get('char_set', 'enhanced')
        edge_detection = data.get('edge_detection', True)
        edge_threshold = data.get('edge_threshold', 50)
        
        image = Image.open(io.BytesIO(image_bytes))
        ascii_art = image_to_ascii(image, width=width, char_set=char_set, sampling_factor=sampling_factor,
                                 edge_detection=edge_detection, edge_threshold=edge_threshold)
        
        return jsonify({
            'success': True,
            'ascii': ascii_art
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)