

cd oacz-dubbing-ui

gcloud run deploy web-ui --source .


cd ../oacz-dubbing-job

gcloud builds submit --tag gcr.io/oacz-ariel-poc/movie-processor:latest

gcloud run jobs deploy dubbing-jobs \
    --image gcr.io/oacz-ariel-poc/movie-processor \
    --region europe-west4 \
    --set-env-vars BUCKET_NAME="oacz-video-dubbing",SOURCE_FOLDER="/",DESTINATION_FOLDER="/output"