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
# Import types, though they might not be used if config is removed
from google.generativeai import types as genai_types


# --- Functions defined directly for clarity ---

def pdf_to_images(pdf_bytes, password=None):
    """
    Convert a PDF (in bytes) to a list of PIL Image objects (one per page).
    If a password is provided and the PDF is encrypted, attempt to authenticate.
    Uses higher resolution for better OCR potential.
    """
    try:
        doc = fitz.open("pdf", pdf_bytes)
        if doc.is_encrypted:
            if password is None:
                st.error("PDF is encrypted and requires a password.")
                raise ValueError("PDF is encrypted and requires a password.")
            if not doc.authenticate(password):
                st.error("Incorrect password for encrypted PDF.")
                raise ValueError("Incorrect password for encrypted PDF.")

        images = []
        for page_number in range(len(doc)):
            page = doc.load_page(page_number)
            zoom_x = 2.0
            zoom_y = 2.0
            mat = fitz.Matrix(zoom_x, zoom_y)
            pix = page.get_pixmap(matrix=mat)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(image)
        doc.close()
        return images
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        raise e


def parse_extracted_text(text, delimiter="|"):
    """
    Parses pipe-delimited text into a list of lists (rows).
    Handles potential extra whitespace around delimiters, empty lines,
    and removes common separator lines.
    """
    rows = []
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if all(c in '-|= ' for c in line.replace('|','')):
             continue
        cells = [cell.strip() for cell in line.split(delimiter)]
        if cells and cells[0] == '':
            cells.pop(0)
        if cells and cells[-1] == '':
            cells.pop(-1)
        if cells:
             rows.append(cells)
    return rows


def adjust_table_rows(header, rows):
    """
    Adjust each row so that it matches the header length.
    If a row has extra columns, trim them; if it has fewer, pad with empty strings.
    """
    adjusted_rows = []
    if not header:
        # st.warning("Adjusting rows skipped: No header provided.") # Reduced noise
        return rows
    num_cols = len(header)
    if num_cols == 0:
        # st.warning("Adjusting rows skipped: Header has zero columns.") # Reduced noise
        return rows

    for row_idx, row in enumerate(rows):
        if not isinstance(row, list):
             st.warning(f"Skipping row {row_idx+1}: Expected a list, got {type(row)}")
             continue
        if len(row) > num_cols:
            adjusted_row = row[:num_cols]
        elif len(row) < num_cols:
            adjusted_row = row + [""] * (num_cols - len(row))
        else:
            adjusted_row = row
        adjusted_rows.append(adjusted_row)
    return adjusted_rows


def build_json_structure(table_rows, project_id, project_name, project_description,
                         file_id, file_name, file_format, scanned_file_name,
                         metadata_id, tabledata_id):
    """
    Builds a JSON structure from extracted table rows and metadata.
    Assumes the first row in table_rows is the header.
    """
    output = {
        "project": {"id": project_id, "name": project_name, "description": project_description},
        "file": {"id": file_id, "name": file_name, "format": file_format, "scanned_file_name": scanned_file_name},
        "metadata": {"id": metadata_id, "extraction_timestamp": datetime.now().isoformat()},
        "table_data": {"id": tabledata_id, "header": table_rows[0] if table_rows else [], "rows": table_rows[1:] if len(table_rows) > 1 else []}
    }
    return output

