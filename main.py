import os
import streamlit as st
import io
import json
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image
import fitz  # PyMuPDF for PDF conversion
import math
from google import genai
from google.genai import types
from conversion import parse_extracted_text, build_json_structure

def pdf_to_images(pdf_bytes, password=None):
    """
    Convert a PDF (in bytes) to a list of PIL Image objects (one per page).
    If a password is provided and the PDF is encrypted, attempt to authenticate.
    """
    doc = fitz.open("pdf", pdf_bytes)
    if doc.is_encrypted:
        if password is None:
            raise ValueError("PDF is encrypted and requires a password.")
        if not doc.authenticate(password):
            raise ValueError("Incorrect password for encrypted PDF.")
    
    images = []
    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        pix = page.get_pixmap()
        # Convert pixmap to a PIL Image in RGB mode
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(image)
    return images

def adjust_table_rows(header, rows):
    """
    Adjust each row so that it matches the header length.
    If a row has extra columns, trim them; if it has fewer, pad with empty strings.
    """
    adjusted_rows = []
    num_cols = len(header)
    for row in rows:
        if len(row) > num_cols:
            row = row[:num_cols]
        elif len(row) < num_cols:
            row = row + [""] * (num_cols - len(row))
        adjusted_rows.append(row)
    return adjusted_rows

def main():
    st.title("Upload PDF and Process Data")
    
    # Upload PDF file
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
    
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        # Try to open the PDF to check if it's encrypted
        try:
            doc = fitz.open("pdf", pdf_bytes)
        except Exception as e:
            st.error(f"Error opening PDF: {e}")
            return

        pdf_password = None
        if doc.is_encrypted:
            st.info("This PDF is password protected.")
            pdf_password = st.text_input("Enter PDF password", type="password")
            if not pdf_password:
                st.warning("Please enter the password to continue.")
                return  # Wait for the password input

        # Convert PDF pages to images
        try:
            with st.spinner("Converting PDF to images..."):
                images = pdf_to_images(pdf_bytes, password=pdf_password)
        except ValueError as ve:
            st.error(str(ve))
            return
        
        st.success(f"PDF uploaded with {len(images)} page(s).")
        
        # Display a preview of the first page
        if images:
            st.image(images[0], caption="Preview of Page 1", use_container_width=True)
        
        submit_button = st.button("Submit")
        if submit_button:
            client = genai.Client(api_key="****************************")
            
            # Create an output folder to store all chunk images and CSV files
            output_folder = "output_chunks"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            
            # Set chunk height to 500 pixels (approx. 10 rows per chunk) and define overlap (50 pixels)
            chunk_height = 500
            overlap = 50
            
            # Compute total chunks for overall progress tracking
            total_chunks = sum(math.ceil(image.height / chunk_height) for image in images)
            
            chunk_counter = 0
            all_extracted_text = ""
            progress_bar = st.progress(0)
            
            # Process each page separately
            for page_idx, page_image in enumerate(images):
                # Create a folder for the page
                page_folder = os.path.join(output_folder, f"page_{page_idx+1}")
                if not os.path.exists(page_folder):
                    os.makedirs(page_folder)
                    
                page_extracted_text = ""
                num_chunks = math.ceil(page_image.height / chunk_height)
                for chunk_idx in range(num_chunks):
                    left = 0
                    # Overlap: move top up by 'overlap' for chunks except the first
                    top = max(0, chunk_idx * chunk_height - (overlap if chunk_idx > 0 else 0))
                    right = page_image.width
                    # Extend bottom by overlap if within image bounds
                    bottom = min(page_image.height, (chunk_idx + 1) * chunk_height + overlap)
                    chunk = page_image.crop((left, top, right, bottom))
                    
                    # Save the chunk image in the corresponding page folder
                    chunk_filename = os.path.join(page_folder, f"chunk_{chunk_idx+1}.png")
                    chunk.save(chunk_filename)
                    
                    with st.spinner(f"Processing page {page_idx+1}, chunk {chunk_idx+1} of {num_chunks}..."):
                        response = client.models.generate_content(
                            model="gemini-2.0-flash-exp",
                            contents=[
                                "Extract table information from these images. Return all data, including headings, as pipe-delimited text. Remove lines containing '-----'. Do not add any extra text beyond the table data.",
                                chunk
                            ]
                        )
                        page_extracted_text += response.text + "\n"
                        all_extracted_text += response.text + "\n"
                    
                    chunk_counter += 1
                    progress_bar.progress(chunk_counter / total_chunks)
                
                # Parse the extracted text for the current page and save as CSV.
                page_table_rows = parse_extracted_text(page_extracted_text, delimiter="|")
                if page_table_rows:
                    header = page_table_rows[0]
                    data_rows = adjust_table_rows(header, page_table_rows[1:])
                    df_page = pd.DataFrame(data_rows, columns=header)
                    csv_filename = os.path.join(page_folder, "page_data.csv")
                    df_page.to_csv(csv_filename, index=False)
                    
                    # Display the table for this page on the front end.
                    st.subheader(f"Extracted Table Data {page_idx+1}")
                    st.dataframe(df_page)
            
            # Optionally, process the global extracted text for overall data.
            table_rows = parse_extracted_text(all_extracted_text, delimiter="|")
            
            # Define project and file information
            project_id = 101
            file_id = 102
            metadata_id = 103
            tabledata_id = 104
            project_name = "MyProject"
            project_description = "Extracted from PDF images"
            file_name = "extracted_data.txt"
            file_format = "txt"
            scanned_file_name = "extracted_data_scanned.txt"
            
            # Build the JSON structure using your custom function
            json_output = build_json_structure(
                table_rows=table_rows,
                project_id=project_id,
                project_name=project_name,
                project_description=project_description,
                file_id=file_id,
                file_name=file_name,
                file_format=file_format,
                scanned_file_name=scanned_file_name,
                metadata_id=metadata_id,
                tabledata_id=tabledata_id
            )
            
            json_str = json.dumps(json_output, indent=2)
            
            # Optionally, display a global DataFrame from all pages.
            if table_rows:
                header = table_rows[0]
                data_rows = adjust_table_rows(header, table_rows[1:])
                df = pd.DataFrame(data_rows, columns=header)
                st.subheader("Global Extracted Table Data")
                st.dataframe(df)
            else:
                st.error("No table rows extracted.")
    else:
        st.info("Please upload a PDF file.")

if __name__ == "__main__":
    main()
