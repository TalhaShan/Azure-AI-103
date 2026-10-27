from dotenv import load_dotenv
import os
from playsound3 import playsound

# Import namespaces
# speech_sdk: the Azure AI Speech SDK (pip package azure-cognitiveservices-speech)
import azure.cognitiveservices.speech as speech_sdk
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential


def main():
    try:
        # Clear the console
        os.system('cls' if os.name == 'nt' else 'clear')

        # Get Configuration Settings
        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')
        foundry_key = os.getenv('FOUNDRY_KEY')  # not needed: we sign in with Entra ID

        # Create speech_config using Entra ID authentication
        # The token credential gets tokens from your Azure sign-in, so no key is
        # used. The endpoint must be the resource's custom-domain endpoint, like
        # https://<name>.cognitiveservices.azure.com/
        # Your account needs the "Cognitive Services Speech User" role.
        credential = DefaultAzureCredential()
        speech_config = speech_sdk.SpeechConfig(
            token_credential=credential,
            endpoint=foundry_endpoint,
        )


        # Loop until user quits
        inputText = ""
        while inputText.lower() != "3":
            inputText = input("Choose an option:\n1: Record a greeting\n2: Transcribe messages\n3: Exit\n")
            if inputText != "3":
                if inputText == "1":
                    record_greeting(speech_config)
                elif inputText == "2":
                    transcribe_messages(speech_config)
                elif inputText == "3":
                    print("Exiting...")
                    return
                else:
                    print("Invalid option, please try again.")



    except Exception as ex:
        print(ex)

# record_greeting function
def record_greeting(speech_config):
    print("Recording greeting...")

    # Get greeting message from user
    greeting_message = input("Enter your greeting message: ")


    # Synthesize the greeting message to an audio file
    # The voice is the speaker used to read the text aloud.
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"

    # AudioOutputConfig with a filename sends the audio into a .wav file
    # instead of the speakers.
    output_file = "greeting.wav"
    audio_config = speech_sdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speech_sdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    # Run the synthesis and wait for the result
    result = synthesizer.speak_text_async(greeting_message).get()

    if result.reason == speech_sdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Greeting saved to {output_file}")
    elif result.reason == speech_sdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(f"Speech synthesis canceled: {details.reason}")
        if details.reason == speech_sdk.CancellationReason.Error:
            print(f"Error details: {details.error_details}")

    # Release the synthesizer so the file is closed and can be played
    del synthesizer

    # Play the saved greeting back
    if os.path.exists(output_file):
        playsound(output_file)



# transcribe_messages function
def transcribe_messages(speech_config):
    print("Transcribing messages...")
    
    messages_folder = 'messages'
    for file_name in os.listdir(messages_folder):
        if file_name.endswith('.wav'):
            print(f"\nTranscribing {file_name}...")
            file_path = os.path.join(messages_folder, file_name)
            playsound(file_path)

            # Transcribe the audio file
            # AudioConfig with a filename reads the audio from the .wav file
            # instead of the microphone.
            audio_config = speech_sdk.audio.AudioConfig(filename=file_path)
            recognizer = speech_sdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            # recognize_once transcribes the first spoken phrase (up to ~30
            # seconds), which is enough for short voice messages.
            result = recognizer.recognize_once_async().get()

            if result.reason == speech_sdk.ResultReason.RecognizedSpeech:
                print(f"Transcription: {result.text}")
            elif result.reason == speech_sdk.ResultReason.NoMatch:
                print("No speech could be recognized.")
            elif result.reason == speech_sdk.ResultReason.Canceled:
                details = result.cancellation_details
                print(f"Transcription canceled: {details.reason}")
                if details.reason == speech_sdk.CancellationReason.Error:
                    print(f"Error details: {details.error_details}")

            # Release the recognizer so the audio file is closed
            del recognizer



if __name__ == "__main__":
    main()