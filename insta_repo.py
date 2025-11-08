import streamlit as st
import json
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ==============================================================================
# 🚀 INSTA REPO - STREAMLIT PYTHON APPLICATION
# Creator: Gandikota Saikowshik
#
# NOTE: This application requires the 'google-genai' library to be installed.
# The Gemini API Key is now hardcoded below for convenience.
# ==============================================================================

# --- 1. CONFIGURATION AND INITIAL STATE ---

# Set Streamlit page configuration
st.set_page_config(
    page_title="Insta Repo - AI Builder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'data' not in st.session_state:
    st.session_state.data = {
        'personal': {
            'name': 'Student Name',
            'email': 'email@example.com',
            'phone': '123-456-7890',
            'linkedin': 'https//linkedin/profile'
        },
        'summary': 'A highly motivated student seeking a challenging internship in AI and Cloud computing, leveraging strong foundational skills in Python and machine learning to drive impactful project execution.',
        'education': [
            {'id': 1, 'institution': 'University/College Name', 'degree': 'B.Tech/B.Sc in Computer Science', 'dates': '2021 - 2025'}
        ],
        'experience': [
            {'id': 1, 'title': 'AI and Cloud Intern', 'company': 'Edunet/IBM SkillsBuild', 'dates': 'June 2024 - Present', 'bullets': 'Successfully completed AI and Cloud internship project.\nGained hands-on experience with cloud services and generative AI tools.\nApplied Python and data analysis techniques to optimize project outcomes.'}
        ],
        'skills': ['Python', 'Cloud Computing (IBM/AWS/Azure)', 'Generative AI', 'Data Analysis', 'Web Development (React/JS)'],
        'portfolio': [
            {'id': 1, 'name': 'AI Resume Builder Project', 'link': 'https://github.com/my-project', 'description': 'Developed an AI tool to generate and optimize resumes and portfolios using Gemini API for content refinement.'}
        ],
        'cover_letter_inputs': {'company': '', 'title': ''},
        'cover_letter_draft': ''
    }
    st.session_state.ai_loading = None
    st.session_state.generated_html = ""
    st.session_state.theme = 'light' # <-- NEW: Default to light theme

# Fixed section order (as preferred in the React version)
SECTION_ORDER = ['summary', 'skills', 'portfolio', 'experience', 'education']


# --- 2. GEMINI API UTILITY FUNCTIONS ---
# Function to initialize the Gemini client (must be done only once)
@st.cache_resource
def get_gemini_client():
    try:
        # --- THIS IS THE CORRECT, SECURE WAY ---
        # It reads the key from the .streamlit/secrets.toml file
        GEMINI_KEY = st.secrets["GEMINI_KEY"]
        
        if not GEMINI_KEY:
            st.error("GEMINI_KEY not found. Please add it to your .streamlit/secrets.toml file.")
            return None

        return genai.Client(api_key=GEMINI_KEY)
    
    except Exception as e:
        st.error(f"Error initializing Gemini Client. Is your API key in .streamlit/secrets.toml correct? Details: {e}")
        return None

client = get_gemini_client()
MODEL = 'gemini-2.5-flash'
MAX_RETRIES = 5

def generate_content_with_ai(prompt, system_instruction):
    if not client:
        return 'Error: Gemini client not initialized. Check API Key configuration.'

    for attempt in range(MAX_RETRIES):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )
            response = client.models.generate_content(
                model=MODEL,
                contents=[prompt],
                config=config,
            )
            return response.text.strip()

        except APIError as e:
            if '429' in str(e) and attempt < MAX_RETRIES - 1:
                st.warning(f"Rate limit hit. Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt + 1)
            else:
                st.error(f"Gemini API Call Failed: {e}")
                st.session_state.ai_loading = None
                return 'Error: Could not connect to AI service or API key is invalid.'
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            st.session_state.ai_loading = None
            return 'Error: An unexpected error occurred during AI generation.'

# --- 3. AI HANDLERS ---

def handle_generate_summary():
    st.session_state.ai_loading = 'summary'
    data = st.session_state.data

    system_instruction = "You are a world-class resume writer. Generate a concise, 3-4 sentence professional summary based on the provided experience and education. Use strong action verbs and highlight key skills (AI, Cloud, Python, Web Dev). Do not include any introductory phrases, just the summary text."
    
    education_text = "; ".join([f"{e['degree']} from {e['institution']}" for e in data['education']])
    experience_text = "; ".join([f"{e['title']} at {e['company']}. Key points: {e['bullets']}" for e in data['experience']])
    
    user_prompt = f"Generate a summary for the following: \n\nEducation: {education_text}\n\nExperience: {experience_text}"
    
    result = generate_content_with_ai(user_prompt, system_instruction)
    st.session_state.data['summary'] = result
    st.session_state.ai_loading = None

def handle_suggest_skills():
    st.session_state.ai_loading = 'skills'
    data = st.session_state.data
    
    current_skills = ", ".join(data['skills'])
    system_instruction = "You are an AI career coach. Based on the user's current skills and their AI/Cloud internship focus, suggest 5-8 additional, relevant, high-demand skills that they should include. Provide the new skills as a comma-separated list ONLY, with no introductory text or numbering. Examples: Kubernetes, DevOps, PostgreSQL, Agile Methodology."
    user_prompt = f"Current Skills: {current_skills}\nFocus: AI and Cloud Intern"
    
    result = generate_content_with_ai(user_prompt, system_instruction)
    
    if not result.startswith('Error'):
        new_skills = [s.strip() for s in result.split(',') if s.strip()]
        # Merge unique skills
        merged_skills = list(set(data['skills']) | set(new_skills))
        st.session_state.data['skills'] = merged_skills
        
    st.session_state.ai_loading = None

def handle_refine_bullets(id, section='experience'):
    st.session_state.ai_loading = id
    
    if section == 'experience':
        item = next((exp for exp in st.session_state.data['experience'] if exp['id'] == id), None)
        title_field = 'title'
        bullet_field = 'bullets'
    elif section == 'portfolio':
        item = next((proj for proj in st.session_state.data['portfolio'] if proj['id'] == id), None)
        title_field = 'name'
        bullet_field = 'description'
        
    if not item or not item[bullet_field]:
        st.warning("No raw input to refine.")
        st.session_state.ai_loading = None
        return

    if section == 'experience':
        system_instruction = "You are an expert resume optimizer. Rewrite the following raw achievement points into 3-5 professional, high-impact bullet points. Each point must start with a strong action verb and include quantifiable results where possible. Return only the bullet points, each separated by a newline."
        user_prompt = f"Title: {item[title_field]}\nRaw Points:\n{item[bullet_field]}"
    else: # portfolio
        system_instruction = "You are a professional portfolio project describer. Write a concise, one-sentence description for a technical portfolio project. Focus on the tools used, the problem solved, and the impact. Return only the single sentence description."
        user_prompt = f"Project Name: {item[title_field]}\nExisting Description (if any): {item[bullet_field]}"


    result = generate_content_with_ai(user_prompt, system_instruction)
    
    if not result.startswith('Error'):
        if section == 'experience':
            st.session_state.data['experience'] = [
                {**exp, 'bullets': result} if exp['id'] == id else exp
                for exp in st.session_state.data['experience']
            ]
        else:
            st.session_state.data['portfolio'] = [
                {**proj, 'description': result} if proj['id'] == id else proj
                for proj in st.session_state.data['portfolio']
            ]
            
    st.session_state.ai_loading = None


def handle_generate_cover_letter():
    st.session_state.ai_loading = 'cover-letter'
    data = st.session_state.data
    inputs = data['cover_letter_inputs']
    
    if not inputs['company'] or not inputs['title']:
        st.session_state.data['cover_letter_draft'] = 'Error: Please enter both Target Company and Job Title.'
        st.session_state.ai_loading = None
        return

    system_instruction = "You are a highly skilled professional cover letter writer. Draft a formal, three-paragraph cover letter using the provided resume data, tailored for the specific job title and company. The tone must be professional and enthusiastic, highlighting how the candidate's experience (especially AI/Cloud) directly benefits the target company. Use proper salutations."
    
    experience_text = "\n- ".join([
        f"{e['title']} at {e['company']} ({e['dates']}): {e['bullets']}" for e in data['experience']
    ])
    
    user_prompt = f"""Draft a cover letter for the following job application:

Target Company: {inputs['company']}
Target Job Title: {inputs['title']}
Candidate Name: {data['personal']['name']}
Candidate Email: {data['personal']['email']}
Candidate LinkedIn: {data['personal']['linkedin']}
Candidate Professional Summary: {data['summary']}
Candidate Relevant Experience (Key Points): 
- {experience_text}
"""
    st.session_state.data['cover_letter_draft'] = 'Generating professional cover letter draft...'
    result = generate_content_with_ai(user_prompt, system_instruction)
    
    if not result.startswith('Error'):
        st.session_state.data['cover_letter_draft'] = result
        
    st.session_state.ai_loading = None

# --- 4. UI Rendering Functions ---

def render_personal_details():
    st.subheader("Personal Details")
    data = st.session_state.data['personal']
    
    data['name'] = st.text_input("Full Name", data['name'], key='name')
    data['email'] = st.text_input("Email", data['email'], key='email')
    data['phone'] = st.text_input("Phone", data['phone'], key='phone')
    data['linkedin'] = st.text_input("LinkedIn URL", data['linkedin'], key='linkedin')

def render_summary_generator():
    st.subheader("AI Summary Generator")
    
    st.session_state.data['summary'] = st.text_area(
        "Professional Summary (Editable)", 
        st.session_state.data['summary'], 
        height=150
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        # FIX: Ensure disabled state is strictly boolean (True/False)
        is_disabled = st.session_state.ai_loading is not None
        st.button(
            "Generate AI Summary 🚀", 
            on_click=handle_generate_summary,
            disabled=is_disabled,
            use_container_width=True
        )
    with col2:
        if st.session_state.ai_loading == 'summary':
            st.info("Generating Summary...")

def render_skills_form():
    st.subheader("Skills")
    
    skills_input = st.text_area(
        "Skills (comma-separated list)", 
        ", ".join(st.session_state.data['skills']), 
        height=100
    )
    
    # Update skills state when text area changes
    if skills_input != ", ".join(st.session_state.data['skills']):
        st.session_state.data['skills'] = [s.strip() for s in skills_input.split(',') if s.strip()]

    col1, col2 = st.columns(2)
    with col1:
        # FIX: Ensure disabled state is strictly boolean (True/False)
        is_disabled = st.session_state.ai_loading is not None
        if st.button("AI Suggest Skills 🧠", on_click=handle_suggest_skills, disabled=is_disabled, use_container_width=True):
            pass
    with col2:
        if st.session_state.ai_loading == 'skills':
            st.info("Suggesting Skills...")

def render_array_section(title, section_key, fields, handle_refine):
    st.subheader(title)
    
    for i, item in enumerate(st.session_state.data[section_key]):
        with st.container(border=True):
            st.markdown(f"**{item.get(fields[0][0]) or f'New {title.split()[0]}'}**")
            
            for field_name, label in fields:
                if label.endswith('(Raw Input)'):
                    # Text area for bullets/description
                    new_value = st.text_area(
                        label, 
                        item.get(field_name, ''), 
                        key=f'{section_key}_{item["id"]}_{field_name}',
                        height=100
                    )
                else:
                    # Regular text input
                    new_value = st.text_input(
                        label, 
                        item.get(field_name, ''), 
                        key=f'{section_key}_{item["id"]}_{field_name}'
                    )
                
                # Update state if value changed
                if new_value != item.get(field_name, ''):
                    st.session_state.data[section_key][i][field_name] = new_value

            # Action buttons
            col_refine, col_remove = st.columns([2, 1])
            if handle_refine and (section_key == 'experience' or section_key == 'portfolio'):
                with col_refine:
                    # FIX: Ensure disabled state is strictly boolean (True/False)
                    is_disabled = st.session_state.ai_loading is not None
                    if st.button(
                        f"AI Refine {'Bullets' if section_key == 'experience' else 'Description'} ✨",
                        key=f'ai_{section_key}_{item["id"]}',
                        on_click=handle_refine,
                        args=(item['id'], section_key),
                        disabled=is_disabled,
                        use_container_width=True
                    ):
                        st.session_state.ai_loading = item['id']
                
            with col_remove:
                if st.button(
                    "Remove 🗑️",
                    key=f'remove_{section_key}_{item["id"]}',
                    use_container_width=True
                ):
                    st.session_state.data[section_key].pop(i)
                    st.rerun()

    if st.button(f"➕ Add New {title.split()[0]}", key=f'add_{section_key}'):
        new_item = {'id': time.time()} # Use timestamp for unique ID
        for field_name, _ in fields:
            new_item[field_name] = ''
        st.session_state.data[section_key].append(new_item)
        st.rerun()

# --- 5. COMPILATION AND EXPORT FUNCTIONS ---

def compile_resume_text(data):
    """Compiles resume data into a clean, plain text string for download."""
    lines = []
    personal = data['personal']
    
    # 1. Header
    lines.append(personal['name'].upper())
    lines.append("=" * len(personal['name']))
    lines.append(f"Email: {personal['email']}")
    lines.append(f"Phone: {personal['phone']}")
    lines.append(f"LinkedIn: {personal['linkedin']}")
    lines.append("\n" * 2)

    # 2. Sections
    for key in SECTION_ORDER:
        if key == 'summary':
            lines.append("PROFESSIONAL SUMMARY")
            lines.append("-" * 20)
            lines.append(data['summary'])
            lines.append("\n")
        
        elif key == 'skills':
            lines.append("SKILLS")
            lines.append("-" * 6)
            lines.append(f"Technical Skills: {', '.join(data['skills'])}")
            lines.append("\n")

        elif key == 'portfolio':
            lines.append("PROJECTS")
            lines.append("-" * 8)
            for proj in data['portfolio']:
                lines.append(f"{proj['name']} ({proj['link']})")
                lines.append(f"  - {proj['description']}")
            lines.append("\n")

        elif key == 'experience':
            lines.append("EXPERIENCE")
            lines.append("-" * 10)
            for exp in data['experience']:
                lines.append(f"{exp['title']}, {exp['company']}")
                lines.append(f"  Dates: {exp['dates']}")
                for bullet in exp['bullets'].split('\n'):
                    if bullet.strip():
                        lines.append(f"  - {bullet.strip()}")
            lines.append("\n")

        elif key == 'education':
            lines.append("EDUCATION")
            lines.append("-" * 9)
            for edu in data['education']:
                lines.append(f"{edu['degree']}, {edu['institution']}")
                lines.append(f"  Dates: {edu['dates']}")
            lines.append("\n")
            
    return "\n".join(lines).strip()

def generate_portfolio_html():
    data = st.session_state.data
    
    # Simplified HTML template from the React version
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['personal']['name'] or 'Student'} Projects Portfolio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0d1117; /* Dark background */
        }}
        .section-title {{
            position: relative;
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }}
        .section-title::after {{
            content: '';
            position: absolute;
            left: 0;
            bottom: 0;
            height: 3px;
            width: 50px;
            background-color: #2563eb; /* Blue accent */
            border-radius: 9999px;
        }}
    </style>
