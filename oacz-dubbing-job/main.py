import os
import json
import logging
from google.cloud import storage
from google import genai
from google.genai import types
from google.genai.types import HttpOptions, Part
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_json_files(bucket_name, source_folder, destination_folder):
    """
    Reads all JSON files from a source folder within a bucket and moves them to a destination folder within the same bucket.

    Args:
        bucket_name (str): The name of the Google Cloud Storage bucket.
        source_folder (str): The folder within the bucket containing the JSON files (e.g., "input/").
        destination_folder (str): The folder within the bucket to move the JSON files to (e.g., "output/").
    """
    try:
        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()

        # Get the bucket
        bucket = storage_client.bucket(bucket_name)
        logging.info(f"Accessing bucket: {bucket_name}")

        if source_folder == "/":
            blobs = bucket.list_blobs()
        else:
            blobs = bucket.list_blobs(prefix=source_folder)


        for blob in blobs:
            if blob.name.lower().endswith('.json'):
                logging.info(f"Processing JSON file: {blob.name}")

                try:
                    # Construct the new blob name for the destination folder
                    new_blob_name = os.path.join(destination_folder, blob.name)
                    logging.info(f"caputuring '{blob.name}' from source folder.")
                    #copy the file
                    new_blob = bucket.copy_blob(blob, bucket, new_blob_name)
                    logging.info(f"Successfully moved '{blob.name}' to '{new_blob_name}' within the bucket.")

                    # Delete the original JSON file from the source folder
                    blob.delete()
                    logging.info(f"Deleted '{blob.name}' from source folder.")
                    #start the processing of the json file
                    call_gemini(new_blob)
                    break
                    

                except Exception as e:
                    logging.error(f"Error processing file '{blob.name}': {e}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise  # Re-raise the exception for Cloud Run Job to report failure

    logging.info("JSON file moving job completed.")


def call_gemini(json_config):
    logging.info("Processing Config file with Gemini...")
   
    
    try:
        storage_client = storage.Client()
        json_data = json.loads(json_config.download_as_bytes())
        video_gcs_url = json_data.get("video_gcs_url")
        logging.info(f"video_gcs_url: {video_gcs_url}")

        # Call Gemini API to transcribe the video
        logging.info(f"Calling Gemini API to transcribe video: {video_gcs_url}")
        
        clientai = genai.Client(vertexai=True,project="oacz-ariel-poc",location="europe-west4",http_options=HttpOptions(api_version="v1"))
        
        response = clientai.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[
            Part.from_uri(
                file_uri=video_gcs_url,
                mime_type="video/mp4",
            ),
            "Create a table with the transcription of the video and the time stamp, and translate the transcription to spanish. Break it out by complete phrases. Output in a CSV format. Just output 3 colums no header. Each colum should be separated by a comma and in quotes. Just out the requested information avoid introductory phrases like for example of course here is the result",
            ],
            config = types.GenerateContentConfig(
            temperature = 1,
            top_p = 0.95,
            response_modalities = ["TEXT"],
            )
        )
        logging.info(f"Response from gemini: {response.text}")
        # Upload the response to GCS
        output_bucket_name = os.environ.get("BUCKET_NAME")
        if not output_bucket_name:
            logging.error("Environment variable OUTPUT_BUCKET_NAME must be set.")
            raise ValueError("Environment variable OUTPUT_BUCKET_NAME must be set.")
        
        output_file_name = os.path.splitext(os.path.basename(video_gcs_url))[0] + ".csv"
        output_blob_name = os.path.join("transcriptions", output_file_name)
        output_bucket = storage_client.bucket(output_bucket_name)
        output_blob = output_bucket.blob(output_blob_name)
        # Upload the response to GCS with UTF-8 encoding
        response_bytes = response.text.encode('utf-8')
        output_blob.upload_from_string(response_bytes, content_type="text/csv")

        
        logging.info(f"Response uploaded to gs://{output_bucket_name}/{output_blob_name}")


        logging.info(f"Gemini API call completed for video: {video_gcs_url}")


    except Exception as e:
        logging.error(f"Error processing JSON data: {e}")


def main():
    """
    Main function to read bucket name, source folder, and destination folder from environment variables and run the move job.
    """
    bucket_name = os.environ.get("BUCKET_NAME")
    source_folder = os.environ.get("SOURCE_FOLDER")
    destination_folder = os.environ.get("DESTINATION_FOLDER")


    if not bucket_name or not destination_folder:
        logging.error("Environment variables BUCKET_NAME, SOURCE_FOLDER, and DESTINATION_FOLDER must be set.")
        exit(1)
    
    # make sure the source folder ends with /
    if not source_folder.endswith('/'):
      source_folder += '/'
    # make sure the destination folder ends with /
    if not destination_folder.endswith('/'):
      destination_folder += '/'

    logging.info("Starting JSON file moving job...")
    process_json_files(bucket_name, source_folder, destination_folder)


if __name__ == "__main__":
    main()
