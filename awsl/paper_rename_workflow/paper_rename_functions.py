import os
import shutil
import base64
from io import BytesIO
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from pdf2image import convert_from_path
import logging
from awsl.paper_rename_workflow.prompts import get_vision_prompt

logger = logging.getLogger(__name__)

class Book(BaseModel):
    book_name: str = Field(description="Book name")
    authors_names: list[str] = Field(description="array with authors names, empty if not found")
    year: str = Field(description="the year book was published, `None` if not found")

def get_files(state: dict, config: dict) -> dict:
    folder_path = state.get("drafts_folder_path")
    return {"file_paths": [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".pdf")]}

def read_pdf_file(state: dict, config: dict) -> dict:
    pages_to_read = config.get("metadata", {}).get("pages_to_read")
    file_path = state.get("RenameLoop.remaining_file_paths_to_process")[0]
    # Render the first 2 pages of PDF as images using pdf2image
    try:
        # Convert first 2 pages to images at 200 DPI for good quality without being too large
        page_images = convert_from_path(
            file_path,
            dpi=200, 
            first_page=1, 
            last_page=pages_to_read
        )
        print(f"Successfully rendered {len(page_images)} PDF pages as images")
        return {"pages": page_images, "file_path": file_path}
    except Exception as e:
        print(f"Error rendering PDF pages as images: {str(e)}")
        raise e

def extract_metadata(state: dict, config: dict) -> dict:
    def encode_image_for_llm(image):
        byte_arr = BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(byte_arr, format="JPEG")
        img_str = base64.b64encode(byte_arr.getvalue()).decode('utf-8')
        return img_str
    
    pages = state.get("ReadPdfFile.pages")
    llm_model = config.get("metadata", {}).get("model")
    base_url = config.get("metadata", {}).get("base_url")
    temperature = config.get("metadata", {}).get("temperature")

    vision_llm = ChatOpenAI(
        model = llm_model,
        base_url = base_url,
        temperature=temperature,
        api_key="sk",
    )
    structured_vision_llm = vision_llm.with_structured_output(Book, method="json_mode")
    vision_book = None

    if not pages or len(pages) == 0:          
        logger.error("No pages to read")
        raise Exception("No pages to read")
        
    content = [
        {
            "type":"text",
            "text": get_vision_prompt()
        }
    ]
    
    # Add each page as an image
    for page in pages:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image_for_llm(page)}"
            }
        })
    
    vision_messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    vision_book = structured_vision_llm.invoke(vision_messages)
    logger.info(f"Extracted book: {vision_book}")

    return {"title": vision_book.book_name, "authors": vision_book.authors_names, "year": vision_book.year}

def rename_file(state: dict, config: dict) -> dict:
    file_path = state.get("ReadPdfFile.file_path")
    title = state.get("ExtractMetadata.title")
    authors = state.get("ExtractMetadata.authors")
    year = state.get("ExtractMetadata.year")
    processed_folder_path = state.get("RenameLoop.processed_folder_path")
    new_file_path = os.path.join(processed_folder_path, f"[{year}] {authors[0]} - {title}.pdf")
    shutil.move(file_path, new_file_path)
    return {"new_file_path": new_file_path}

def check_all_files_processed(state: dict, config: dict) -> dict:
    remaining_file_paths_to_process = state.get("RenameLoop.remaining_file_paths_to_process")
    processed_files = state.get("RenameLoop.processed_files") or []
    processed_file = state.get("RenameFile.new_file_path")
    remaining_file_paths_to_process.pop(0)
    processed_files.append(processed_file)

    return {"is_done": len(remaining_file_paths_to_process) == 0, 
            "remaining_file_paths_to_process": remaining_file_paths_to_process, 
            "processed_files": processed_files}

def return_processed_files(state: dict, config: dict) -> dict:
    processed_files = state.get("RenameLoop.processed_files")
    return {"processed_files": processed_files}

