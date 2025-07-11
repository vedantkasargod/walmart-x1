import fitz  # PyMuPDF is imported as 'fitz'
import io
import logging

def extract_text_from_pdf(file_contents: bytes) -> str:
    """
    Extracts all text from a PDF file provided as in-memory bytes.
    This function handles both text-based and scanned (image-based) PDFs if Tesseract is installed,
    but primarily focuses on text extraction.
    
    Args:
        file_contents: The raw bytes of the PDF file.
        
    Returns:
        A string containing all the extracted text from the PDF.
    """
    try:
        # Open the PDF from the in-memory byte stream
        pdf_document = fitz.open(stream=file_contents, filetype="pdf")
        
        full_text = []
        logging.info(f"Processing PDF with {len(pdf_document)} pages.")
        
        # Iterate through each page of the PDF
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # The .get_text() method is highly efficient for text-based PDFs
            page_text = page.get_text("text")
            if page_text:
                full_text.append(page_text)
        
        logging.info("Successfully extracted text from PDF.")
        return "\n".join(full_text)
        
    except Exception as e:
        logging.error(f"Failed to process PDF file: {e}")
        # Return an empty string if any error occurs
        return ""