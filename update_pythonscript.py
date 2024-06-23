import pandas as pd
import serial
import os
import pygame
import time
import uuid

# Google Cloud Text-to-Speech setup
try:
    from google.cloud import texttospeech
    google_tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    google_tts_client = None
    print("Failed to configure Google Text-to-Speech:", str(e))

def read_from_arduino(serial_port, baud_rate=9600, timeout=1):
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=timeout)
        line = ser.readline().decode('utf-8').strip()
        ser.close()
        if not line:
            return "No data received"
        return line
    except serial.SerialException as e:
        return f"Serial error: {e}"

def find_gesture(csv_file, input_values):
    if input_values in ["No data received", "Serial error"]:
        return input_values
    try:
        input_list = list(map(float, input_values.split(',')))
        input_list = input_list[:5]  # Only use Flex1 to Flex5 values
    except ValueError as e:
        return f"Error converting input to float: {e}"

    df = pd.read_csv(csv_file)
    for col in df.columns[:5]:  # Only converting Flex1 to Flex5
        df[col] = pd.to_numeric(df[col], errors='coerce')

    tolerances = [0.10, 0.15, 0.20, 0.10, 0.05]  # Tolerance values adjustable
    conditions = []
    for i, column in enumerate(df.columns[:5]):
        tolerance = tolerances[i]
        lower_bound = input_list[i] * (1 - tolerance)
        upper_bound = input_list[i] * (1 + tolerance)
        conditions.append((df[column] >= lower_bound) & (df[column] <= upper_bound))

    if conditions:
        all_conditions = conditions[0]
        for condition in conditions[1:]:
            all_conditions &= condition
        row = df.loc[all_conditions]
        return row['Gesture'].values[0] if not row.empty else "No matching gesture found"
    return "No valid conditions to evaluate"

def text_to_speech(text, filename, language_code="ml-IN"):
    if google_tts_client:
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            response = google_tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            output_file = f"{filename}_{uuid.uuid4()}.mp3"
            
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            play_sound(output_file)
            safe_delete(output_file)  # Use the safe delete function
        except Exception as e:
            print("Error in Google TTS:", str(e))

def play_sound(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()  # Ensure the mixer unloads the file

def safe_delete(file_path):
    for _ in range(10):  # Try to delete the file up to 10 times
        try:
            os.remove(file_path)
            break  # If the file is successfully deleted, exit the loop
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")
            time.sleep(0.1)  # Wait a bit before trying again

if __name__ == "__main__":
    csv_file = 'gesture_data.csv'
    serial_port = 'COM11'
    
    while True:  # This will create a continuous loop
        input_values = read_from_arduino(serial_port)
        print(f"Received from Arduino: {input_values}")
        gesture = find_gesture(csv_file, input_values)
        print(f"The corresponding gesture is: {gesture}")

        if gesture not in ["Error converting input to float", "No valid conditions to evaluate", "No data received", "Serial error", "No matching gesture found"]:
            filename = gesture
            text_to_speech(gesture, filename)
        else:
            text_to_speech("സാധുവായ ശൈലി ഇല്ല", "no_gesture_found")

        time.sleep(1)  # Sleep for 1 second to prevent high CPU usage and manage resources