</head>
<body class="text-gray-200">
    <div id="app" class="max-w-4xl mx-auto p-4 sm:p-8 space-y-12">
        <header id="header" class="text-center p-6 bg-[#161b22] rounded-xl shadow-2xl">
            <h1 class="text-5xl font-extrabold text-blue-400 mb-2">{data['personal']['name']}</h1>
            <p class="text-xl text-gray-400 mb-4">Aspiring AI & Cloud Developer</p>
            <div class="flex flex-wrap justify-center space-x-4 text-sm">
                <a href="mailto:{data['personal']['email']}" class="text-blue-400 hover:text-blue-300 transition duration-200">📧 {data['personal']['email']}</a>
                <a href="{data['personal']['linkedin']}" target="_blank" class="text-blue-400 hover:text-blue-300 transition duration-200">🔗 LinkedIn</a>
            </div>
        </header>

        <section id="about">
            <h2 class="text-3xl font-bold text-gray-100 section-title">About Me</h2>
            <p class="text-lg leading-relaxed text-gray-400">{data['summary']}</p>
        </section>

        <section id="skills">
            <h2 class="text-3xl font-bold text-gray-100 section-title">Core Skills</h2>
            <div class="flex flex-wrap gap-3">
                {''.join([f'<span class="px-4 py-2 bg-gray-700 text-blue-300 rounded-full text-sm font-medium shadow-md">{(skill)}</span>' for skill in data['skills']])}
            </div>
        </section>

        <section id="projects">
            <h2 class="text-3xl font-bold text-gray-100 section-title">Projects</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                {''.join([f'''
                    <div class="p-6 bg-[#161b22] border border-gray-700 rounded-xl">
                        <h3 class="text-xl font-semibold text-blue-400 mb-2">{proj['name']}</h3>
                        <p class="text-gray-400 text-sm mb-4">{proj['description']}</p>
                        <a href="{proj['link']}" target="_blank" class="inline-block text-sm font-medium text-blue-500 hover:text-blue-400 transition duration-200 flex items-center">
                            View Project
                            <span class="ml-1">→</span>
                        </a>
                    </div>
                ''' for proj in data['portfolio']])}
            </div>
        </section>
        
        <section id="education">
            <h2 class="text-3xl font-bold text-gray-100 section-title">Education</h2>
            <div class="space-y-4">
                {''.join([f'''
                    <div class="p-4 bg-[#161b22] border border-gray-700 rounded-lg">
                        <div class="flex justify-between items-center mb-1">
                            <h3 class="text-lg font-semibold text-gray-200">{edu['degree']}</h3>
                            <span class="text-sm text-gray-500">{edu['dates']}</span>
                        </div>
                        <p class="text-md text-gray-400">{edu['institution']}</p>
                    </div>
                ''' for edu in data['education']])}
            </div>
        </section>

        <footer class="text-center text-sm text-gray-500 pt-6 border-t border-gray-700">
            <p>&copy; 2025 {data['personal']['name']}. Built with Insta Repo.</p>
        </footer>
    </div>
