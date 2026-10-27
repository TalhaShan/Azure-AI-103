import os
from pathlib import Path
from playsound3 import playsound
from dotenv import load_dotenv

# Import namespaces
# AzureOpenAI: OpenAI SDK client that talks to Azure OpenAI / Foundry models
from openai import AzureOpenAI
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
# get_bearer_token_provider: turns that login into tokens the client can send
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    try:
        # Clear the console
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Get Configuration Settings
        load_dotenv()
        endpoint = os.getenv("MODEL_ENDPOINT")
        model_deployment = os.getenv("MODEL_NAME")
        file_path = Path(__file__).parent / "speech.wav"
        
        # Play the speech file
        playsound(file_path)
        
        # Create the Azure OpenAI client
        # Uses your Azure sign-in instead of an API key, so no secret is stored.
        # Your account needs a role such as "Cognitive Services OpenAI User"
        # on the resource.
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://ai.azure.com/.default",
        )
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2025-03-01-preview",
        )

        
        # Call model to transcribe audio file
        # Opens the audio file in binary mode and sends it to your speech-to-text
        # deployment (e.g. gpt-4o-transcribe or whisper). The result's .text
        # holds the recognized words.
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=model_deployment,
                file=audio_file,
            )

        print("\nTranscription:")
        print(transcription.text)


    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()