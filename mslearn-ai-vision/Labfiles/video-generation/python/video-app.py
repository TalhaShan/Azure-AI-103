import os
from dotenv import load_dotenv

# Add references
import time
# OpenAI: the OpenAI SDK client, pointed at the Foundry v1 API
from openai import OpenAI
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
# get_bearer_token_provider: turns that login into tokens the client can send
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Get configuration settings
load_dotenv()
endpoint = os.getenv("OPENAI_BASE_URL")
model_deployment = os.getenv("MODEL_DEPLOYMENT")

# Get the token provider for Azure OpenAI authentication
# Uses your Azure sign-in instead of an API key, so no secret is stored.
# Your account needs a role such as "Cognitive Services OpenAI User".
# If you get a 401 about the audience, try the scope
# "https://cognitiveservices.azure.com/.default" instead.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

# One client shared by all the functions below.
# OPENAI_BASE_URL should end with /openai/v1/, and the token provider is passed
# where the API key normally goes.
client = OpenAI(
    base_url=endpoint,
    api_key=token_provider,
)

def main(): 

    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')
        
    try:       
        print("=== Video Generation Application ===\n")
        

        print("Step 1: Generating video from text prompt...")
        # Generate a video from a text prompt
        # Video generation is asynchronous: create() only starts the job. The
        # size and length (seconds) are set here, and poll_video_status then
        # waits until the job has finished.
        video = client.videos.create(
            model=model_deployment,
            prompt="A robot walks through a rainy city street at dusk, neon signs reflecting in puddles",
            size="1280x720",
            seconds="4",
        )
        print(f"Video creation started. ID: {video.id}")
        video = poll_video_status(video.id)

        if video.status == "completed":
            download_video(video.id, "original_video.mp4")
            original_video_id = video.id
            
            # Step 2: Remix the video with a different style
            print("\nStep 2: Remixing the video with a new color palette...")
            remixed = remix_video(
                original_video_id,
                "Shift the color palette to warm sunset tones with golden light"
            )
            
            if remixed.status == "completed":
                download_video(remixed.id, "remixed_video.mp4")

        print("\nStep 3: Generating a video from a reference image...")
        # Generate a video from a reference image
        # The image becomes the first frame. Its resolution must exactly match
        # the video size (1280x720), and it must not contain human faces.
        # Set REFERENCE_IMAGE in .env to your image file.
        image_path = os.getenv("REFERENCE_IMAGE", "reference_image.png")
        image_video = generate_video_from_image(
            image_path,
            "The camera slowly pans across the landscape as clouds drift overhead",
            size="1280x720",
            seconds=4,
        )
        if image_video.status == "completed":
            download_video(image_video.id, "image_video.mp4")

        print("\n=== Video generation complete ===")

    except Exception as ex:
        print(ex)


def poll_video_status(video_id):
    """Poll the video status every 20 seconds until it completes or fails."""

    # Poll video status until completion
    # queued / in_progress mean "still working"; the other states are final.
    video = client.videos.retrieve(video_id)
    while video.status not in ["completed", "failed", "cancelled"]:
        print(f"Status: {video.status}. Waiting 20 seconds...")
        time.sleep(20)
        video = client.videos.retrieve(video_id)

    print(f"Final status: {video.status}")
    if video.status == "failed":
        print(f"Generation failed: {video.error}")
    return video


def remix_video(video_id, prompt):
    """Create a remix of an existing video with a new prompt."""
    print(f"Starting video remix for: {video_id}")
    
    # Remix an existing video
    # remix() keeps the structure of the original video and applies the new
    # prompt. It creates a new video job, so we poll it just like before.
    remixed = client.videos.remix(video_id=video_id, prompt=prompt)
    print(f"Remix started. ID: {remixed.id}")
    return poll_video_status(remixed.id)
    

def download_video(video_id, output_filename="output.mp4"):
    """Download the completed video to a local file."""
    print(f"Downloading video {video_id}...")

    # Download the completed video
    # variant="video" asks for the .mp4 file (other variants are thumbnails).
    content = client.videos.download_content(video_id, variant="video")
    content.write_to_file(output_filename)
    print(f"Video saved to {output_filename}")


def generate_video_from_image(image_path, prompt, size="1280x720", seconds=8):
    """Generate a video using a reference image as the starting frame."""
    print(f"Starting video generation from image: {image_path}")
    
    # Create the video with an image reference
    # input_reference takes the image file, opened in binary mode.
    with open(image_path, "rb") as image_file:
        video = client.videos.create(
            model=model_deployment,
            prompt=prompt,
            size=size,
            seconds=str(seconds),
            input_reference=image_file,
        )
    

    print(f"Video creation started. ID: {video.id}")
    print(f"Initial status: {video.status}")
    
    # Poll for completion
    video = poll_video_status(video.id)
    return video

if __name__ == '__main__': 
    main()