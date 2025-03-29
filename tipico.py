from google import genai
from google.genai import types

import pathlib

import requests
import PIL

image_path_1 = "0.jpg"  # Replace with the actual path to your first image
image_path_2 = "1.jpg" # Replace with the actual path to your second image

#image_url_1 = "https://goo.gle/instrument-img" # Replace with the actual URL to your third image

pil_image = PIL.Image.open(image_path_1)

pil_image2 = PIL.Image.open(image_path_2)


#downloaded_image = requests.get(image_url_1)

client = genai.Client(api_key="******************************")
response = client.models.generate_content(
    model="gemini-2.0-flash-exp",
    contents=["Extract table information form these images",
              pil_image, pil_image2])
              
print(response.text)
