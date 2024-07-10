import os
import sys
import arxiv
import requests
from typing import Optional, List
from phi.assistant import Assistant
from phi.knowledge import AssistantKnowledge
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb
from phi.document import Document
from phi.document.reader.pdf import PDFReader
import logging

# Set up logging
logging.getLogger("phi").setLevel(logging.CRITICAL)

# Environment variables and database connection details
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

USERNAME = "admin"
PASSWORD = "SingleStore3!"
HOST = "svc-59539893-4fcc-43ed-a05d-7582477f9579-dml.aws-virginia-5.svc.singlestore.com"
PORT = 3306
DATABASE = "demo_db"

db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"

# Set up SingleStore storage and knowledge base
assistant_storage = S2AssistantStorage(table_name="pdf_assistant", schema=DATABASE, db_url=db_url)
assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(collection="pdf_documents", schema=DATABASE, db_url=db_url),
    num_documents=5,
)

def sanitize_filename(filename):
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()

def download_arxiv_papers(query, max_results, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    results = client.results(search)

    for paper in results:
        print(f"Processing: {paper.title}")
        pdf_url = paper.pdf_url
        response = requests.get(pdf_url)
        if response.status_code == 200:
            filename = sanitize_filename(paper.title)[:50]
            filepath = os.path.join(output_dir, f"{filename}.pdf")
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {filepath}")
            
            # Upload to SingleStore
            try:
                pdf_documents: List[Document] = PDFReader().read(filepath)
                if pdf_documents:
                    assistant_knowledge.load_documents(pdf_documents, upsert=True)
                    print(f"Uploaded to SingleStore: {filename}")
            except Exception as e:
                print(f"Error uploading {filename}: {str(e)}")
        else:
            print(f"Failed to download PDF. Status code: {response.status_code}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python process_papers.py <query> <max_results> <output_dir>")
        sys.exit(1)
    
    query = sys.argv[1]
    max_results = int(sys.argv[2])
    output_dir = sys.argv[3]
    
    download_arxiv_papers(query, max_results, output_dir)