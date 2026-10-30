from dotenv import load_dotenv
import os

# import namespaces
# TextTranslationClient: client for the Azure AI Translator text translation API
from azure.ai.translation.text import TextTranslationClient
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential



def main():
    try:
        # Clear the console 
        os.system('cls' if os.name == 'nt' else 'clear')

        # Get Configuration Settings
        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')

        # Create client using endpoint and credential
        # Uses your Azure sign-in instead of an API key, so no secret is stored.
        # Your account needs a role such as "Cognitive Services User" on the resource.
        credential = DefaultAzureCredential()
        client = TextTranslationClient(credential=credential, endpoint=foundry_endpoint)


        ## Choose target language
        # Translator uses short language codes, for example: fr (French),
        # es (Spanish), de (German), ja (Japanese), lt (Lithuanian).
        target_language = input("Enter the target language code (for example: fr, es, de, ja): ").strip()


        # Translate text
        # Loop so you can translate several phrases into the same language.
        while True:
            text = input("\nEnter text to translate (or 'quit'): ").strip()
            if text.lower() == "quit" or len(text) == 0:
                break

            # translate() takes a LIST of texts (body) and one or more target
            # languages (to_language). We don't set the source language, so the
            # service detects it automatically.
            # (In library version 2.0 the old `to=` argument was renamed `to_language=`.)
            response = client.translate(body=[text], to_language=[target_language])

            # One result per input text; each has one translation per target language
            result = response[0]
            if result.detected_language:
                print(f"Detected language: {result.detected_language.language} "
                      f"({result.detected_language.score:.0%} confidence)")
            for translation in result.translations:
                print(f"Translation ({translation.to}): {translation.text}")


    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()