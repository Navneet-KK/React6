from flask import Flask, render_template, request, jsonify, Response
import requests

app = Flask(__name__)

UPLOAD_API_URL = "https://temp.kotol.cloud/api/file-upload?expiration="
FILE_INFO_API_URL = "https://temp.kotol.cloud/api/fileinfo/?code="

@app.route('/')
def index():
    return render_template('test-gui.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    expiry = request.form.get('expiry', default='900000')  # default to 15 min

    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    def generate():
        while True:
            chunk = file.stream.read(8192)
            if not chunk:
                break
            yield chunk

    headers = {
        'Content-Type': 'application/octet-stream',
        'File-Name': file.filename
    }

    try:
        response = requests.post(
            UPLOAD_API_URL + expiry,
            headers=headers,
            data=generate()
        )
        # Try parsing JSON, fallback to text
        try:
            api_response = response.json()
            result = api_response
            original_code = result.get('code')
            result['code'] = swap_code(original_code)
        except ValueError:
            api_response = response.text
        return jsonify({
            'status_code': response.status_code,
            'response': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/check', methods=['POST'])
def check_file_code():
    data = request.get_json()
    code = swap_code(data.get('code'))

    if not code:
        return jsonify({'error': 'No code provided'}), 400
    try:
        # Call the external API to get file info by code
        response = requests.get(FILE_INFO_API_URL + code)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Code not found or expired', 'status_code': response.status_code}), response.status_code
    except Exception as e:
        return jsonify({'error': 'Error fetching file info', 'details': str(e)}), 500
    

@app.route('/download')
def proxy_download():
    file = request.args.get('file')
    code = request.args.get('code')

    real_url = f"https://temp.kotol.cloud/api/download/{file}?code={code}"
    r = requests.get(real_url, stream=True)

    # Relay response to frontend
    return Response(
        r.iter_content(chunk_size=65536),
        headers={
            "Content-Disposition": f'attachment; filename="{file}"',
            "Content-Type": r.headers.get("Content-Type", "application/octet-stream")
        }
    )

def swap_code(code):
    if len(code) == 4:
        reordered = [code[2], code[1], code[0], code[3]]  # reqt
        return ''.join(reordered)
    return code

if __name__ == '__main__':
    app.run(debug=True)
