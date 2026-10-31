
import streamlit as st
import sqlite3
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# DATABASE
conn = sqlite3.connect("grading.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    question TEXT,
    answer TEXT,
    marks INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student TEXT,
    question_id INTEGER,
    submission TEXT,
    marks REAL,
    feedback TEXT
)
""")
conn.commit()


# AI GRADING FUNCTION
def grade_answer(student_answer, correct_answer, max_marks):

    if not student_answer.strip():
        return 0, "No answer submitted."

    vectorizer = TfidfVectorizer()
    try:
        vectors = vectorizer.fit_transform(
            [student_answer, correct_answer]
        )
        similarity = cosine_similarity(
            vectors[0:1], vectors[1:2]
        )[0][0]
    except ValueError:
        similarity = 0

    score = round(similarity * max_marks, 2)

    if similarity >= 0.8:
        feedback = "Excellent answer!"
    elif similarity >= 0.5:
        feedback = "Good answer. Some details are missing."
    elif similarity >= 0.25:
        feedback = "Needs improvement. Review the topic."
    else:
        feedback = "Incorrect or incomplete answer."

    return score, feedback


# PAGE SETTINGS
st.set_page_config(
    page_title="AI Grading System",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI-Based Grading System")
st.write("A smart grading platform for students and teachers.")

role = st.sidebar.selectbox(
    "Select Portal",
    ["Student Portal", "Teacher Portal"]
)


# TEACHER PORTAL
if role == "Teacher Portal":

    st.header("👩‍🏫 Teacher Dashboard")

    menu = st.radio(
        "Choose an option",
        ["Add Question", "View Questions",
         "Student Results", "Teacher Performance"]
    )

    if menu == "Add Question":

        st.subheader("Create an examination question")

        subject = st.text_input("Subject")
        question = st.text_area("Enter Question")
        answer = st.text_area("Enter Model Answer")
        marks = st.number_input(
            "Maximum Marks", min_value=1, max_value=100
        )

        if st.button("Save Question"):
            if subject and question and answer:
                cursor.execute("""
                    INSERT INTO questions
                    (subject, question, answer, marks)
                    VALUES (?, ?, ?, ?)
                """, (subject, question, answer, marks))

                conn.commit()
                st.success("Question added successfully!")
            else:
                st.warning("Please fill in all fields.")

    elif menu == "View Questions":

        data = pd.read_sql_query(
            "SELECT * FROM questions", conn
        )
        st.dataframe(data, use_container_width=True)

    elif menu == "Student Results":

        data = pd.read_sql_query("""
            SELECT results.student,
                   questions.subject,
                   questions.question,
                   results.submission,
                   results.marks,
                   results.feedback
            FROM results
            JOIN questions
            ON results.question_id = questions.id
        """, conn)

        st.dataframe(data, use_container_width=True)

        if not data.empty:
            st.subheader("Class Performance")
            st.bar_chart(
                data.groupby("student")["marks"].mean()
            )

    elif menu == "Teacher Performance":

        st.info(
            "Teachers can review grading accuracy, "
            "student progress and feedback quality here."
        )


# STUDENT PORTAL
elif role == "Student Portal":

    st.header("🎓 Student Dashboard")

    student = st.text_input("Enter Your Name")

    menu = st.radio(
        "Student Menu",
        ["Take Examination", "My Results"]
    )

    if menu == "Take Examination":

        questions = pd.read_sql_query(
            "SELECT * FROM questions", conn
        )

        if questions.empty:
            st.warning("No questions are available yet.")

        else:
            for _, q in questions.iterrows():

                st.markdown("---")
                st.subheader(q["subject"])
                st.write(q["question"])
                st.caption(
                    f"Maximum Marks: {q['marks']}"
                )

                answer = st.text_area(
                    "Your Answer",
                    key=f"answer_{q['id']}"
                )

                if st.button(
                    "Submit Answer",
                    key=f"submit_{q['id']}"
                ):

                    if not student.strip():
                        st.warning("Enter your name first.")

                    else:
                        score, feedback = grade_answer(
                            answer,
                            q["answer"],
                            q["marks"]
                        )

                        cursor.execute("""
                            INSERT INTO results
                            (student, question_id,
                             submission, marks, feedback)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            student,
                            int(q["id"]),
                            answer,
                            score,
                            feedback
                        ))

                        conn.commit()

                        st.success("Answer submitted!")
                        st.metric(
                            "AI Suggested Marks",
                            f"{score}/{q['marks']}"
                        )
                        st.info(feedback)

    elif menu == "My Results":

        if student.strip():

            data = pd.read_sql_query(
                "SELECT * FROM results WHERE student = ?",
                conn,
                params=(student,)
            )

            if data.empty:
                st.info("No results found.")

            else:
                st.dataframe(
                    data,
                    use_container_width=True
                )

                st.metric(
                    "Total Marks",
                    round(data["marks"].sum(), 2)
                )

        else:
            st.warning("Please enter your name.")

