# Tipico PDF Table Extraction

This project extracts tabular data from PDF documents by converting PDF pages into images, processing them in chunks, and using Google's Gemini model to recognize and reconstruct table content. It is designed to handle scanned or image-based PDFs and convert the extracted data into structured tabular output. :contentReference[oaicite:0]{index=0}

## Features
- Upload and process PDF files, including password-protected PDFs
- Convert PDF pages into images for OCR-style extraction
- Chunk large page images for better table recognition
- Extract table content using Gemini
- Parse extracted text into rows and columns
- Display structured table data in a Streamlit interface
- Build JSON output for project, file, metadata, table data, and table cell records :contentReference[oaicite:1]{index=1}

## Tech Stack
Python, Streamlit, PyMuPDF, Pillow, Pandas, Google Gemini API. :contentReference[oaicite:2]{index=2}

## Workflow
PDF Input → Page-to-Image Conversion → Image Chunking → Gemini-based Table Extraction → Text Parsing → Structured Table/JSON Output. :contentReference[oaicite:3]{index=3}
