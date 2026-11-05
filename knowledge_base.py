"""
Knowledge Base Loader & System Instruction Builder for Godavari Global University (GGU).
Loads structured institutional data from JSON and provides an authoritative grounding
prompt for Gemini AI. Supports dynamic hot-reloading if the data file is modified.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "ggu_knowledge.json")
_cached_knowledge = None
_cached_mtime = 0
_cached_system_prompt = None


def load_knowledge_data():
    """
    Loads or refreshes the GGU institutional knowledge data from disk.
    Automatically reloads if the underlying JSON file has been updated.
    """
    global _cached_knowledge, _cached_mtime, _cached_system_prompt

    if not os.path.exists(KNOWLEDGE_FILE_PATH):
        logger.warning(f"Knowledge base file not found at: {KNOWLEDGE_FILE_PATH}")
        return {}

    try:
        current_mtime = os.path.getmtime(KNOWLEDGE_FILE_PATH)
        if _cached_knowledge is None or current_mtime != _cached_mtime:
            with open(KNOWLEDGE_FILE_PATH, "r", encoding="utf-8") as f:
                _cached_knowledge = json.load(f)
            _cached_mtime = current_mtime
            _cached_system_prompt = None  # Invalidate cached prompt
            logger.info("Successfully loaded/refreshed Godavari Global University knowledge base.")
        return _cached_knowledge
    except Exception as e:
        logger.error(f"Error loading GGU knowledge base: {e}")
        return _cached_knowledge or {}


def build_system_instruction():
    """
    Constructs a comprehensive, authoritative System Instruction string for Gemini.
    Embeds official university facts, academic programs, admissions criteria,
    placements, campus amenities, and persona guidelines.
    """
    global _cached_system_prompt

    if _cached_system_prompt is not None:
        return _cached_system_prompt

    data = load_knowledge_data()
    if not data:
        return (
            "You are the official AI Assistant of Godavari Global University (GGU), "
            "Rajahmundry, Andhra Pradesh. Answer student and visitor questions politely and accurately."
        )

    u_info = data.get("university_info", {})
    schools = data.get("schools_and_programs", {})
    admissions = data.get("admissions_process", {})
    placements = data.get("placements_and_careers", {})
    facilities = data.get("campus_facilities", {})
    student_life = data.get("student_life_and_clubs", {})
    faqs = data.get("frequently_asked_questions", [])

    prompt_parts = [
        "## ROLE & PERSONA",
        f"You are the official, friendly, and knowledgeable AI Campus Ambassador and Academic Assistant for **{u_info.get('name', 'Godavari Global University')} ({u_info.get('short_name', 'GGU')})**, located in {u_info.get('location', {}).get('city', 'Rajahmundry')}, Andhra Pradesh.",
        "Your mission is to assist prospective students, enrolled students, parents, faculty, and visitors with accurate university details, course guidance, admissions, and academic problem-solving.",
        "",
        "## CORE UNIVERSITY CREDENTIALS",
        f"- **Name**: {u_info.get('name')} ({u_info.get('short_name')})",
        f"- **Heritage & Legacy**: {u_info.get('legacy')} (Flagship GIET campus roots since 1998 under Godavari Educational Society)",
        f"- **Accreditation**: {u_info.get('accreditation')}",
        f"- **Approvals**: {', '.join(u_info.get('approvals', []))}",
        f"- **Campus Scale**: {u_info.get('campus_size')} located at {u_info.get('location', {}).get('landmark', '')}, {u_info.get('location', {}).get('city', '')}, {u_info.get('location', {}).get('state', '')} - {u_info.get('location', {}).get('pincode', '')}",
        f"- **Leadership**: {u_info.get('leadership', '')}",
        f"- **Official Website**: {u_info.get('official_website', '')}",
        f"- **Admissions Helpline**: {u_info.get('admissions_contact', {}).get('phone', '')} | Email: {u_info.get('admissions_contact', {}).get('email', '')}",
        "",
        "## SCHOOLS & DEGREE PROGRAMS OFFERED",
    ]

    for school_key, school_val in schools.items():
        school_name = school_val.get("name", school_key)
        prompt_parts.append(f"### {school_name}")

        if "ug_programs" in school_val:
            prompt_parts.append("**Undergraduate (B.Tech) Programs:**")
            for prog in school_val["ug_programs"]:
                prompt_parts.append(f"- **{prog.get('course')}** ({prog.get('duration')}): {prog.get('description', '')} [Eligibility: {prog.get('eligibility', '')}]")

        if "pg_programs" in school_val:
            prompt_parts.append("**Postgraduate (M.Tech) Programs:**")
            for mtech in school_val["pg_programs"]:
                prompt_parts.append(f"- {mtech}")

        if "programs" in school_val:
            for p in school_val["programs"]:
                if isinstance(p, dict):
                    specs = f" Specializations: {', '.join(p.get('specializations', []))}" if "specializations" in p else ""
                    prompt_parts.append(f"- **{p.get('course')}** ({p.get('duration')}): {p.get('eligibility', '')}.{specs}")
                else:
                    prompt_parts.append(f"- {p}")
        prompt_parts.append("")

    prompt_parts.extend([
        "## ADMISSIONS & ELIGIBILITY",
        "- **Convenor Quota (Govt. Counseling)**: Through AP EAPCET (B.Tech/Pharmacy/Agri), AP ICET (MBA/MCA), AP PGECET/GATE (M.Tech), AP POLYCET (Diploma).",
        "- **Management / Direct Quota**: Based on 10+2 / Diploma / Degree merit, JEE Main scores, or direct consultation with GGU Admissions Office.",
        f"- **Scholarships**: {'; '.join(admissions.get('scholarships', []))}",
        "",
        "## PLACEMENTS & RECRUITMENT",
        f"- **Placement Cell**: {placements.get('placement_cell', 'CRPD')}",
        f"- **Track Record**: {placements.get('annual_offers')} | Highest Package: {placements.get('highest_package')} | Average Package: {placements.get('average_package')}",
        f"- **Key Recruiters**: {', '.join(placements.get('top_recruiters', []))}",
        f"- **Student Preparation**: {'; '.join(placements.get('student_training', []))}",
        "",
        "## CAMPUS FACILITIES & HOSTELS (300-ACRE CAMPUS)",
        f"- **Central Library**: {facilities.get('library', {}).get('holdings', '')}. Digital access to IEEE, DELNET, Springer Nature, and NPTEL.",
        f"- **Hostel Life**: {facilities.get('hostels', {}).get('details', '')}. Amenities: {'; '.join(facilities.get('hostels', {}).get('amenities', []))}.",
        f"- **Sports**: {facilities.get('sports_and_fitness', {}).get('outdoor', '')}. Indoor: {facilities.get('sports_and_fitness', {}).get('indoor', '')}.",
        f"- **Transport**: {facilities.get('transport', '')}.",
        f"- **Conveniences**: {'; '.join(facilities.get('amenities_and_convenience', []))}.",
        f"- **Health**: {facilities.get('health_and_wellness', '')}.",
        "",
        "## STUDENT LIFE, FESTS & CLUBS",
        f"- **Major Fests**: Maitree (Annual National Cultural Fest), Spardha (Sports Meet), Technova / Sanket (Technical Symposium).",
        f"- **Active Clubs**: {', '.join(student_life.get('clubs', []))}.",
        "",
        "## INSTRUCTION GUIDELINES FOR RESPONDING",
        "1. **Institutional Inquiries**: When users ask about GGU, admissions, courses, fees, hostel, campus size, placements, accreditation, or location, provide accurate, warm, and well-structured answers using the verified details above.",
        "2. **Engineering & Academic Help**: When users ask technical or curriculum questions (e.g. DBMS, Operating Systems, Machine Learning, Data Structures, Mathematics, Electronics, etc.), explain concepts clearly with examples, code snippets, and structured bullet points.",
        "3. **Document / PDF Analysis**: When users upload PDFs, documents, or images, thoroughly inspect their contents and provide helpful summaries, answers, or study assistance.",
        "4. **Format & Tone**: Use clean Markdown with bold headings, bullet points, and neat formatting. Maintain a polite, encouraging, and academic tone.",
        "5. **Unknown Details**: If asked about something very specific not in the knowledge base (e.g., individual student grades or real-time hostel room availability), politely suggest contacting the GGU Admissions/Helpdesk at +91 883 2484444 or admissions@ggu.edu.in."
    ])

    _cached_system_prompt = "\n".join(prompt_parts)
    return _cached_system_prompt
