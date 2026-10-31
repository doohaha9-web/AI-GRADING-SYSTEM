
import streamlit as st

st.set_page_config(
    page_title="AI Grading System",
    page_icon="🎓",
    layout="centered"
)

st.title("🎓 AI-Based Student Grading System")

st.write("Welcome! Evaluate student answers easily.")

st.subheader("Enter Question")
question = st.text_area("Question")

st.subheader("Enter Correct Answer")
correct_answer = st.text_area("Model Answer")

st.subheader("Enter Student Answer")
student_answer = st.text_area("Student Answer")

total_marks = st.number_input(
    "Total Marks",
    min_value=1,
    max_value=100,
    value=10
)

if st.button("Evaluate Answer"):
    if question and correct_answer and student_answer:
        st.success("Your answer has been submitted!")
        st.info("AI evaluation will be added in the next step.")
    else:
        st.warning("Please fill in all the fields.")

