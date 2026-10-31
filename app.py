
import streamlit as st
import pandas as pd
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =====================================
# PAGE CONFIGURATION
# =====================================

st.set_page_config(
    page_title="AI Answer Grading System",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 AI Based Automatic Answer Grading System")

st.write(
    "An intelligent examination system that checks "
    "student answers and automatically awards marks."
)

st.divider()


# =====================================
# SESSION STATE
# =====================================

if "results" not in st.session_state:
    st.session_state.results = []


# =====================================
# TEXT PREPROCESSING
# =====================================

def preprocess(text):

    text = text.lower()

    text = re.sub(r'[^a-z0-9\s]', '', text)

    return text


# =====================================
# AI ANSWER EVALUATION
# =====================================

def evaluate_answer(
    correct_answer,
    student_answer,
    maximum_marks
):

    correct_answer = preprocess(correct_answer)
    student_answer = preprocess(student_answer)

    if not student_answer.strip():
        return 0, 0, "Incorrect"

    if not correct_answer.strip():
        return 0, 0, "Incorrect"

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    try:

        vectors = vectorizer.fit_transform([
            correct_answer,
            student_answer
        ])

        similarity = cosine_similarity(
            vectors[0:1],
            vectors[1:2]
        )[0][0]

    except ValueError:

        similarity = 0

    percentage = similarity * 100

    marks = round(
        similarity * maximum_marks,
        2
    )

    # Grading system

    if percentage >= 65:

        status = "Correct"

    elif percentage >= 25:

        status = "Partially Correct"

    else:

        status = "Incorrect"

    return marks, percentage, status


# =====================================
# GRADE CALCULATION
# =====================================

def calculate_grade(percentage):

    if percentage >= 90:
        return "A+"

    elif percentage >= 80:
        return "A"

    elif percentage >= 70:
        return "B"

    elif percentage >= 60:
        return "C"

    elif percentage >= 40:
        return "D"

    else:
        return "F"


# =====================================
# STUDENT INFORMATION
# =====================================

st.header("👨‍🎓 Student Information")

col1, col2 = st.columns(2)

with col1:

    student_name = st.text_input(
        "Student Name"
    )

with col2:

    roll_number = st.text_input(
        "Roll Number"
    )


st.divider()


# =====================================
# QUESTION SECTION
# =====================================

st.header("📝 Examination Question")

subject = st.selectbox(
    "Select Subject",
    [
        "Computer Science",
        "Physics",
        "Chemistry",
        "Mathematics",
        "Biology",
        "English"
    ]
)

question = st.text_area(
    "Enter Question",
    placeholder="Enter the examination question here..."
)

correct_answer = st.text_area(
    "Enter the Correct Answer",
    placeholder="Enter the teacher's model answer..."
)

student_answer = st.text_area(
    "Enter Student Answer",
    placeholder="Enter the student's answer here..."
)

maximum_marks = st.number_input(
    "Maximum Marks",
    min_value=1,
    max_value=100,
    value=5
)


# =====================================
# EVALUATION
# =====================================

if st.button(
    "🚀 Evaluate Answer",
    use_container_width=True
):

    if not student_name.strip():

        st.error("Please enter student name.")

    elif not roll_number.strip():

        st.error("Please enter roll number.")

    elif not question.strip():

        st.error("Please enter a question.")

    elif not correct_answer.strip():

        st.error("Please enter correct answer.")

    elif not student_answer.strip():

        st.error("Please enter student answer.")

    else:

        marks, similarity, status = evaluate_answer(
            correct_answer,
            student_answer,
            maximum_marks
        )

        grade = calculate_grade(similarity)

        st.session_state.results.append({

            "Name": student_name,
            "Roll Number": roll_number,
            "Subject": subject,
            "Question": question,
            "Marks": marks,
            "Maximum Marks": maximum_marks,
            "Similarity": round(similarity, 2),
            "Status": status,
            "Grade": grade

        })

        st.divider()

        st.header("📊 Evaluation Result")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Marks Awarded",
            str(marks) + " / " + str(maximum_marks)
        )

        c2.metric(
            "Similarity Score",
            str(round(similarity, 2)) + "%"
        )

        c3.metric(
            "Grade",
            grade
        )

        st.progress(
            min(1.0, max(0.0, similarity / 100))
        )

        if status == "Correct":

            st.success("✅ Answer is Correct")

        elif status == "Partially Correct":

            st.warning("⚠️ Answer is Partially Correct")

        else:

            st.error("❌ Answer is Incorrect")

        st.info(
            "The similarity score measures text similarity. "
            "It does not guarantee factual correctness."
        )


# =====================================
# STUDENT PERFORMANCE TABLE
# =====================================

st.divider()

st.header("📚 Student Performance Dashboard")

if st.session_state.results:

    df = pd.DataFrame(
        st.session_state.results
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    total_marks = df["Marks"].sum()

    maximum_total = df["Maximum Marks"].sum()

    st.metric(
        "Total Marks",
        str(round(total_marks, 2))
        + " / "
        + str(maximum_total)
    )

    if maximum_total > 0:

        overall_percentage = (
            total_marks / maximum_total
        ) * 100

        st.metric(
            "Overall Percentage",
            str(round(overall_percentage, 2)) + "%"
        )

    # DOWNLOAD REPORT

    csv = df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📥 Download Student Report",
        data=csv,
        file_name="student_results.csv",
        mime="text/csv"
    )

else:

    st.info(
        "Student results will appear here after evaluation."
    )


# =====================================
# PROJECT INFORMATION
# =====================================

st.divider()

st.subheader("About This Project")

st.write("""
This AI-based automatic answer grading system
uses Natural Language Processing techniques.

Scikit-learn is used for TF-IDF vectorization
and cosine similarity to compare answers.

Pandas is used to organize student examination
results and generate performance reports.

Streamlit provides the interactive web interface.
""")

st.caption(
    "Class 12 Artificial Intelligence Project"
)

