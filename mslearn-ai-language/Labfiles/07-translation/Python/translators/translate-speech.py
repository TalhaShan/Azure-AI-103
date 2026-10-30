import os
from dotenv import load_dotenv


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

        # Configure translation
        # Entra ID sign-in (no key). The endpoint must be the resource's
        # custom-domain endpoint, like https://<name>.cognitiveservices.azure.com/
        # Your account needs the "Cognitive Services Speech User" role.
        credential = DefaultAzureCredential()
        translation_config = speech_sdk.translation.SpeechTranslationConfig(
            token_credential=credential,
            endpoint=foundry_endpoint,
        )
        # The language you will speak
        translation_config.speech_recognition_language = 'en-US'
        # The languages to translate into (one result is returned for each)
        translation_config.add_target_language('fr')
        translation_config.add_target_language('es')
        translation_config.add_target_language('hi')
        print('Ready to translate from', translation_config.speech_recognition_language)


        # Configure speech for synthesis of translations
        # A separate SpeechConfig is used to speak the translated text aloud.
        speech_config = speech_sdk.SpeechConfig(
            token_credential=credential,
            endpoint=foundry_endpoint,
        )


        # Translate user speech
        # Ask which language to hear the result in
        target_language = ''
        while target_language not in ('fr', 'es', 'hi'):
            target_language = input('\nTranslate into (fr, es, hi): ').strip().lower()

        # Listen with the default microphone
        audio_config = speech_sdk.AudioConfig(use_default_microphone=True)
        translator = speech_sdk.translation.TranslationRecognizer(
            translation_config=translation_config,
            audio_config=audio_config,
        )
        print('Speak now...')

        # recognize_once listens for one phrase, then returns the text and its translations
        result = translator.recognize_once_async().get()


        # Print and speak the translation results
        if result.reason == speech_sdk.ResultReason.TranslatedSpeech:
            print(f'\nTranslating "{result.text}"')
            # result.translations is a dictionary: language code -> translated text
            translation = result.translations[target_language]
            print(translation)

            # Pick a voice that matches the language, then speak the translation
            voices = {
                "fr": "fr-FR-HenriNeural",
                "es": "es-ES-ElviraNeural",
                "hi": "hi-IN-MadhurNeural",
            }
            speech_config.speech_synthesis_voice_name = voices[target_language]
            speech_synthesizer = speech_sdk.SpeechSynthesizer(speech_config=speech_config)
            speak = speech_synthesizer.speak_text_async(translation).get()
            if speak.reason != speech_sdk.ResultReason.SynthesizingAudioCompleted:
                print(speak.reason)
        elif result.reason == speech_sdk.ResultReason.NoMatch:
            print("No speech could be recognized.")
        elif result.reason == speech_sdk.ResultReason.Canceled:
            details = result.cancellation_details
            print(f"Translation canceled: {details.reason}")
            if details.reason == speech_sdk.CancellationReason.Error:
                print(f"Error details: {details.error_details}")



    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()