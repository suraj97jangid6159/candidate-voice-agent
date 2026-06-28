import httpx
from bs4 import BeautifulSoup
import re
import json

async def scrape_job_description(url: str) -> dict:
    """Scrapes job details (title, company, description, HR contact) from a URL."""
    # Custom headers to bypass simple bot blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    result = {
        "company_name": "Unknown Company",
        "job_title": "Job Role",
        "jd_text": "",
        "hr_phone": "",
        "hr_email": "",
        "fit_score": 0.0
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch job URL {url}, status code: {response.status_code}")
                return result
            
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Extract plain text
            text = soup.get_text(separator="\n")
            # Clean up spacing
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)
            result["jd_text"] = clean_text
            
            # Simple heuristic parsing for Job Title & Company
            # Look at title tag
            page_title = soup.title.string if soup.title else ""
            if page_title:
                # E.g. "Software Engineer at Google - Jobs" or "Google hiring Software Engineer"
                page_title = page_title.strip()
                if " hiring " in page_title:
                    parts = page_title.split(" hiring ")
                    result["company_name"] = parts[0].strip()
                    result["job_title"] = parts[1].split("-")[0].split("|")[0].strip()
                elif " at " in page_title:
                    parts = page_title.split(" at ")
                    result["job_title"] = parts[0].strip()
                    result["company_name"] = parts[1].split("-")[0].split("|")[0].strip()
                else:
                    # Generic cleanup
                    result["job_title"] = page_title.split("-")[0].split("|")[0].strip()
            
            # Find contact details in text
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text)
            if email_match:
                result["hr_email"] = email_match.group(0)
                
            phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", clean_text)
            if phone_match:
                result["hr_phone"] = phone_match.group(0)
                
            # Truncate/clean JD text to avoid sending excessive markup
            # Let's keep it under 3000 chars if it's too big, focusing on the main text
            if len(result["jd_text"]) > 4000:
                result["jd_text"] = result["jd_text"][:4000] + "\n... (truncated)"
                
    except Exception as e:
        print(f"Scraper encountered error: {e}")
        
    return result

def analyze_resume_jd_fit(candidate_skills, jd_text):
    """Calculates a simple matching score between candidate skills and job description."""
    if not candidate_skills or not jd_text:
        return 0.0
        
    matched = 0
    skills_list = [s.strip().lower() for s in candidate_skills.split(",") if s.strip()]
    if not skills_list:
        return 0.0
        
    jd_lower = jd_text.lower()
    for skill in skills_list:
        if re.search(rf"\b{re.escape(skill)}\b", jd_lower):
            matched += 1
            
    score = round((matched / len(skills_list)) * 10, 1)
    return score

if __name__ == "__main__":
    import asyncio
    async def test():
        url = "https://news.ycombinator.com/jobs"
        res = await scrape_job_description(url)
        print("Scraped title:", res["job_title"])
        print("Scraped company:", res["company_name"])
        print("Preview text:", res["jd_text"][:200])
    asyncio.run(test())
