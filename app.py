from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import os

app = Flask(__name__)

# API Keys
PEXELS_API_KEY = "fc5nRBBWuy5RqfWQP6I8A9ZssloxIikENw9xaov5LpQbv3TyvlKp8YB0"
HUGGING_FACE_API_KEY = "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"

# Function to fetch videos from Pexels API
def fetch_video(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/videos/search?query={query}&per_page=1"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['videos']:
            return data['videos'][0]['video_files'][0]['link']
    return None

# Function to generate text using Hugging Face API
def generate_text(prompt):
    headers = {"Authorization": f"Bearer {HUGGING_FACE_API_KEY}"}
    response = requests.post(
        "https://api-inference.huggingface.co/models/gpt2",
        headers=headers,
        json={"inputs": prompt}
    )
    if response.status_code == 200:
        return response.json()[0]['generated_text']
    else:
        raise Exception(f"Error: {response.text}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_comedy():
    prompt = request.json.get('prompt', '')

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    try:
        # Generate comedy text
        generated_text = generate_text(prompt).strip()

        # Convert generated text to speech
        tts = gTTS(generated_text, lang='en')
        audio_file = 'comedy_audio.mp3'
        tts.save(audio_file)

        # Fetch video related to the prompt from Pexels
        video_url = fetch_video(prompt)
        if not video_url:
            raise Exception("No video found for the given prompt")

        # Download the video file
        video_file = 'background_video.mp4'
        video_response = requests.get(video_url)
        with open(video_file, 'wb') as f:
            f.write(video_response.content)

        # Load the video and audio files
        audio_clip = AudioFileClip(audio_file)
        video_clip = VideoFileClip(video_file)

        # Adjust video duration to match audio length
        video_duration = video_clip.duration
        audio_duration = audio_clip.duration

        if video_duration < audio_duration:
            # Repeat video to match audio length
            num_repeats = int(audio_duration // video_duration) + 1
            video_clips = [video_clip] * num_repeats
            final_video_clip = concatenate_videoclips(video_clips).subclip(0, audio_duration)
        else:
            # Trim video to match audio length
            final_video_clip = video_clip.subclip(0, audio_duration)

        # Set the audio of the video
        final_video_clip = final_video_clip.set_audio(audio_clip)

        # Save the final video
        final_video_file = 'static/comedy_video.mp4'
        final_video_clip.write_videofile(final_video_file, fps=24)

        return jsonify({"comedy": generated_text, "video_path": final_video_file})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/<path:filename>')
def serve_file(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
