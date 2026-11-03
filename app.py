
import streamlit as st
import pandas as pd
import pytesseract
import re
import io

from PIL import Image, ImageOps, ImageEnhance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="AI Grading System", page_icon="📝", layout="wide")

st.title("AI Student Grading System")
st.caption("Automated answer sheet evaluation")

if "key" not in st.session_state:
    st.session_state.key = None
if "results" not in st.session_state:
    st.session_state.results = []
if "details" not in st.session_state:
    st.session_state.details = []


# TEXT PROCESSING
def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", str(text).lower())).strip()


# IMAGE OCR
def read_image(file):
    img = Image.open(io.BytesIO(file.getvalue()))
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageEnhance.Contrast(img).enhance(2)
    return pytesseract.image_to_string(img, config="--psm 6")


# EXTRACT QUESTION ANSWERS
def extract_answers(text):
    pattern = r"(?im)^\s*(?:question\s*|q\s*)?(\d+)\s*[\).:\-]\s*"
    matches = list(re.finditer(pattern, text))
    answers = {}

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        answers[int(match.group(1))] = text[start:end].strip()

    return answers


# OBJECTIVE EVALUATION
def objective(student, expected):
    accepted = [clean(x) for x in str(expected).split("|")]
    return 1.0 if clean(student) in accepted and clean(student) else 0.0


# DESCRIPTIVE EVALUATION
def descriptive(student, expected):
    student = clean(student)
    answers = [clean(x) for x in str(expected).split("|") if clean(x)]

    if not student or not answers:
        return 0.0

    scores = []

    for answer in answers:
        try:
            vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))
            vectors = vectorizer.fit_transform([student, answer])
            scores.append(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
        except ValueError:
            scores.append(0.0)

    return max(scores, default=0.0)


# NAVIGATION
page = st.sidebar.radio(
    "Teacher Dashboard",
    ["Dashboard", "Answer Key", "Upload Papers", "Results", "Analysis"]
)


# DASHBOARD
if page == "Dashboard":
    st.header("Examination Dashboard")
    c1, c2 = st.columns(2)
    c1.metric("Questions", len(st.session_state.key) if st.session_state.key is not None else 0)
    c2.metric("Students Evaluated", len(st.session_state.results))
    st.write("Create exams, upload answer sheets, evaluate marks and analyse class performance.")


# ANSWER KEY
elif page == "Answer Key":
    st.header("Create Answer Key")
    st.text_input("Examination Name", key="exam")

    if st.session_state.key is None:
        initial = pd.DataFrame({
            "Question No": [1, 2, 3],
            "Question": ["Question 1", "Question 2", "Question 3"],
            "Type": ["Objective", "Descriptive", "Objective"],
            "Correct Answer": ["25", "Plants make food through photosynthesis", "100"],
            "Marks": [2, 5, 3]
        })
    else:
        initial = st.session_state.key

    data = st.data_editor(
        initial, num_rows="dynamic", use_container_width=True,
        column_config={
            "Type": st.column_config.SelectboxColumn(options=["Objective", "Descriptive"]),
            "Marks": st.column_config.NumberColumn(min_value=0)
        },
        key="editor"
    )

    if st.button("Save Answer Key"):
        valid = data.dropna().copy()
        valid["Question No"] = pd.to_numeric(valid["Question No"], errors="coerce")
        valid["Marks"] = pd.to_numeric(valid["Marks"], errors="coerce")

        if valid.empty or valid[["Question No", "Question", "Type", "Correct Answer", "Marks"]].isna().any().any():
            st.error("Complete all question fields.")
        elif valid["Question No"].duplicated().any() or (valid["Marks"] < 0).any():
            st.error("Question numbers must be unique and marks non-negative.")
        else:
            st.session_state.key = valid
            st.session_state.results = []
            st.session_state.details = []
            st.success("Answer key saved!")


# UPLOAD AND EVALUATE
elif page == "Upload Papers":
    st.header("Upload Student Answer Sheets")

    if st.session_state.key is None:
        st.warning("Create an answer key first.")
    else:
        files = st.file_uploader("Upload answer sheet images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

        if files and st.button("Start Evaluation", type="primary"):
            progress = st.progress(0)

            for i, file in enumerate(files):
                name = file.name.rsplit(".", 1)[0]

                try:
                    text = read_image(file)
                    answers = extract_answers(text)
                    total = 0
                    maximum = 0
                    review = 0
                    detail = []
                    result = {"Student": name}

                    for _, q in st.session_state.key.iterrows():
                        number = int(q["Question No"])
                        student = answers.get(number, "")
                        expected = str(q["Correct Answer"])
                        marks = float(q["Marks"])
                        maximum += marks

                        score = objective(student, expected) if q["Type"] == "Objective" else descriptive(student, expected)
                        awarded = round(marks * score, 2)
                        status = "Correct" if score == 1 else "Incorrect"

                        if not student:
                            awarded, status = 0, "Answer Not Detected"
                            review += 1
                        elif q["Type"] == "Descriptive":
                            status = "Teacher Review Required"
                            review += 1

                        total += awarded
                        result[f"Q{number}"] = awarded

                        detail.append({
                            "Student": name,
                            "Question": number,
                            "Student Answer": student,
                            "Correct Answer": expected,
                            "Similarity (%)": round(score * 100, 2),
                            "Marks": awarded,
                            "Status": status
                        })

                    result.update({
                        "Total": round(total, 2),
                        "Maximum": maximum,
                        "Percentage": round(total / maximum * 100, 2) if maximum else 0,
                        "Review Required": review
                    })

                    st.session_state.results.append(result)
                    st.session_state.details.extend(detail)

                    with st.expander(f"OCR: {name}"):
                        st.text(text)

                except Exception as e:
                    st.error(f"{name}: {e}")

                progress.progress((i + 1) / len(files))

            st.success("Evaluation completed!")


# RESULTS
elif page == "Results":
    st.header("Student Results")

    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results)
        st.dataframe(df, use_container_width=True)

        a, b, c = st.columns(3)
        a.metric("Students", len(df))
        b.metric("Class Average", f"{df['Percentage'].mean():.2f}%")
        c.metric("Highest Marks", df["Total"].max())

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "class_results.csv",
            "text/csv"
        )

        st.subheader("Detailed Evaluation")
        st.dataframe(pd.DataFrame(st.session_state.details), use_container_width=True)
    else:
        st.info("No results available yet.")


# PERFORMANCE ANALYSIS
elif page == "Analysis":
    st.header("Class Performance Analysis")

    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results)
        st.bar_chart(df.set_index("Student")["Percentage"])

        if st.session_state.details:
            details = pd.DataFrame(st.session_state.details)
            analysis = details.groupby("Question").agg(
                Average_Marks=("Marks", "mean"),
                Students=("Student", "count")
            ).reset_index()

            st.subheader("Question-wise Performance")
            st.dataframe(analysis, use_container_width=True)
            st.bar_chart(analysis.set_index("Question")["Average_Marks"])
    else:
        st.info("Evaluate students to view analysis.")
