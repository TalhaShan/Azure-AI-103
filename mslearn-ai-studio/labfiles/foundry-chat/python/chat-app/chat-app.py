
import os
from dotenv import load_dotenv
from openai import AzureOpenAI


def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        # Get configuration settings
        load_dotenv()
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

        # Initialize the Azure OpenAI client
        openai_client = AzureOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=api_key,
            api_version=api_version
        )

        # Loop until the user wants to quit
        while True:
            input_text = input(
                '\nEnter a prompt (or type "quit" to exit): '
            )

            if input_text.lower() == "quit":
                break

            if len(input_text.strip()) == 0:
                print("Please enter a prompt.")
                continue

            # Get a response

            # Chat Completions API (commented out)
            # completion = openai_client.chat.completions.create(
            #     model=model_deployment,
            #     messages=[
            #         {
            #             "role": "system",
            #             "content": (
            #                 "You are a helpful AI assistant that "
            #                 "answers questions clearly and accurately."
            #             )
            #         },
            #         {
            #             "role": "user",
            #             "content": input_text
            #         }
            #     ]
            # )
            #
            # print(completion.choices[0].message.content)

            # Responses API (active)
            responses = openai_client.responses.create(
                model=model_deployment,
                instructions=(
                    "You are a helpful AI assistant that "
                    "answers questions clearly and accurately."
                ),
                input=input_text
            )

            print(responses.output_text)

    except Exception as ex:
        print(f"An error occurred: {ex}")


if __name__ == '__main__':
    main()



# Responses API with conversation context
# responses = openai_client.responses.create(
#     model=model_deployment,
#     instructions=(
#         "You are a helpful AI assistant that "
#         "answers questions clearly and accurately."
#     ),
#     input=input_text,
#     previous_response_id=previous_response_id
# )

# print(responses.output_text)

# # Save the ID for the next request
# previous_response_id = responses.id