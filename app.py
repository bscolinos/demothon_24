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
from analytics import execute_query, get_unique_doctors, get_unique_conditions
import pymysql

# Page configuration
st.set_page_config(page_title="Patient 360 Portal", layout="wide")

# Connection details
config = {
    'user': 'admin',
    'password': 'SingleStore3!',
    'host': 'svc-59539893-4fcc-43ed-a05d-7582477f9579-dml.aws-virginia-5.svc.singlestore.com',
    'port': 3306,
    'database': 'demo_db'
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
section = st.sidebar.radio("Go to", ["Patient Records", "Analytics", "Research"])

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
def display_patient_records(): # TODO tie in how latest research relates to each patient, think about how 
    # we simulate a lot of questions, 5 most similar patients to this one
    st.title("Patient Records Management")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT patient_id FROM patients ORDER BY patient_id ASC LIMIT 10;")
                ids = [row[0] for row in cursor.fetchall()]

        selected_id = st.selectbox("Select an ID", ids)

        if selected_id:
            with get_db_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("""
                        SELECT * FROM appointments
                        WHERE patient_id = %s
                    """, (selected_id,))
                    appointments = cursor.fetchall()

            if appointments:
                st.write(appointments)
            else:
                st.write("No appointments found for this ID.")

    except mysql.connector.Error as err:
        st.error(f"Database error: {err}")


# Function to display analytics
def display_analytics():
    st.title("Analytics and Reporting")

    # Create a dropdown for selecting the analysis type
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Patient Demographics", "Medication Usage", "Appointment Trends", "Billing Claims", "Allergies Report"]
    )

    if analysis_type == "Patient Demographics":
        result = subprocess.run(["python", "analytics.py", "demographics"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        df = pd.DataFrame(data)
        st.write("Patient Demographics")
        st.dataframe(df)

    elif analysis_type == "Medication Usage":
        result = subprocess.run(["python", "analytics.py", "medication"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        df = pd.DataFrame(data)
        st.write("Medication Usage")
        st.dataframe(df)

    elif analysis_type == "Appointment Trends":
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        condition = st.selectbox("Select Condition", [""] + get_unique_conditions())
        doctor_id = st.selectbox("Select Doctor ID", [""] + get_unique_doctors())
        
        if st.button("Generate Appointment Trends"):
            result = subprocess.run([
                "python", "analytics.py", "appointments",
                str(start_date), str(end_date),
                condition if condition else "None",
                str(doctor_id) if doctor_id else "None"
            ], capture_output=True, text=True)
            data = json.loads(result.stdout)
            df = pd.DataFrame(data)
            st.write("Appointment Trends")
            st.dataframe(df)

    elif analysis_type == "Billing Claims":
        result = subprocess.run(["python", "analytics.py", "billing"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        df = pd.DataFrame(data)
        st.write("Billing Claims")
        st.dataframe(df)

    elif analysis_type == "Allergies Report":
        result = subprocess.run(["python", "analytics.py", "allergies"], capture_output=True, text=True)
        data = json.loads(result.stdout)
        df = pd.DataFrame(data)
        st.write("Allergies Report")
        st.dataframe(df)

    


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

def display_search(): # TODO add vectorize and upload to get results. Search with different code
    st.title("Hybrid Search on latest scientific research")
    pdf_folder = os.path.join(os.path.dirname(__file__), "arxiv_pdfs")
    
    arxiv_query = st.text_input("Enter search query (e.g., 'arthritis research')")
    max_results = st.slider("Maximum number of papers to download", 1, 50, 10)
    
    if st.button("Search and Download Papers"):
        with st.spinner("Searching and downloading papers..."):
            download_arxiv_papers(arxiv_query, max_results, pdf_folder)
        st.success(f"Downloaded {max_results} papers to {pdf_folder}")

    st.markdown("---")
    
    question = st.text_input("Enter a question about the downloaded papers")
    
    if st.button("Get Answer"):
        if question:
            result = subprocess.run(
                ["python", "doc_qa.py", question, pdf_folder],
                capture_output=True,
                text=True
            )
            
            st.write("Assistant's response:")
            st.write(result.stdout)
        else:
            st.warning("Please enter a question.")


# Navigation logic
if section == "Patient Records":
    display_patient_records()
elif section == "Analytics":
    display_analytics()
elif section == "Research":
    display_search()