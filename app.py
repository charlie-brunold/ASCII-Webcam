from flask import Flask, render_template, request, jsonify, Response
from PIL import Image
import cv2
import os
import io
import base64
import numpy as np

app = Flask(__name__)

def image_to_ascii(image, width=80):
    ascii_chars = "$@B%8WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~i!lI;:,^`. "
    
    aspect_ratio = image.height / image.width
    height = int(aspect_ratio * width * 0.55)
    
    image = image.resize((width, height))
    image = image.convert('L')
    
    ascii_str = ''
    for y in range(height):
        for x in range(width):
            pixel = image.getpixel((x, y))
            ascii_str += ascii_chars[pixel * (len(ascii_chars) - 1) // 255]
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
        image = Image.open(io.BytesIO(file.read()))
        ascii_art = image_to_ascii(image)
        
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
        
        image = Image.open(io.BytesIO(image_bytes))
        ascii_art = image_to_ascii(image, width=60)
        
        return jsonify({
            'success': True,
            'ascii': ascii_art
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)