</body>
</html>"""
    
    st.session_state.generated_html = html_content


def render_cover_letter_generator():
    st.subheader("✨ AI Cover Letter Draft")
    
    inputs = st.session_state.data['cover_letter_inputs']
    
    inputs['company'] = st.text_input("Target Company Name", inputs['company'], key='cl_company')
    inputs['title'] = st.text_input("Target Job Title", inputs['title'], key='cl_title')
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # FIX: Ensure disabled state is strictly boolean (True/False)
        is_disabled = st.session_state.ai_loading is not None
        st.button(
            "Generate Cover Letter ✍️", 
            on_click=handle_generate_cover_letter,
            disabled=is_disabled,
            use_container_width=True
        )
    with col2:
        if st.session_state.ai_loading == 'cover-letter':
            st.info("Drafting Letter...")

    if st.session_state.data['cover_letter_draft']:
        st.markdown("---")
        st.markdown("##### Cover Letter Draft:")
        st.text_area("Draft Output", st.session_state.data['cover_letter_draft'], height=350, disabled=True)
        
        # Download button for cover letter text
        st.download_button(
            label="Download Cover Letter (.txt)",
            data=st.session_state.data['cover_letter_draft'],
            file_name="cover_letter.txt",
            mime="text/plain",
            use_container_width=True
        )


def render_preview():
    # --- Dynamic Theme Colors ---
    theme = st.session_state.theme
    
    if theme == 'dark':
        BG_COLOR = '#1f2937' # Dark Gray background
        TEXT_COLOR = '#f3f4f6' # Light text
        ACCENT_COLOR = '#60a5fa' # Blue accent (headers/links)
        SUB_TEXT_COLOR = '#9ca3af' # Gray sub-text
        BORDER_COLOR = '#374151' # Darker border
    else: # light theme
        BG_COLOR = '#ffffff' # White background
        TEXT_COLOR = '#1f2937' # Dark text
        ACCENT_COLOR = '#1e40af' # Dark blue accent
        SUB_TEXT_COLOR = '#6b7280' # Gray sub-text
        BORDER_COLOR = '#e5e7eb' # Light border

    # Helper to convert internal data structure to markdown/HTML
    def format_resume_section(key, data):
        html_output = f'<div style="margin-bottom: 20px; background-color: {BG_COLOR}; color: {TEXT_COLOR}; padding: 10px; border: 1px solid {BORDER_COLOR};">'
        
        if key == 'summary':
            html_output += f'<h3 style="border-bottom: 2px solid {ACCENT_COLOR}; padding-bottom: 5px; margin-bottom: 10px; color: {ACCENT_COLOR}; font-size: 16px;">PROFESSIONAL SUMMARY</h3>'
            html_output += f'<p style="font-size: 14px; line-height: 1.5; color: {TEXT_COLOR};">{data["summary"]}</p>'
        
        elif key == 'skills':
            html_output += f'<h3 style="border-bottom: 2px solid {ACCENT_COLOR}; padding-bottom: 5px; margin-bottom: 10px; color: {ACCENT_COLOR}; font-size: 16px;">SKILLS</h3>'
            html_output += f'<p style="font-size: 14px; color: {TEXT_COLOR};"><b>Technical Skills:</b> {", ".join(data["skills"])}</p>'

        elif key == 'portfolio':
            html_output += f'<h3 style="border-bottom: 2px solid {ACCENT_COLOR}; padding-bottom: 5px; margin-bottom: 10px; color: {ACCENT_COLOR}; font-size: 16px;">PROJECTS</h3>'
            for proj in data['portfolio']:
                html_output += f'''
                    <div style="margin-bottom: 10px;">
                        <a href="{proj['link']}" target="_blank" style="font-weight: bold; color: {ACCENT_COLOR}; text-decoration: none;">{proj['name']}</a>
                        <p style="font-size: 12px; color: {SUB_TEXT_COLOR};">{proj['link']}</p>
                        <p style="font-size: 14px; color: {TEXT_COLOR};">{proj['description']}</p>
                    </div>
                    '''
                
        elif key == 'experience':
            html_output += f'<h3 style="border-bottom: 2px solid {ACCENT_COLOR}; padding-bottom: 5px; margin-bottom: 10px; color: {ACCENT_COLOR}; font-size: 16px;">EXPERIENCE</h3>'
            for exp in data['experience']:
                # FIX: Pre-calculate the HTML list items to avoid complex f-string expression error
                bullet_list_items = ''.join([
                    f'<li>{bullet.strip()}</li>' 
                    for bullet in exp['bullets'].split('\n')
                    if bullet.strip()
                ])
                
                html_output += f'''
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: {TEXT_COLOR};">{exp['title']}</span>
                        <span style="font-size: 12px; color: {SUB_TEXT_COLOR};">{exp['dates']}</span>
                    </div>
                    <p style="font-size: 14px; font-style: italic; color: {SUB_TEXT_COLOR};">{exp['company']}</p>
                    <ul style="margin-left: 20px; list-style-type: disc; font-size: 14px; color: {TEXT_COLOR};">
                        {bullet_list_items}
                    </ul>
                </div>
                '''

        elif key == 'education':
            html_output += f'<h3 style="border-bottom: 2px solid {ACCENT_COLOR}; padding-bottom: 5px; margin-bottom: 10px; color: {ACCENT_COLOR}; font-size: 16px;">EDUCATION</h3>'
            for edu in data['education']:
                html_output += f'''
                <div style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: {TEXT_COLOR};">{edu['degree']}</span>
                        <span style="font-size: 12px; color: {SUB_TEXT_COLOR};">{edu['dates']}</span>
                    </div>
                    <p style="font-size: 14px; font-style: italic; color: {SUB_TEXT_COLOR};">{edu['institution']}</p>
                </div>
                '''
        
        html_output += f'</div>'
        return html_output

    # --- HEADER ---
    header_html = f"""
    <div style="text-align: center; border-bottom: 4px solid {ACCENT_COLOR}; padding-bottom: 15px; margin-bottom: 20px; background-color: {BG_COLOR}; color: {TEXT_COLOR};">
        <h1 style="font-size: 32px; font-weight: 800; margin-bottom: 5px;">
            <a href="{st.session_state.data['personal']['linkedin']}" target="_blank" style="color: {ACCENT_COLOR}; text-decoration: none;">{st.session_state.data['personal']['name']}</a>
        </h1>
        <p style="font-size: 14px; color: {SUB_TEXT_COLOR};">
            {st.session_state.data['personal']['email']} | {st.session_state.data['personal']['phone']} | 
            <a href="{st.session_state.data['personal']['linkedin']}" target="_blank" style="color: {ACCENT_COLOR}; text-decoration: none;">LinkedIn</a>
        </p>
    </div>
    """
    
    st.markdown(header_html, unsafe_allow_html=True)
    
    # --- SECTIONS ---
    for section_key in SECTION_ORDER:
        st.markdown(format_resume_section(section_key, st.session_state.data), unsafe_allow_html=True)


# --- 6. MAIN APP LOGIC ---

def main():
    
    # Run the Portfolio HTML generation automatically when the app loads or data changes
    generate_portfolio_html()
    
    st.title("Insta Repo")
    st.markdown(
        '<p style="font-size: 18px; color: gray;">Instant AI Resume, Cover Letter and Portfolio Builder</p>', 
        unsafe_allow_html=True
    )
    st.markdown("---")

    # --- Theme Selector ---
    col_theme, col_empty = st.columns([1, 3])
    with col_theme:
        # Update theme state using a radio button
        theme_choice = st.radio(
            "Select Theme",
            ('Light', 'Dark'),
            index=0 if st.session_state.theme == 'light' else 1,
            horizontal=True
        )
        st.session_state.theme = theme_choice.lower()


    # --- Tabbed Layout ---
    input_tab, preview_tab = st.tabs(["Data Input & AI Tools", "Resume Preview & Portfolio"])

    with input_tab:
        
        # --- AI Summary and Personal Details in Columns ---
        col_personal, col_summary = st.columns(2)
        with col_personal:
            render_personal_details()
        with col_summary:
            render_summary_generator()

        st.markdown("---")
        
        # --- Array Sections ---
        render_skills_form()
        st.markdown("---")
        
        # Use columns for Education and Experience
        col_edu, col_exp = st.columns(2)
        with col_edu:
            render_array_section(
                "Education",
                'education',
                [('degree', 'Degree/Course'), ('institution', 'Institution'), ('dates', 'Dates')],
                None # No AI refine for education
            )
        with col_exp:
            render_array_section(
                "Experience",
                'experience',
                [('title', 'Title'), ('company', 'Company/Organization'), ('dates', 'Dates'), ('bullets', 'Achievements/Bullets (Raw Input)')],
                handle_refine_bullets
            )
        
        st.markdown("---")
        
        # --- Projects/Portfolio Section ---
        render_array_section(
            "Projects",
            'portfolio',
            [('name', 'Project Name'), ('link', 'Link (GitHub/Live Demo)'), ('description', 'Brief Description')],
            handle_refine_bullets
        )
        
        st.markdown("---")
        
        # --- Cover Letter Generator ---
        render_cover_letter_generator()
        
        st.markdown("---")
        
    with preview_tab:
        
        st.header("Resume Preview")
        st.warning(f"Theme: **{st.session_state.theme.capitalize()}**. Note: The Streamlit preview uses simple native styling. For final, polished output, use the Portfolio HTML download or **download the text file for easy copy/paste**.")
        
        # Ensure the preview container adapts to the theme background
        st.markdown(f'<div style="background-color: {"#1f2937" if st.session_state.theme == "dark" else "#ffffff"}; padding: 20px; border-radius: 8px;">', unsafe_allow_html=True)
        render_preview()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Compile resume text for download
        resume_text_data = compile_resume_text(st.session_state.data)
        
        st.markdown("---")
        st.subheader("Download Options")
        
        col_resume, col_portfolio = st.columns(2)
        
        with col_resume:
            st.download_button(
                label="Download Resume as Text (.txt) 📄",
                data=resume_text_data,
                file_name="resume_gandikota.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.caption("Best for copying to job forms or final formatting.")

        with col_portfolio:
            st.download_button(
                label="Download Portfolio Website (.html) 🌐",
                data=st.session_state.generated_html,
                file_name="portfolio_live.html",
                mime="text/html",
                use_container_width=True
            )
            st.caption("A responsive, dark-theme website based on your data.")


    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Insta Repo - Created by Gandikota Saikowshik")

if __name__ == '__main__':
    main()