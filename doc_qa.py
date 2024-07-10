from typing import Optional
from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.knowledge import AssistantKnowledge
from phi.storage.assistant.singlestore import S2AssistantStorage
from phi.vectordb.singlestore import S2VectorDb
import logging

logging.getLogger("phi").setLevel(logging.CRITICAL)

# Database connection details (same as in preprocessing script)
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
        description="You are 'SingleStoreAI' designed to help users answer questions from a knowledge base of PDFs. The PDFs contain relevant research to latest diseases for doctors to review. DO NOT tell the user to consult a doctor.",
    )

class PDFAssistant:
    def __init__(self, username: str):
        self.username = username
        self.pdf_assistant = get_pdf_assistant(user_id=username)
        self.run_id = self.pdf_assistant.create_run()

    def process_question(self, question: str) -> str:
        response = ""
        for delta in self.pdf_assistant.run(question):
            response += delta
        return response

def main(question: str):
    assistant = PDFAssistant(username="arxiv_user")
    response = assistant.process_question(question)
    print(response)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process a question using the PDF assistant.")
    parser.add_argument("question", type=str, help="The question to ask the assistant")
    args = parser.parse_args()
    main(args.question)