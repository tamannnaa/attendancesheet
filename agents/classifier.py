from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os
import json
from dotenv import load_dotenv
load_dotenv()

def classify_document(text: str):
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0
    )

    prompt = ChatPromptTemplate.from_template("""
Classify this document:

Possible types:
- ATTENDANCE_GRID
- ATTENDANCE_DATE_BASED
- UNKNOWN

Return STRICT JSON:
{{ "type": "ATTENDANCE_GRID | ATTENDANCE_DATE_BASED | UNKNOWN" }}

TEXT:
{text}
""")

    resp = llm.invoke(prompt.format_messages(text=text))
    try:
        return json.loads(resp.content)["type"]
    except:
        return "UNKNOWN"
