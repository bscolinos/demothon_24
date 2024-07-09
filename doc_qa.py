import os
from typing import Optional, List
from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.knowledge import AssistantKnowledge
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb
from phi.document import Document
from phi.document.reader.pdf import PDFReader
from logging import getLogger
import argparse 

from logging import getLogger

logger = getLogger(__name__)

USERNAME = "admin"
PASSWORD = "SingleStore3!"
HOST = "svc-59539893-4fcc-43ed-a05d-7582477f9579-dml.aws-virginia-5.svc.singlestore.com"
PORT = 3306
DATABASE = "demo_db"

db_url = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8mb4"

assistant_storage = S2AssistantStorage(table_name="pdf_assistant", schema=DATABASE, db_url=db_url)

assistant_knowledge = AssistantKnowledge(
    vector_db=S2VectorDb(collection="pdf_documents", schema=DATABASE, db_url=db_url),
    num_documents=5,
)

def get_pdf_assistant(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    return Assistant(
        name="pdf_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OpenAIChat(model="gpt-4"),
        storage=assistant_storage,
        knowledge_base=assistant_knowledge,
        use_tools=True,
        show_tool_calls=True,
        add_chat_history_to_messages=True,
        num_history_messages=4,
        markdown=True,
        debug_mode=debug_mode,
        description="You are 'SingleStoreAI' designed to help users answer questions from a knowledge base of PDFs.",
    )

class PDFAssistant:
    def __init__(self, username: str):
        self.username = username
        self.pdf_assistant = get_pdf_assistant(user_id=username, debug_mode=True)
        self.run_id = self.pdf_assistant.create_run()

    def process_question(self, question: str) -> str:
        response = ""
        for delta in self.pdf_assistant.run(question):
            response += delta
        return response

    def upload_pdfs_from_folder(self, folder_path: str) -> None:
        reader = PDFReader()
        for filename in os.listdir(folder_path):
            if filename.endswith(".pdf"):
                file_path = os.path.join(folder_path, filename)
                pdf_documents: List[Document] = reader.read(file_path)
                if pdf_documents:
                    self.pdf_assistant.knowledge_base.load_documents(pdf_documents, upsert=True)
                    logger.info(f"Uploaded: {filename}")
                else:
                    logger.warning(f"Failed to read: {filename}")

def main(question: str, pdf_folder: str):
    assistant = PDFAssistant(username="arxiv_user")
    
    # Upload PDFs from the specified folder
    assistant.upload_pdfs_from_folder(pdf_folder)
    logger.info("Finished uploading PDFs")

    # Process the question
    response = assistant.process_question(question)
    print(response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a question using PDFs from a specified folder.")
    parser.add_argument("question", type=str, help="The question to ask the assistant")
    parser.add_argument("pdf_folder", type=str, help="Path to the folder containing arXiv PDFs")
    
    args = parser.parse_args()
    main(args.question, args.pdf_folder)