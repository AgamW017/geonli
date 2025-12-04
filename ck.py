import requests
import base64
import json

# Use 127.0.0.1 to use the SSH tunnel
URL = "http://127.0.0.1:7860/run/predict"

# Path to your local image
image_path = "/Users/utkarshpatel/Storage/inter iit/make-it-work/05865_0000.png"

# 1. Convert image to Base64
with open(image_path, "rb") as f:
    encoded_string = base64.b64encode(f.read()).decode('utf-8')
    # Gradio 3.x expects the data URI prefix
    base64_image = f"data:image/png;base64,{encoded_string}"

# 2. Prepare Payload
payload = {
    "data": [
        base64_image,       # Argument 1: Image
        "Describe this"     # Argument 2: Prompt
    ]
}

# 3. Send Request
print("Sending raw HTTP request...")
response = requests.post(URL, json=payload)

if response.status_code == 200:
    # Gradio 3 returns data in specific JSON format
    print("Success!")
    print(response.json()['data'][0])
else:
    print(f"Error: {response.status_code}")
    print(response.text)