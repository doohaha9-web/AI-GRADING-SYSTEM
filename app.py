
import json
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(
    page_title="AI Student Grading System",
    page_icon="📝",
    layout="wide"
)

MODEL = "gemini-3.8-flash"

# SESSION DATA
for key, value in {
    "exam": "My Examination",
    "questions": [],
    "results": [],
    "approved": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def ask_gemini(prompt, uploaded_file):
    client = get_client()

    try:
        part = types.Part.from_bytes(
            data=uploaded_file.getvalue(),
            mime_type=uploaded_file.type
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=[prompt, part],
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)

    finally:
        client.close()
def ask_gemini(prompt, uploaded_file):
    mime = uploaded_file.type

    part = types.Part.from_bytes(
        data=uploaded_file.getvalue(),
        mime_type=mime
    )

    response = get_client().models.generate_content(
        model=MODEL,
        contents=[prompt, part],
        config={
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)


# SIDEBAR
st.sidebar.title("📝 AI Grading System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Create Exam",
        "Upload Question Paper",
        "Review Answer Key",
        "Upload Student Papers",
        "Results",
        "Class Analysis"
    ]
)

st.title("AI Student Grading System")
st.caption("Gemini-powered answer sheet evaluation")


# DASHBOARD
if page == "Dashboard":

    total_marks = sum(
        float(q["marks"])
        for q in st.session_state.questions
    )

    a, b, c = st.columns(3)

    a.metric("Questions", len(st.session_state.questions))
    b.metric("Students Evaluated", len(st.session_state.results))
    c.metric("Maximum Marks", total_marks)

    st.subheader(st.session_state.exam)

    st.write(
        "Upload a question paper, generate an AI answer key, "
        "evaluate student papers and analyse class performance."
    )

    if st.session_state.approved:
        st.success("Answer key approved and ready for evaluation.")
    else:
        st.info("Upload a question paper to begin.")


# CREATE EXAM
elif page == "Create Exam":

    st.subheader("Examination Details")

    name = st.text_input(
        "Examination Name",
        st.session_state.exam
    )

    if st.button("Save Examination"):
        st.session_state.exam = name
        st.success("Examination saved!")


# UPLOAD QUESTION PAPER
elif page == "Upload Question Paper":

    st.subheader("Upload Question Paper")

    paper = st.file_uploader(
        "Choose question paper",
        type=["pdf", "png", "jpg", "jpeg"]
    )

    if paper:

        st.write("Uploaded:", paper.name)

        if st.button("Generate AI Answer Key"):

            prompt = """
            Read this examination question paper carefully.

            Extract every question, including subquestions.
            Identify the marks for each question.
            If marks are not visible, estimate them and clearly
            mention that they are estimated.

            Generate a suggested correct answer and marking points
            for each question.

            Return JSON with this structure:
            {
              "questions": [
                {
                  "question_number": "1",
                  "question": "Question text",
                  "marks": 2,
                  "suggested_answer": "Answer",
                  "marking_points": "Important points"
                }
              ]
            }

            Do not invent unreadable questions.
            Mark unclear information as UNCLEAR.
            """

            try:
                with st.spinner("Gemini is reading the question paper..."):

                    data = ask_gemini(prompt, paper)

                    questions = data.get("questions", [])

                    if not questions:
                        st.error("No questions were extracted.")
                    else:
                        st.session_state.questions = questions
                        st.session_state.approved = False
                        st.session_state.results = []

                        st.success(
                            f"Extracted {len(questions)} questions!"
                        )

                        st.info(
                            "Open Review Answer Key to check the answers."
                        )

            except Exception as e:
                st.error(f"Gemini error: {e}")


# REVIEW ANSWER KEY
elif page == "Review Answer Key":

    st.subheader("AI Generated Answer Key")

    if not st.session_state.questions:

        st.warning("Upload a question paper first.")

    else:

        df = pd.DataFrame(st.session_state.questions)

        edited = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("Approve Answer Key"):

            try:
                records = edited.to_dict(orient="records")

                for q in records:
                    q["marks"] = float(q["marks"])

                    if q["marks"] <= 0:
                        raise ValueError("Marks must be greater than zero.")

                    if not str(q["suggested_answer"]).strip():
                        raise ValueError(
                            f"Question {q['question_number']} has no answer."
                        )

                st.session_state.questions = records
                st.session_state.approved = True

                st.success("Answer key approved!")

            except Exception as e:
                st.error(str(e))


# UPLOAD STUDENT PAPERS
elif page == "Upload Student Papers":

    st.subheader("Evaluate Student Answer Sheets")

    if not st.session_state.approved:

        st.warning("Approve the answer key before uploading student papers.")

    else:

        files = st.file_uploader(
            "Upload student papers",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True
        )

        for file in files or []:

            with st.expander(file.name):

                student = st.text_input(
                    "Student name",
                    file.name.rsplit(".", 1)[0],
                    key="student_" + file.name
                )

                if st.button(
                    "Evaluate Paper",
                    key="evaluate_" + file.name
                ):

                    prompt = f"""
                    Evaluate this student's answer sheet.

                    APPROVED ANSWER KEY:
                    {json.dumps(st.session_state.questions)}

                    Instructions:
                    - Read the student's answers carefully.
                    - Match each answer to the correct question.
                    - Award marks only up to the maximum marks.
                    - Accept valid alternative wording.
                    - Do not assume missing answers are correct.
                    - Flag unclear handwriting or uncertain answers.
                    - Descriptive marking is an AI suggestion and
                      must be reviewed by the teacher.

                    Return JSON:
                    {{
                      "answers": [
                        {{
                          "question_number": "1",
                          "student_answer": "Extracted answer",
                          "marks_awarded": 2,
                          "feedback": "Reason for marks",
                          "review_required": true
                        }}
                      ]
                    }}
                    """

                    try:
                        with st.spinner("Gemini is evaluating the paper..."):

                            data = ask_gemini(prompt, file)

                            answer_rows = data.get("answers", [])

                            maximum = sum(
                                float(q["marks"])
                                for q in st.session_state.questions
                            )

                            question_marks = {
                                str(q["question_number"]): float(q["marks"])
                                for q in st.session_state.questions
                            }

                            cleaned = []
                            total = 0

                            for answer in answer_rows:

                                number = str(answer["question_number"])

                                if number not in question_marks:
                                    continue

                                awarded = max(
                                    0,
                                    min(
                                        float(answer["marks_awarded"]),
                                        question_marks[number]
                                    )
                                )

                                total += awarded

                                cleaned.append({
                                    "Question": number,
                                    "Student Answer": answer.get(
                                        "student_answer", ""
                                    ),
                                    "Marks": awarded,
                                    "Maximum Marks": question_marks[number],
                                    "Feedback": answer.get("feedback", ""),
                                    "Teacher Review": answer.get(
                                        "review_required", True
                                    )
                                })

                            st.session_state.results.append({
                                "Student": student,
                                "Marks": round(total, 2),
                                "Maximum Marks": maximum,
                                "Percentage": round(
                                    total / maximum * 100, 2
                                ) if maximum else 0,
                                "Details": cleaned
                            })

                            st.success(
                                f"Suggested score: {total}/{maximum}"
                            )

                            st.dataframe(
                                pd.DataFrame(cleaned),
                                use_container_width=True
                            )

                            st.warning(
                                "Review the extracted answers and marks "
                                "before finalising the result."
                            )

                    except Exception as e:
                        st.error(f"Evaluation error: {e}")


# RESULTS
elif page == "Results":

    st.subheader("Student Results")

    if not st.session_state.results:

        st.info("No students evaluated yet.")

    else:

        summary = [
            {k: v for k, v in r.items() if k != "Details"}
            for r in st.session_state.results
        ]

        df = pd.DataFrame(summary)

        st.dataframe(df, use_container_width=True)

        for result in st.session_state.results:

            with st.expander(result["Student"]):

                st.dataframe(
                    pd.DataFrame(result["Details"]),
                    use_container_width=True
                )

        st.download_button(
            "Download Results CSV",
            df.to_csv(index=False).encode("utf-8"),
            "class_results.csv",
            "text/csv"
        )


# CLASS ANALYSIS
elif page == "Class Analysis":

    st.subheader("Class Performance")

    if not st.session_state.results:

        st.info("Evaluate students to see class performance.")

    else:

        df = pd.DataFrame([
            {k: v for k, v in r.items() if k != "Details"}
            for r in st.session_state.results
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
st.sidebar.caption("AI Grading System | Teacher-reviewed prototype")
