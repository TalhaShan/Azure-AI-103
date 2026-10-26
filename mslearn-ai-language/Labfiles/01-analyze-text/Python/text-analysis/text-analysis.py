from dotenv import load_dotenv
import os

# Import namespaces
# TextAnalyticsClient: client for the Azure AI Language text analysis features
from azure.ai.textanalytics import TextAnalyticsClient
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential


def main():
    try:
        # Clear the console
        os.system('cls' if os.name == 'nt' else 'clear')

        # Get Configuration Settings
        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')


        # Create client using endpoint
        # Uses your Azure sign-in instead of an API key, so no secret is stored.
        # Your account needs a role such as "Cognitive Services User" on the resource.
        credential = DefaultAzureCredential()
        client = TextAnalyticsClient(endpoint=foundry_endpoint, credential=credential)


        # Analyze each text file in the reviews folder
        reviews_folder = 'reviews'
        for file_name in os.listdir(reviews_folder):
            # Read the file contents
            print('\n-------------\n' + file_name)
            text = open(os.path.join(reviews_folder, file_name), encoding='utf8').read()
            print('\n' + text)

            # Get language
            # The service takes a list of documents and returns one result per
            # document, so we send one text and take the first result [0].
            detected_language = client.detect_language(documents=[text])[0]
            print('\nLanguage: {}'.format(detected_language.primary_language.name))


            # Get entities
            # Entities are things the text mentions, such as people, places,
            # organizations and dates, each with a category.
            entities = client.recognize_entities(documents=[text])[0].entities
            if len(entities) > 0:
                print("\nEntities")
                for entity in entities:
                    print('\t{} ({})'.format(entity.text, entity.category))


            # Get PII
            # PII is personal data such as emails, phone numbers and addresses.
            # The result also includes a copy of the text with PII masked out.
            pii_result = client.recognize_pii_entities(documents=[text])[0]
            if len(pii_result.entities) > 0:
                print("\nPII Entities")
                for entity in pii_result.entities:
                    print('\t{} ({})'.format(entity.text, entity.category))
                print("\nRedacted text:\n" + pii_result.redacted_text)


    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()