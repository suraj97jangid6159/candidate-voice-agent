import pdfplumber
import json
import re

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file using pdfplumber."""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

# Simple regex fallback in case LLM is offline/mock
def parse_resume_fallback(resume_text):
    """Simple regex/heuristics to parse contact information if LLM fails or is in mock mode."""
    lines = resume_text.split("\n")
    name = "Unknown Candidate"
    if lines:
        # Often the first line is the name
        name = lines[0].strip()
        
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", resume_text)
    phone = phone_match.group(0) if phone_match else "Not Specified"
    
    # Simple search for CTC or notice period
    current_ctc = "Not Specified"
    expected_ctc = "Not Specified"
    notice_period = "Not Specified"
    
    ctc_matches = re.findall(r"(?:ctc|salary|lpa)\s*[:=-]?\s*([\w\s\.\+\$]+)", resume_text, re.IGNORECASE)
    if ctc_matches:
        current_ctc = ctc_matches[0].strip()
        
    notice_matches = re.findall(r"(?:notice|notice period|joining time)\s*[:=-]?\s*([\w\s\.\+\$]+)", resume_text, re.IGNORECASE)
    if notice_matches:
        notice_period = notice_matches[0].strip()

    # Extract some common programming keywords as skills
    common_skills = ["python", "javascript", "react", "fastapi", "django", "node", "aws", "docker", "sql", "git", "sqlite", "java", "c++", "kubernetes"]
    skills = []
    for skill in common_skills:
        if re.search(rf"\b{skill}\b", resume_text, re.IGNORECASE):
            skills.append(skill.capitalize())
            
    return {
        "name": name,
        "phone": phone,
        "current_ctc": current_ctc,
        "expected_ctc": expected_ctc,
        "notice_period": notice_period,
        "skills": skills
    }

async def parse_resume_pdf(pdf_path, llm_adapter=None):
    """Main function to extract and parse PDF resume."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None
        
    structured_data = None
    if llm_adapter:
        try:
            # Construct a clean JSON-generating prompt
            prompt = f"Resume Content:\n{text}"
            system_prompt = (
                "You are an expert resume parsing assistant. Extract candidate information from the resume text.\n"
                "Return ONLY a valid JSON object matching this schema:\n"
                "{\n"
                "  \"name\": \"Full Name\",\n"
                "  \"phone\": \"Phone number\",\n"
                "  \"current_ctc\": \"Current CTC/Salary\",\n"
                "  \"expected_ctc\": \"Expected CTC/Salary\",\n"
                "  \"notice_period\": \"Notice Period\",\n"
                "  \"skills\": [\"Skill1\", \"Skill2\", ...]\n"
                "}\n"
                "Do not include any introductory or concluding text, markdown code blocks, or explanations. Only return valid JSON."
            )
            response_str = await llm_adapter.generate_response(system_prompt, prompt, [])
            # Clean response from markdown backticks if any
            clean_response = response_str.strip()
            if clean_response.startswith("```"):
                # strip code block formatting
                clean_response = re.sub(r"^```(?:json)?\n", "", clean_response)
                clean_response = re.sub(r"\n```$", "", clean_response)
            structured_data = json.loads(clean_response)
        except Exception as e:
            print(f"LLM parsing failed, using regex fallback: {e}")
            structured_data = parse_resume_fallback(text)
    else:
        structured_data = parse_resume_fallback(text)
        
    structured_data["resume_text"] = text
    return structured_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        text_extracted = extract_text_from_pdf(pdf_file)
        print("Extracted Text Preview:")
        print(text_extracted[:500])
        print("\nFallback Structured Parse:")
        print(parse_resume_fallback(text_extracted))
