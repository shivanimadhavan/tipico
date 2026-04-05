# Tipico PDF Table Extraction

This project extracts tabular data from PDF documents by converting PDF pages into images, processing them in chunks, and using Google's Gemini model to recognize and reconstruct table content. It is designed to handle scanned or image-based PDFs and convert the extracted data into structured tabular output.

## Features
- Upload and process PDF files, including password-protected PDFs
- Convert PDF pages into images for OCR-style extraction
- Chunk large page images for better table recognition
- Extract table content using Gemini
- Parse extracted text into rows and columns
- Display structured table data in a Streamlit interface

## Tech Stack
Python, Streamlit, PyMuPDF, Pillow, Pandas, Google Gemini API.

## Workflow
PDF Input → Page-to-Image Conversion → Image Chunking → Gemini-based Table Extraction → Text Parsing → Structured Table/JSON Output.