# --- Main Streamlit App ---
def main():
    st.set_page_config(layout="wide")
    st.title("📄 PDF Table Extractor using Gemini AI")

    # --- Use original API Key Initialization (as requested) ---
    api_key = "AIzaSyC0kB6SRs4kwmeWyCjZabqCcQCQz_dIu_Y" # Replace with your actual key
    if not api_key or api_key == "YOUR_API_KEY_HERE":
         st.error("Google API Key is missing or is a placeholder. Please add your key.")
         st.stop()

    try:
        # Use the genai.Client initialization method
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize Google Gemini client: {e}")
        st.stop()
    # --- End API Key Section ---

    st.sidebar.header("Upload PDF")
    uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        pdf_password = None

        # Check for encryption
        try:
            with fitz.open("pdf", pdf_bytes) as doc: is_encrypted = doc.is_encrypted
        except Exception as e:
            try:
                doc = fitz.open("pdf", pdf_bytes); is_encrypted = doc.is_encrypted; doc.close()
            except Exception as e_inner:
                 st.error(f"Error opening PDF to check encryption: {e_inner}"); return

        if is_encrypted:
            st.sidebar.info("🔒 This PDF is password protected.")
            pdf_password = st.sidebar.text_input("Enter PDF password", type="password")
            if not pdf_password:
                st.sidebar.warning("Please enter the password to continue."); return

        # Convert PDF pages to images
        try:
            with st.spinner("Converting PDF to images..."):
                images = pdf_to_images(pdf_bytes, password=pdf_password if is_encrypted else None)
        except ValueError as ve: return
        except Exception as e: st.error(f"Error during PDF conversion: {e}"); return

        if not images: st.warning("Could not extract pages."); return

        st.sidebar.success(f"✅ PDF uploaded with {len(images)} page(s).")
        st.subheader("Preview of Page 1")
        try: st.image(images[0], caption="Preview of Page 1", use_container_width=True)
        except Exception as img_e: st.error(f"Could not display preview: {img_e}")

        st.sidebar.markdown("---")
        # --- Configuration Options ---
        st.sidebar.subheader("Extraction Settings")
        chunk_height = st.sidebar.slider("Chunk Height (px)", 300, 1500, 800, 50)
        overlap = st.sidebar.slider("Chunk Overlap (px)", 0, 300, 100, 10)
        # Model selection - MUST match models usable with client.models interface
        # Typically older or specific model names might be needed. Flash might not work here.
        # Let's stick to the one potentially used in the original snippet or a known compatible one.
        # Note: "gemini-2.0-flash-exp" was in the original code's comment, let's try that.
        # If this model name causes errors, you'll need to find one compatible with client.models
        model_name = st.sidebar.selectbox(
            "Select AI Model (ensure compatibility with client.models)",
            ["gemini-1.5-flash-latest", "gemini-pro"], # Provide likely candidates
             index=0 # Default to flash, but might need 'gemini-pro'
        )
        # --- End Configuration Options ---

        submit_button = st.sidebar.button("Extract Tables", type="primary")

        if submit_button:
            output_folder = "output_chunks"
            if not os.path.exists(output_folder): os.makedirs(output_folder)

            # Refined prompt
            prompt = """Extract all table data meticulously from the provided image chunk.
Format the output STRICTLY as pipe-delimited text (|).
- Ensure every row has a consistent number of columns, matching the table's structure. Use pipes `|` as delimiters.
- Represent empty cells explicitly using consecutive pipes (e.g., `value1||value3`). If a row starts or ends with empty cells, include leading/trailing pipes accordingly (e.g., `|value1|value2||` or `||value1|value2`).
- Do NOT include any explanatory text, greetings, introductions, summaries, or markdown formatting like backticks (`). Only output the raw pipe-delimited table data.
- Preserve the original content within cells accurately, including spacing within the cell if relevant.
- Ignore any text clearly outside of table structures.
- Remove lines that are only visual separators like '----' or '===='.
"""
            # Compute total chunks
            total_chunks = 0
            for image in images:
                 page_height = image.height
                 if page_height <= chunk_height: total_chunks += 1
                 else: step = max(1, chunk_height - overlap); total_chunks += 1 + math.ceil(max(0, page_height - chunk_height) / step)
            if total_chunks == 0: total_chunks = 1

            st.info(f"🚀 Starting extraction using model: `models/{model_name}` via client.models...")
            progress_bar = st.progress(0)
            status_text = st.empty()

            all_extracted_text_list = []
            global_chunk_counter = 0

            for page_idx, page_image in enumerate(images):
                page_folder = os.path.join(output_folder, f"page_{page_idx+1}")
                if not os.path.exists(page_folder): os.makedirs(page_folder)

                page_extracted_text = ""
                page_height, page_width = page_image.height, page_image.width

                # Calculate chunks for page
                if page_height <= chunk_height: num_chunks_on_page = 1
                else: step = max(1, chunk_height - overlap); num_chunks_on_page = 1 + math.ceil(max(0, page_height - chunk_height) / step)

                status_text.text(f"⏳ Processing Page {page_idx+1}/{len(images)}...")

                for chunk_idx in range(num_chunks_on_page):
                    current_chunk_num = chunk_idx + 1
                    step = max(1, chunk_height - overlap)
                    top = max(0, chunk_idx * step)
                    bottom = min(page_height, top + chunk_height)

                    if top >= page_height: continue
                    if chunk_idx > 0 :
                         prev_bottom = min(page_height, max(0, (chunk_idx-1)*step) + chunk_height)
                         if bottom <= prev_bottom + overlap * 0.6 : continue

                    chunk = page_image.crop((0, top, page_width, bottom))

                    # Save chunk image (optional debugging)
                    # chunk_filename = os.path.join(page_folder, f"chunk_{current_chunk_num}.png")
                    # try: chunk.save(chunk_filename)
                    # except Exception as save_e: st.warning(f"Could not save chunk image {chunk_filename}: {save_e}")

                    status_text.text(f"⏳ Processing Page {page_idx+1}/{len(images)}, Chunk {current_chunk_num}/{num_chunks_on_page}...")

                    # --- Call Gemini API using client.models.generate_content ---
                    try:
                        # IMPORTANT: Removed 'generation_config' and 'safety_settings' arguments
                        # as they caused the TypeError with client.models.generate_content.
                        # Model will use default temperature and safety settings.
                        response = client.models.generate_content(
                            # Ensure model name format is correct (e.g., models/gemini-pro)
                            model=f'models/{model_name}',
                            contents=[prompt, chunk]
                            # generation_config=... # REMOVED
                            # safety_settings=... # REMOVED
                        )

                        # Accessing the text - primarily check response.text with this client method
                        chunk_text = ""
                        if hasattr(response, 'text'):
                             chunk_text = response.text
                        elif response.candidates: # Fallback check
                             if (response.candidates[0].content and
                                 response.candidates[0].content.parts and
                                 hasattr(response.candidates[0].content.parts[0], 'text')):
                                 chunk_text = response.candidates[0].content.parts[0].text

                        # Add newline separator between chunks
                        page_extracted_text += chunk_text + "\n" if chunk_text else ""

                    except Exception as e:
                        error_type = type(e).__name__
                        st.error(f"⚠️ API Error chunk {current_chunk_num} (Page {page_idx+1}): {error_type} - {e}")
                        page_extracted_text += f"[API Error: {error_type} in chunk {current_chunk_num}]\n"
                    # --- End Call Gemini API ---

                    global_chunk_counter += 1
                    progress_percentage = min(1.0, global_chunk_counter / total_chunks) if total_chunks > 0 else 0
                    progress_bar.progress(progress_percentage)

                all_extracted_text_list.append(page_extracted_text.strip())

                # --- Process and Display Page Data ---
                st.markdown(f"### Extracted Data - Page {page_idx+1}")
                page_results_container = st.container()

                if page_extracted_text.strip():
                    page_table_rows = parse_extracted_text(page_extracted_text, delimiter="|")

                    if page_table_rows:
                        header, data_rows, header_found_idx = [], [], -1
                        for i, row in enumerate(page_table_rows):
                            if any(cell and cell.strip() for cell in row):
                                header = row; header_found_idx = i; break
                        if header_found_idx != -1:
                            data_rows = [r for r in page_table_rows[header_found_idx + 1:] if not (len(r)==1 and r[0].startswith("[API Error:"))]
                            adjusted_data_rows = adjust_table_rows(header, data_rows)
                            if adjusted_data_rows:
                                try:
                                    df_page = pd.DataFrame(adjusted_data_rows, columns=header)
                                    page_results_container.dataframe(df_page)
                                    csv_filename = os.path.join(page_folder, f"page_{page_idx+1}_data.csv")
                                    try:
                                        df_page.to_csv(csv_filename, index=False)
                                        page_results_container.caption(f"Page data saved: `{csv_filename}`")
                                    except Exception as csv_e: page_results_container.warning(f"Save failed: {csv_e}")
                                except ValueError as ve:
                                     page_results_container.error(f"DF Error page {page_idx+1}: {ve}")
                                     page_results_container.text(f"Header ({len(header)}): {header}")
                                     if adjusted_data_rows: page_results_container.text(f"Row 1 ({len(adjusted_data_rows[0])}): {adjusted_data_rows[0]}")
                                except Exception as e: page_results_container.error(f"DF Error page {page_idx+1}: {e}")
                            else: page_results_container.info(f"Page {page_idx+1}: Header found, no data rows."); page_results_container.text(f"Header: {header}")
                        else: page_results_container.warning(f"No header row found page {page_idx+1}.")
                    else: page_results_container.warning(f"No table rows parsed page {page_idx+1}.")
                else: page_results_container.info(f"No text extracted page {page_idx+1}.")
                st.markdown("---")
                # --- End Process and Display Page Data ---

            status_text.text("✅ Extraction Complete!")
            progress_bar.progress(1.0)

            # --- Combine and Process Global Data ---
            st.markdown("## Combined Extracted Data (All Pages)")
            combined_results_container = st.container()
            full_extracted_text = "\n".join(all_extracted_text_list).strip()

            if full_extracted_text:
                global_table_rows = parse_extracted_text(full_extracted_text, delimiter="|")
                if global_table_rows:
                    global_header, global_data_rows, header_found = [], [], False
                    for i, row in enumerate(global_table_rows):
                        if any(cell and cell.strip() for cell in row):
                            global_header = row
                            global_data_rows = [r for r in global_table_rows[i+1:] if not (len(r)==1 and r[0].startswith("[API Error:"))]
                            header_found = True; break
                    if header_found:
                        adjusted_global_rows = adjust_table_rows(global_header, global_data_rows)
                        if adjusted_global_rows:
                            try:
                                df_global = pd.DataFrame(adjusted_global_rows, columns=global_header)
                                combined_results_container.dataframe(df_global)
                                global_csv_filename = os.path.join(output_folder, "combined_data.csv")
                                try:
                                    df_global.to_csv(global_csv_filename, index=False)
                                    combined_results_container.caption(f"Combined data saved: `{global_csv_filename}`")
                                except Exception as csv_e: combined_results_container.warning(f"Save failed: {csv_e}")

                                # --- JSON Output ---
                                st.subheader("JSON Output Structure")
                                project_id, file_id, metadata_id, tabledata_id = 101, 102, 103, 104
                                project_name, project_desc = "PDF_Extraction", f"From: {uploaded_file.name}"
                                json_table_rows = [global_header] + adjusted_global_rows
                                json_output = build_json_structure(json_table_rows, project_id, project_name, project_desc, file_id, "combined_data.csv", "csv", uploaded_file.name, metadata_id, tabledata_id)
                                json_str = json.dumps(json_output, indent=2)
                                st.json(json_str)
                                st.download_button("Download JSON", json_str, "extracted_data.json", "application/json")
                                # --- End JSON Output ---
                            except ValueError as ve: combined_results_container.error(f"Global DF Error: {ve}")
                            except Exception as e: combined_results_container.error(f"Global DF Error: {e}")
                        else: combined_results_container.info("Global header found, no data rows.")
                    else: combined_results_container.warning("No global header found.")
                else: combined_results_container.error("No table rows parsed from combined text.")
            else: combined_results_container.error("No text extracted overall.")
    else:
        st.info("👈 Upload a PDF file using the sidebar to begin.")

if __name__ == "__main__":
    main()