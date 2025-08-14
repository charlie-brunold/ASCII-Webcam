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

def get_char_brightness_map(char_set):
    char_map = {}
    num_chars = len(char_set)
    for i, char in enumerate(char_set):
        brightness = int((i / (num_chars - 1)) * 255)
        char_map[brightness] = char
    return char_map

def image_to_ascii(image, width=80, char_set='enhanced', sampling_factor=3):
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
            
            # Use gaussian-weighted averaging for smoother results
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
        
        image = Image.open(io.BytesIO(file.read()))
        ascii_art = image_to_ascii(image, width=width, char_set=char_set, sampling_factor=sampling_factor)
        
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
        
        image = Image.open(io.BytesIO(image_bytes))
        ascii_art = image_to_ascii(image, width=width, char_set=char_set, sampling_factor=sampling_factor)
        
        return jsonify({
            'success': True,
            'ascii': ascii_art
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)