import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import mysql.connector
import subprocess
import json
# from langchain_community.llms import OpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from openai import OpenAI
import os

# Page configuration
st.set_page_config(page_title="Patient 360 Portal", layout="wide")

# Connection details
config = {
    'user': 'admin',
    'password': 'SingleStore3!',
    'host': 'svc-216a63c3-a592-4e41-b082-b666a1e894ca-dml.aws-virginia-5.svc.singlestore.com',
    'port': 3306,
    'database': 'demothon'
}

def get_db_connection():
    conn = mysql.connector.connect(**config)
    return conn

def download_arxiv_papers(query, max_results=10, output_dir="arxiv_pdfs"):
    subprocess.run([
        "python", 
        "search_papers.py", 
        query, 
        "--max_results", str(max_results), 
        "--output_dir", output_dir
    ])

# Load data TODO fix this shit
# @st.cache
def load_data():
    return None
    # patients = pd.read_csv('patients.csv')
    # appointments = pd.read_csv('appointments.csv')
    # visits = pd.read_csv('visits.csv')
    # billing = pd.read_csv('billing.csv')
    # return patients, appointments, visits, billing

# patients, appointments, visits, billing = load_data()

# Sidebar for navigation
st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to", ["Patient Records", "Analytics", "Search"])

emb_model = OpenAIEmbeddings()

def get_embedding(text):
    embedding = emb_model.embed_documents(text)
    return json.dumps(embedding[0])

def hybrid_search(query, limit: int = 5): # TODO integrate BM25 or other 8.7 release
    '''Returns a list of the top matches to the query ordered by a combined score of text and vector similarity.'''
    query_embedding_vec = get_embedding(query)
    print("Query Embedded")
    search_term = query

    # run hybrid search TODO: fix query 
    statement = '''WITH fts AS (
                       SELECT id, paragraph, 
                           MATCH(paragraph) AGAINST(%s) AS ft_score
                       FROM vecs
                       WHERE MATCH(paragraph) AGAINST(%s)
                       ORDER BY ft_score DESC
                       LIMIT 200
                   ), vs AS (
                       SELECT id, paragraph, v <*> %s AS vec_score
                       FROM vecs
                       ORDER BY vec_score DESC
                       LIMIT 200
                   )
                   SELECT vs.id, vs.paragraph,
                       FORMAT(IFNULL(fts.ft_score, 0) * 0.3 + IFNULL(vs.vec_score, 0) * 0.7, 4) AS combined_score
                   FROM fts
                   FULL OUTER JOIN vs ON fts.id = vs.id
                   ORDER BY combined_score DESC
                   LIMIT %s;'''

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, (search_term, search_term, query_embedding_vec, limit))
            results_as_dict = cursor.fetchall()

    return results_as_dict

# Function to display patient records
def display_patient_records():
    st.title("Patient Records Management")
    st.subheader("Patient Profiles")
    # st.dataframe(patients)
    
    st.subheader("Appointments")
    # st.dataframe(appointments)
    
    st.subheader("Visits and Encounters")
    # st.dataframe(visits)
    
    st.subheader("Billing and Insurance")
    # st.dataframe(billing)

# Function to display analytics
def display_analytics():
    st.title("Analytics and Reporting")

# Function to perform hybrid search
# def display_search():
#     st.title("Hybrid Search on latest scientific research")
#     pdf_folder = os.path.join(os.path.dirname(__file__), "arxiv_pdfs")
    
#     question = st.text_input("Enter search query")
    
#     # TODO uncomment and make all this work together
#     # if question: 
#     #     # Full-text search
#     #     hybrid_search()
#     if st.button("Get Answer"):
#         if question:
#             # Run the PDF assistant script as a subprocess
#             result = subprocess.run(
#                 ["python", "doc_qa.py", question, pdf_folder],
#                 capture_output=True,
#                 text=True
#             )
            
#             # Display the response
#             st.write("Assistant's response:")
#             st.write(result.stdout)
#         else:
#             st.warning("Please enter a question.")

def display_search():
    st.title("Hybrid Search on latest scientific research")
    pdf_folder = os.path.join(os.path.dirname(__file__), "arxiv_pdfs")
    
    arxiv_query = st.text_input("Enter arXiv search query (e.g., 'quantum computing')")
    max_results = st.slider("Maximum number of papers to download", 1, 50, 10)
    
    if st.button("Search arXiv and Download Papers"):
        with st.spinner("Searching arXiv and downloading papers..."):
            download_arxiv_papers(arxiv_query, max_results, pdf_folder)
        st.success(f"Downloaded {max_results} papers to {pdf_folder}")

    st.markdown("---")
    
    question = st.text_input("Enter a question about the downloaded papers")
    
    if st.button("Get Answer"):
        if question:
            try:
                # Run the PDF assistant script as a subprocess
                result = subprocess.run(
                    ["python", "doc_qa.py", question, pdf_folder],
                    capture_output=True,
                    text=True,
                    check=True  # This will raise an exception if the subprocess fails
                )
                
                # Display the response
                st.write("Assistant's response:")
                st.write(result.stdout)
                
                # Log any errors
                if result.stderr:
                    st.error(f"Error occurred: {result.stderr}")
            except subprocess.CalledProcessError as e:
                st.error(f"An error occurred while running the assistant: {e}")
                st.error(f"Error output: {e.stderr}")
        else:
            st.warning("Please enter a question.")


# Navigation logic
if section == "Patient Records":
    display_patient_records()
elif section == "Analytics":
    display_analytics()
elif section == "Search":
    display_search()
