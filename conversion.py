import json
from datetime import datetime
from google import genai
from google.genai import types
import PIL


def parse_extracted_text(extracted_text, delimiter="|"):
    """
    Parses the raw extracted table text into a list of rows,
    where each row is a list of columns.
    This version skips empty lines and prints each parsed row.
    """
    lines = [line for line in extracted_text.strip().split("\n") if line.strip()]
    table_rows = []
    for line in lines:
        columns = [col.strip() for col in line.split(delimiter)]
        print("Parsed row:", columns)  # Debug print
        table_rows.append(columns)
    return table_rows


def build_json_structure(
    table_rows,
    project_id,
    project_name,
    project_description,
    file_id,
    file_name,
    file_format,
    scanned_file_name,
    metadata_id,
    tabledata_id
):
    """
    Builds the JSON structure that matches your ER diagram (PROJECT, FILE, METADATA, TABLEDATA, TABLECELL).
    No hard-coded IDs or timestamps; uses current time for created_at/updated_at, 
    and takes other info from function arguments.
    """
    now = datetime.now().isoformat()

    result = {
        "PROJECT": {
            "id": project_id,
            "name": project_name,
            "description": project_description,
            "created_at": now,
            "updated_at": now
        },
        "FILE": {
            "id": file_id,
            "file_name": file_name,
            "format": file_format,
            "created_at": now,
            "scanned_file_name": scanned_file_name,
            "last_scanned_at": now,
            "project_id": project_id
        },
        "METADATA": {
            "id": metadata_id,
            "project_id": project_id,
            "file_id": file_id
        },
        "TABLEDATA": {
            "id": tabledata_id,
            "row_count": len(table_rows),
            "col_count": len(table_rows[0]) if table_rows else 0,
            "metadata_id": metadata_id
        },
        "TABLECELL": []
    }

    # Fill TABLECELL with every cell from the table (header + data rows)
    cell_id = 1
    for r_idx, row in enumerate(table_rows):
        for c_idx, col_content in enumerate(row):
            cell_obj = {
                "id": cell_id,
                "row_index": r_idx,
                "col_index": c_idx,
                "col_span": 1,
                "row_span": 1,
                "content": col_content,
                "tabledata_id": tabledata_id
            }
            result["TABLECELL"].append(cell_obj)
            cell_id += 1

    return result
