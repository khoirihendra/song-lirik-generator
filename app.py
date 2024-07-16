import yt_dlp
import os
import re
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
import pygame
import threading
import importlib.util
import sys
import shutil
import platform

# Set your OpenAI API key here
_ = load_dotenv()
client = OpenAI()

def sanitize_title(title):
    sanitized = re.sub(r'[^a-zA-Z\s]', '', title)
    sanitized = sanitized.replace(' ', '_')
    return sanitized

def create_result_folder(youtube_title):
    folder_name = f"results/{sanitize_title(youtube_title)}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def download_audio(youtube_url, output_folder):
    ydl_opts = {
        'quiet': True,
        'format': 'bestaudio/best'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        video_title = sanitize_title(info_dict.get('title', 'audio'))
        audio_output = os.path.join(output_folder, f'{video_title}.mp3')

        ydl_opts.update({
            'outtmpl': audio_output.replace('.mp3', '.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

    for file_name in os.listdir(output_folder):
        if file_name.endswith('.mp3') and not file_name == f'{video_title}.mp3':
            os.rename(os.path.join(output_folder, file_name), audio_output)
            break

    if os.path.exists(audio_output):
        audio = AudioSegment.from_file(audio_output, format="mp3")
        wav_output = os.path.join(output_folder, f"{video_title}.wav")
        audio.export(wav_output, format="wav")
        # print(f"Audio downloaded and converted to WAV: {wav_output}")
        print(f"Audio | Done")
        return wav_output, video_title
    else:
        print("Failed to download audio")
        return None, None

def audio_to_text_with_timestamps(audio_file, output_folder):
    try:
        with open(audio_file, "rb") as file:
            transcript = client.audio.transcriptions.create(
                file=file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        
        words_with_timestamps = transcript.words
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_folder, f"{timestamp}.json")
        with open(output_file, "w") as f:
            json.dump(words_with_timestamps, f, indent=2)
        
        #print(f"Transcription saved to: {output_file}")
        print(f"Speech-to-text | Done")
        return output_file

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def generate_python_code(words_with_timestamps, wav_file_name):
    code = """import time
import pygame
import threading
import sys

def animate_text(text, duration):
    char_delay = duration / len(text) if len(text) > 0 else duration
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(char_delay)
    sys.stdout.write(' ')
    sys.stdout.flush()

def play_audio(wav_file):
    pygame.mixer.init()
    pygame.mixer.music.load(wav_file)
    pygame.mixer.music.play()

def sing_lyrics():
    words = [
    """
    
    for i, word_data in enumerate(words_with_timestamps):
        word = word_data['word']
        start = word_data['start']
        end = word_data['end']
        
        if i == 0:
            initial_delay = start
        else:
            previous_end = words_with_timestamps[i-1]['end']
            delay = max(0, start - previous_end)
        
        duration = max(0, end - start)
        
        # Add a newline flag if the word starts with a capital letter
        newline_flag = word[0].isupper() if word else False
        
        if i == 0:
            code += f'    ("{word}", {initial_delay:.2f}, {duration:.2f}, {newline_flag}),\n'
        else:
            code += f'    ("{word}", {delay:.2f}, {duration:.2f}, {newline_flag}),\n'
        
        if (i + 1) % 6 == 0:
            code += "\n"
    
    code += """]

    for i, (word, delay, duration, newline) in enumerate(words):
        if newline and i > 0:
            sys.stdout.write('\\n')
            sys.stdout.flush()
        time.sleep(delay)
        animate_text(word, duration)
    
def main():
    wav_file = "{}"
    audio_thread = threading.Thread(target=play_audio, args=(wav_file,))
    audio_thread.start()
    sing_lyrics()
    pygame.mixer.music.stop()
    audio_thread.join()

if __name__ == "__main__":
    main()
    """.format(wav_file_name)

    return code

def generate_lyrics_player(input_file, wav_file_path, output_folder):
    try:
        with open(input_file, 'r') as f:
            words_with_timestamps = json.load(f)
        
        wav_file_name = os.path.basename(wav_file_path)
        python_code = generate_python_code(words_with_timestamps, wav_file_path)
        
        output_file = os.path.join(output_folder, "lyrics_player.py")
        with open(output_file, "w") as f:
            f.write(python_code)
        
        # print(f"Lyrics player code has been created in: {output_file}")
        print(f"Generate kodingan lirik | Done")
        return output_file
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def clear_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def main():
    temp_folder = "temp"
    try:
        youtube_url = input("Masukkan URL Youtube: ")
        
        # Download audio
        output_folder, video_title = download_audio(youtube_url, temp_folder)
        if not output_folder:
            return
        
        # Create result folder
        result_folder = create_result_folder(video_title)
        
        # Move WAV file to result folder
        new_wav_path = os.path.join(result_folder, os.path.basename(output_folder))
        os.rename(output_folder, new_wav_path)
        
        # Convert speech to text
        json_file = audio_to_text_with_timestamps(new_wav_path, result_folder)
        if not json_file:
            return
        
        # Generate lyrics player code
        lyrics_player_file = generate_lyrics_player(json_file, new_wav_path, result_folder)
        if not lyrics_player_file:
            return
        
        # Ask user if they want to play the generated script
        play_choice = input("Jalankan kodingan hasil generate? (Y/N): ").strip().lower()
        
        if play_choice == 'y':
            clear_screen()  # Clear the console screen
            print("\n\nMainkan cuk...\n")
            
            # Add the result folder to Python's sys.path
            sys.path.append(os.path.dirname(lyrics_player_file))
            
            # Import and run the lyrics_player module
            try:
                spec = importlib.util.spec_from_file_location("lyrics_player", lyrics_player_file)
                lyrics_player_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(lyrics_player_module)
                
                # Run the main function of the lyrics player
                lyrics_player_module.main()
            except ImportError as e:
                print(f"Error importing the lyrics player module: {e}")
                print("Please ensure you have all required modules installed, including pygame.")
            except Exception as e:
                print(f"An error occurred while running the lyrics player: {e}")

            print("\n\nMantap...")
        else:
            print("Lyrics player not started. You can run it later by executing the generated script.")

    finally:
        # Clean up: remove the temp folder
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)

if __name__ == "__main__":
    main()