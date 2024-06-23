import pandas as pd  
import serial  
import os  
import pygame  
import pyttsx3  # Fallback text-to-speech library  
  
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
        # Only use Flex1 to Flex5 values  
        input_list = input_list[:5]  
    except ValueError as e:  
        return f"Error converting input to float: {e}"  
  
    df = pd.read_csv(csv_file)  
    # Convert columns to numeric, errors='coerce' will convert non-convertible values to NaN  
    for col in df.columns[:5]:  # Only converting Flex1 to Flex5  
        df[col] = pd.to_numeric(df[col], errors='coerce')  
  
    # Define separate tolerance values for Flex sensors (in percentage)  
    tolerances = [0.10, 0.15, 0.20, 0.10, 0.05]  # Adjust these values as needed  
  
    conditions = []  
    for i, column in enumerate(df.columns[:5]):  # Only using Flex1 to Flex5  
        tolerance = tolerances[i]  
        lower_bound = input_list[i] * (1 - tolerance)  
        upper_bound = input_list[i] * (1 + tolerance)  
        print(f"Checking column: {column}, value: {input_list[i]}, lower_bound: {lower_bound}, upper_bound: {upper_bound}")  
        conditions.append((df[column] >= lower_bound) & (df[column] <= upper_bound))  
  #
    if conditions:  
        all_conditions = conditions[0]  
        for condition in conditions[1:]:  
            all_conditions &= condition  
        row = df.loc[all_conditions]  
        print(f"Matching rows: {row}")  
        return row['Gesture'].values[0] if not row.empty else "No matching gesture found"  
    return "No valid conditions to evaluate"  
  
def text_to_speech(text, filename, language_code="ml-IN"):  
    if google_tts_client:  
        try:  
            synthesis_input = texttospeech.SynthesisInput(text=text)  
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)  
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)  
            response = google_tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)  
            with open(filename, "wb") as out:  
                out.write(response.audio_content)  
                print(f"Audio content written to file '{filename}'")  
            play_sound(filename)  
        except Exception as e:  
            print("Error in Google TTS:", str(e))  
    else:  
        print("Google TTS client is not configured, using pyttsx3.")  
        engine = pyttsx3.init()  
        engine.setProperty('voice', 'com.apple.speech.synthesis.voice.amelie')  # Set to a voice that supports Malayalam if available  
        engine.say(text)  
        engine.runAndWait()  
  
def play_sound(file_path):  
    pygame.mixer.init()  
    pygame.mixer.music.load(file_path)  
    pygame.mixer.music.play()  
    while pygame.mixer.music.get_busy():  
        pygame.time.Clock().tick(10)  
  
if __name__ == "__main__":  
    csv_file = 'gesture_data.csv'  # Replace with the path to your CSV file  
    serial_port = 'COM11'  # Adjust the serial port as necessary  
  
    input_values = read_from_arduino(serial_port)  
    print(f"Received from Arduino: {input_values}")  
    gesture = find_gesture(csv_file, input_values)  
    print(f"The corresponding gesture is: {gesture}")  
if gesture not in ["Error converting input to float", "No valid conditions to evaluate", "No data received", "Serial error", "No matching gesture found"]:
    filename = gesture
    text_to_speech(gesture, filename)
else:
    text_to_speech("സാധുവായ ആംഗ്യമില്ല", "no_gesture_found")