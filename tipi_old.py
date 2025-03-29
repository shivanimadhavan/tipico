import fitz  # PyMuPDF
import os
import json
from PIL import Image
from google import genai
import PIL

def segment_image(image_path, segment_size=(500, 500)):
    """Splits an image into smaller chunks of given segment size."""
    image = Image.open(image_path)
    width, height = image.size
    
    segments = []
    for top in range(0, height, segment_size[1]):
        for left in range(0, width, segment_size[0]):
            box = (left, top, left + segment_size[0], top + segment_size[1])
            segment = image.crop(box)
            segment_path = f"{image_path}_segment_{left}_{top}.png"
            segment.save(segment_path)
            segments.append(segment_path)
    
    return segments

# Initialize Google GenAI client
client = genai.Client(api_key="*******************************")

def pdf_to_images(pdf_path, output_folder, zoom_x=2, zoom_y=2):
    """Converts a PDF into images, saving each page as a PNG."""
    pdf_document = fitz.open(pdf_path)
    pdf_document.authenticate("mPuKdWX5Flkdb57LzhnQ")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    image_paths = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        mat = fitz.Matrix(zoom_x, zoom_y)
        pix = page.get_pixmap(matrix=mat)
        
        image_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
        pix.save(image_path)
        image_paths.append(image_path)
        
        print(f"Saved {image_path}")
    
    pdf_document.close()
    return image_paths

def extract_text_from_images(image_paths):
    """Extracts text in table format from images using Google GenAI."""
    extracted_data = []
    
    for image_path in image_paths:
        segments = segment_image(image_path)  # Segment the image first
        
        for segment_path in segments:
            pil_image = PIL.Image.open(segment_path)
            
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[f"Extract table information from {segment_path}", pil_image]
            )
            
            extracted_data.append({"image": segment_path, "data": response.text})
            print(f"Processed: {segment_path}")
    
    return extracted_data

def save_to_json(data, output_file="extracted_data.json"):
    """Saves extracted data into a structured JSON file."""
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    print(f"Extraction complete. Data saved to {output_file}")

# Example usage
pdf_path = "omar1993.pdf"  # Replace with actual PDF file
output_folder = "output_images"

# Convert PDF to images
image_paths = pdf_to_images(pdf_path, output_folder)

# Extract text from segmented images
extracted_data = extract_text_from_images(image_paths)

# Save extracted data to JSON
save_to_json(extracted_data)
