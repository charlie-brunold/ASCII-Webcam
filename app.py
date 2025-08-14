from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

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
    
    # For now, return a placeholder ASCII art
    # This will be replaced with actual ASCII conversion logic later
    placeholder_ascii = """
 ██████╗ ██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝ ██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║      ██║     ███████║██║   ██║██║  ██║█████╗  
██║      ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  
╚██████╗ ███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
                                                   
        ASCII ART CONVERSION READY!
        Upload functionality working ✓
    """
    
    return jsonify({
        'success': True, 
        'ascii': placeholder_ascii
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)