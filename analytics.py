import sys
import json
import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(**config)
    return conn

def execute_query(query):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
        connection.commit()
    finally:
        connection.close()
    return result

config = {
    'user': 'admin',
    'password': 'SingleStore3!',
    'host': 'svc-59539893-4fcc-43ed-a05d-7582477f9579-dml.aws-virginia-5.svc.singlestore.com',
    'port': 3306,
    'database': 'demo_db'
}

def get_unique_conditions():
    query = "SELECT DISTINCT `condition` FROM appointments WHERE `condition` IS NOT NULL"
    return [row[0] for row in execute_query(query)]

def get_unique_doctors():
    query = "SELECT DISTINCT doctor_id FROM appointments WHERE doctor_id IS NOT NULL"
    return [row[0] for row in execute_query(query)]

def get_patient_demographics():
    query = """
    SELECT
    DATE_FORMAT(FROM_DAYS(DATEDIFF(NOW(), STR_TO_DATE(date_of_birth, '%Y-%m-%d'))), '%Y')+0 AS age,
    blood_type,
    COUNT(*) AS count
    FROM patients
    GROUP BY age, blood_type
    ORDER BY age;
    """
    return execute_query(query)

def get_medication_usage():
    query = """
    SELECT
    medication_name,
    COUNT(*) AS usage_count,
    AVG(DATEDIFF(end_date, start_date)) AS avg_duration
    FROM medications
    GROUP BY medication_name
    ORDER BY usage_count DESC;
    """
    return execute_query(query)

def get_appointment_trends(start_date, end_date, condition, doctor_id):
    query = f"""
    SELECT
    DATE_FORMAT(appointment_date, '%Y-%m') AS month,
    COUNT(*) AS appointment_count,
    condition
    FROM appointments
    WHERE appointment_date BETWEEN '{start_date}' AND '{end_date}'
    """
    if condition != "None":
        query += f" AND condition = '{condition}'"
    if doctor_id != "None":
        query += f" AND doctor_id = {doctor_id}"
    query += """
    GROUP BY DATE_FORMAT(appointment_date, '%Y-%m'), condition
    ORDER BY DATE_FORMAT(appointment_date, '%Y-%m');
    """
    return execute_query(query)

def get_billing_claims():
    query = """
    SELECT
    status,
    COUNT(*) AS count,
    SUM(amount) AS total_amount,
    AVG(DATEDIFF(NOW(), STR_TO_DATE(payment_date, '%Y-%m-%d'))) AS avg_payment_delay
    FROM billings
    GROUP BY status
    ORDER BY count DESC;
    """
    return execute_query(query)

def get_allergies_report():
    query = """
    SELECT
    allergen,
    severity,
    COUNT(*) AS count
    FROM allergies
    WHERE allergen IS NOT NULL AND severity IS NOT NULL
    GROUP BY allergen, severity
    ORDER BY count DESC;
    """
    return execute_query(query)

if __name__ == "__main__":
    analysis_type = sys.argv[1]
    
    if analysis_type == "demographics":
        result = get_patient_demographics()
    elif analysis_type == "medication":
        result = get_medication_usage()
    elif analysis_type == "appointments":
        start_date, end_date, condition, doctor_id = sys.argv[2:]
        result = get_appointment_trends(start_date, end_date, condition, doctor_id)
    elif analysis_type == "billing":
        result = get_billing_claims()
    elif analysis_type == "allergies":
        result = get_allergies_report()
    else:
        result = []

    print(json.dumps(result))