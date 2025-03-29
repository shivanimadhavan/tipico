```mermaid
erDiagram
    PROJECT {
        int id PK
        string name
        string description
        datetime created_at
        datetime updated_at
    }
    
    FILE {
        int id PK
        string file_name
        string format
        datetime created_at
        string scanned_file_name
        datetime last_scanned_at
        int project_id FK
    }
    
    METADATA {
        int id PK
        int project_id FK
        int file_id FK
    }
    
    TABLEDATA {
        int id PK
        int row_count
        int col_count
        int metadata_id FK
    }
    
    TABLECELL {
        int id PK
        int row_index
        int col_index
        int col_span
        int row_span
        string content
        int tabledata_id FK
    }

    PROJECT ||--|{ FILE : has
    PROJECT ||--|{ METADATA : has
    FILE ||--|{ METADATA : has
    METADATA ||--|{ TABLEDATA : has
    TABLEDATA ||--|{ TABLECELL : has
