from flask import Flask, request, jsonify, render_template
import os
import json
from google.cloud import storage # Google Cloud Storage client library

app = Flask(__name__)

# --- Google Cloud Storage Configuration ---
# TODO: Replace with your actual Google Cloud Project ID and Bucket Name
PROJECT_ID = 'oacz-ariel-poc'  # Replace with your Google Cloud Project ID
BUCKET_NAME = 'oacz-video-dubbing' # Replace with your Google Cloud Bucket Name
os.environ['GOOGLE_CLOUD_PROJECT'] = PROJECT_ID # Set project ID in environment (if needed)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# --- Local Folders (Optional - for temporary local storage if needed) ---
UPLOAD_FOLDER = 'uploads' # Folder to temporarily store uploaded videos (optional - can upload directly to GCS)
JSON_FOLDER = 'json_data'  # Folder to store JSON files (optional - can store JSON in GCS or database)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # Configure Flask app for upload folder (if used)
app.config['JSON_FOLDER'] = JSON_FOLDER   # Configure Flask app for json folder (if used)

# Ensure local folders exist (if you choose to use them temporarily)
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Optional local upload folder
os.makedirs(JSON_FOLDER, exist_ok=True)   # Optional local json folder

# --- Route to serve the index.html page ---
@app.route('/') # ADDED this route and function
def index():
    return render_template('index.html') # ADDED render_template call

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'videoFile' not in request.files:
        return jsonify({'success': False, 'message': 'No video file part'}), 400

    video_file = request.files['videoFile']
    language = request.form.get('language')
    
    if video_file.filename == '':
        return jsonify({'success': False, 'message': 'No selected video file'}), 400

    if video_file:
        try:
            video_filename = video_file.filename
            # --- Upload video to Google Cloud Storage ---
            blob = bucket.blob(video_filename) # Define blob (object) in GCS bucket
            blob.upload_from_file(video_file) # Upload video file directly to GCS

            video_gcs_url = f"gs://{BUCKET_NAME}/{video_filename}" # Construct GCS URL (optional - for reference)
            print(f"Video uploaded to Google Cloud Storage: {video_gcs_url}")

            # --- Create JSON data ---
            json_data = {'language': language, 'video_gcs_url': video_gcs_url} # Include GCS URL in JSON
            json_filename = os.path.splitext(video_filename)[0] + 'config.json' # JSON filename based on video name
            json_path = os.path.join(app.config['JSON_FOLDER'], json_filename) # Local path for JSON (optional - can save to GCS)

            # --- Save JSON data locally (optional - you can also save to GCS or database) ---
           # with open(json_path, 'w') as f:
           #     json.dump(json_data, f, indent=4) # Save JSON file locally

           # print(f"JSON data saved locally: {json_path}")

            # --- Optional: Save JSON data to Google Cloud Storage as well ---
            json_blob = bucket.blob(json_filename)
            json_blob.upload_from_string(
                 data=json.dumps(json_data, indent=4),
                 content_type='application/json'
            )
            json_gcs_url = f"gs://{BUCKET_NAME}/{json_filename}"
            print(f"JSON data saved to Google Cloud Storage: {json_gcs_url}")


            return jsonify({'success': True, 'message': 'Video uploaded to GCS and information saved!', 'video_url': video_gcs_url}) # Return GCS URL

        except Exception as e:
            return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

    else:
        return jsonify({'success': False, 'message': 'Allowed video types are only video'}), 400

if __name__ == '__main__':
    app.run(debug=True)