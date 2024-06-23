import pandas as pd
import serial
import os
import pygame
import pyttsx3  # Fallback text-to-speech library
import time  # Import time module for adding delay
import uuid  # Import uuid module for generating unique filenames

# Google Cloud Text-to-Speech setup
try:
    from google.cloud import texttospeech
    google_tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    google_tts_client = None
    print("Failed to configure Google Text-to-Speech:", str(e))

def read_from_arduino(serial_port, baud_rate=9600, timeout=1):
    ser = serial.Serial(serial_port, baud_rate, timeout=timeout)
    try:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            return "No data received"
    except serial.SerialException as e:
        return f"Serial error: {e}"
    finally:
        ser.close()
    return line

def find_gesture(csv_file, input_values):
    if input_values in ["No data received", "Serial error"]:
        return input_values

    try:
        input_list = list(map(float, input_values.split(',')))
    except ValueError as e:
        return f"Error converting input to float: {e}"

    # Check if the number of inputs matches the expected number
    expected_number_of_inputs = 11  # Adjust this number based on your specific data format
    if len(input_list) != expected_number_of_inputs:
        return "Unexpected number of inputs received"

    df = pd.read_csv(csv_file)
    
    # Convert columns to numeric, errors='coerce' will convert non-convertible values to NaN
    for col in df.columns[:-1]:  # Assuming last column is 'Gesture' and not needed for comparison
        df[col] = pd.to_numeric(df[col], errors='coerce')

    tolerance = 0.05  # 5% tolerance
    conditions = []
    for i, column in enumerate(df.columns[:-1]):  # Exclude the last column assumed to be 'Gesture'
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

def text_to_speech(text, language_code="ml-IN"):
    if google_tts_client:
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            response = google_tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            output_file = f"output_{uuid.uuid4()}.mp3"  # Unique filename
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            play_sound(output_file)
            os.remove(output_file)  # Delete the file after playing
        except Exception as e:
            print("Error in Google TTS:", str(e))
    else:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

def play_sound(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():  # Wait until the music is no longer busy
        pygame.time.Clock().tick(10)

if __name__ == "__main__":
    csv_file = 'gesture_data.csv'
    serial_port = 'COM11'
    
    while True:  # This will create a continuous loop
        input_values = read_from_arduino(serial_port)
        print(f"Received from Arduino: {input_values}")
        gesture = find_gesture(csv_file, input_values)
        print(f"The corresponding gesture is: {gesture}")

        if gesture not in ["Error converting input to float", "No valid conditions to evaluate", "No data received", "Serial error", "No matching gesture found", "Unexpected number of inputs received"]:
            text_to_speech(f"അംഗീകരിച്ച ശൈലി {gesture}")
        else:
            text_to_speech("സാധുവായ ശൈലി ഇല്ല")

        time.sleep(1)  # Sleep for 1 second to prevent high CPU usage and manage resources