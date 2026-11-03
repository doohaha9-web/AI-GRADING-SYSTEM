
import re
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(
    page_title="AI Student Grading System",
    page_icon="📝",
    layout="wide"
)

# SESSION DATA
for key, value in {
    "exam": "My Examination",
    "questions": [],
    "results": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


# HELPER FUNCTIONS
def clean(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def extract_answers(text):
    answers = {}
    pattern = (
        r"(?im)^\s*(?:question\s*)?(?:q\s*)?"
        r"(\d+)\s*[\).:\-]\s*(.*?)"
        r"(?=^\s*(?:question\s*)?(?:q\s*)?\d+\s*[\).:\-]|\Z)"
    )

    for number, answer in re.findall(pattern, text, re.S):
        answers[int(number)] = answer.strip()

    return answers


def read_image(file):
    import pytesseract

    image = Image.open(file).convert("L")
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.5)

    return pytesseract.image_to_string(image)


def check_objective(student, correct):
    accepted = correct.split("|")
    return any(clean(student) == clean(a) for a in accepted)


def similarity(student, correct):
    if not student.strip() or not correct.strip():
        return 0

    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5)
        )

        matrix = vectorizer.fit_transform(
            [correct, student]
        )

        return cosine_similarity(
            matrix[0:1], matrix[1:2]
        )[0][0]

    except ValueError:
        return 0


def evaluate(answers):
    total = 0
    maximum = 0
    details = []

    for q in st.session_state.questions:
        number = q["number"]
        marks = q["marks"]
        maximum += marks

        student = answers.get(number, "")

        if q["type"] == "Objective":
            score = marks if check_objective(
                student, q["answer"]
            ) else 0
            review = "No"

        else:
            score = round(
                marks * similarity(student, q["answer"]), 2
            )
            review = "Yes"

        total += score

        details.append({
            "Question": number,
            "Student Answer": student,
            "Suggested Marks": round(score, 2),
            "Maximum Marks": marks,
            "Teacher Review": review
        })

    return round(total, 2), maximum, details


# SIDEBAR
st.sidebar.title("📝 AI Grading System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Create Exam",
        "Answer Key",
        "Upload Papers",
        "Results",
        "Class Analysis"
    ]
)

st.title("AI Student Grading System")
st.caption("Automated Answer Sheet Evaluation")


# DASHBOARD
if page == "Dashboard":

    total = sum(q["marks"] for q in st.session_state.questions)

    a, b, c = st.columns(3)

    a.metric("Questions", len(st.session_state.questions))
    b.metric("Students Evaluated", len(st.session_state.results))
    c.metric("Maximum Marks", total)

    st.subheader(st.session_state.exam)

    st.write(
        "Create examinations, upload answer sheets, "
        "evaluate marks and analyse class performance."
    )


# CREATE EXAM
elif page == "Create Exam":

    st.subheader("Create Examination")

    name = st.text_input(
        "Examination Name",
        st.session_state.exam
    )

    if st.button("Save Examination"):
        st.session_state.exam = name
        st.success("Examination saved!")


# ANSWER KEY
elif page == "Answer Key":

    st.subheader("Create Answer Key")

    with st.form("question_form"):

        number = st.number_input(
            "Question Number", min_value=1, step=1
        )

        question = st.text_input("Question")

        qtype = st.selectbox(
            "Question Type",
            ["Objective", "Descriptive"]
        )

        answer = st.text_area("Correct Answer")

        marks = st.number_input(
            "Marks", min_value=0.5, value=1.0
        )

        submit = st.form_submit_button("Add Question")

    if submit:

        if not answer.strip():
            st.error("Enter the correct answer.")

        elif any(
            q["number"] == int(number)
            for q in st.session_state.questions
        ):
            st.error("Question number already exists.")

        else:
            st.session_state.questions.append({
                "number": int(number),
                "question": question,
                "type": qtype,
                "answer": answer,
                "marks": float(marks)
            })

            st.success("Question added!")

    if st.session_state.questions:

        st.write("Saved Answer Key")

        st.dataframe(
            pd.DataFrame(st.session_state.questions),
            use_container_width=True
        )

        if st.button("Clear Answer Key"):
            st.session_state.questions = []
            st.rerun()


# UPLOAD PAPERS
elif page == "Upload Papers":

    st.subheader("Upload Student Answer Sheets")

    if not st.session_state.questions:

        st.warning("Create an answer key first.")

    else:

        files = st.file_uploader(
            "Upload answer sheet images",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )

        for file in files or []:

            st.write("File:", file.name)

            name = st.text_input(
                "Student Name",
                file.name.rsplit(".", 1)[0],
                key="name_" + file.name
            )

            try:
                extracted = read_image(file)

                text = st.text_area(
                    "Extracted Answers — correct OCR mistakes here",
                    extracted,
                    height=180,
                    key="text_" + file.name
                )

                if st.button(
                    "Evaluate " + file.name,
                    key="button_" + file.name
                ):

                    answers = extract_answers(text)

                    if not answers:
                        st.error(
                            "No numbered answers found. "
                            "Use labels like 1. Answer, 2. Answer."
                        )

                    else:
                        marks, maximum, details = evaluate(answers)

                        st.session_state.results.append({
                            "Student": name,
                            "Marks": marks,
                            "Maximum Marks": maximum,
                            "Percentage": round(
                                marks / maximum * 100, 2
                            ) if maximum else 0,
                            "Details": details
                        })

                        st.success(
                            f"Evaluation complete: {marks}/{maximum}"
                        )

            except Exception as e:
                st.error("OCR error: " + str(e))


# RESULTS
elif page == "Results":

    st.subheader("Student Results")

    if not st.session_state.results:

        st.info("No students evaluated yet.")

    else:

        data = [
            {k: v for k, v in result.items() if k != "Details"}
            for result in st.session_state.results
        ]

        df = pd.DataFrame(data)

        st.dataframe(df, use_container_width=True)

        for result in st.session_state.results:

            with st.expander(result["Student"]):

                st.dataframe(
                    pd.DataFrame(result["Details"]),
                    use_container_width=True
                )

                if any(
                    d["Teacher Review"] == "Yes"
                    for d in result["Details"]
                ):
                    st.warning(
                        "Descriptive marks are suggestions only. "
                        "Teacher review is required."
                    )

        st.download_button(
            "Download Results CSV",
            df.to_csv(index=False).encode("utf-8"),
            "student_results.csv",
            "text/csv"
        )

        if st.button("Clear Results"):
            st.session_state.results = []
            st.rerun()


# CLASS ANALYSIS
elif page == "Class Analysis":

    st.subheader("Class Performance Analysis")

    if not st.session_state.results:

        st.info("Evaluate students to view class analysis.")

    else:

        df = pd.DataFrame([
            {k: v for k, v in result.items() if k != "Details"}
            for result in st.session_state.results
        ])

        a, b, c = st.columns(3)

        a.metric("Students", len(df))

        b.metric(
            "Class Average",
            f"{df['Percentage'].mean():.1f}%"
        )

        c.metric(
            "Highest Score",
            f"{df['Percentage'].max():.1f}%"
        )

        st.bar_chart(
            df.set_index("Student")["Percentage"]
        )


st.sidebar.divider()
st.sidebar.caption(
    "AI Grading System | Teacher-reviewed prototype"
)
