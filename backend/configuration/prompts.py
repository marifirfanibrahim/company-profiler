"""
prompt configuration
build system prompts
define templates
"""

# core system prompt for profile focused analysis
SYSTEM_PROMPT = (
    "You are a research analyst focusing on Malaysian companies and related entities.\n\n"
    "Your task is to analyse open source information about a company and produce:\n"
    "- a short snapshot of recent business and company developments\n"
    "- a structured profile for the customer and any corporate guarantor\n"
    "- a list of high risk individuals or entities linked to the customer or guarantor\n\n"
    "Always prioritise Malaysian context and institutions where relevant.\n"
)


# ==================== SNAPSHOT TEMPLATE ====================

SNAPSHOT_TEMPLATE = (
    "{system_prompt}\n\n"
    "COMPANY NAME: {company}\n\n"
    "AVAILABLE INFORMATION (each item is truncated):\n"
    "{documents_block}\n\n"
    "TASK:\n"
    "- Write one concise narrative snapshot (1-3 short paragraphs, about 5-8 sentences total).\n"
    "- Focus on business activities, recent developments, financings, ratings, major strategic moves, "
    "and any clearly material regulatory or controversy items.\n"
    "- Write in neutral, factual language based only on the provided information.\n"
    "- If ratings (ram or marc) are present, include them.\n"
    "- If sustainability or esg reporting is present, summarise it briefly.\n"
    "- Do not output bullet points, numbered lists, section headings, or JSON.\n"
    "- Do not mention document numbers, indices, or any labels such as 'Source:', 'Title:', 'Date:', 'URL:' or '---'.\n"
    "- Do not mention that you are summarising documents or that information comes from specific sources.\n"
    "- Do not include any bracketed reference markers such as [1], [2], etc.\n"
)


# ==================== PROFILE TEMPLATE ====================

PROFILE_TEMPLATE = (
    "{system_prompt}\n\n"
    "COMPANY NAME: {company}\n\n"
    "AVAILABLE INFORMATION (each item is truncated):\n"
    "{documents_block}\n\n"
    "ADDITIONAL CONTEXT FROM PRIOR EXTRACTION (may be incomplete or noisy):\n"
    "{context_block}\n\n"
    "TASK:\n"
    "Use all of the information above to return a single valid JSON object only.\n"
    "Do not wrap the JSON in markdown code fences such as ```json ... ```.\n"
    "Do not include any comments, explanations, or extra keys outside the required structure.\n\n"
    "The top-level JSON object must have exactly these keys:\n"
    "  - \"customer\"\n"
    "  - \"corporate_guarantor\"\n"
    "  - \"high_risk_entities\"\n\n"
    "Rules for each key:\n"
    "1. \"customer\" must be an object with the fields:\n"
    "   - \"name\" (string or null)\n"
    "   - \"rating\" (string or null)\n"
    "   - \"esg_scorecard\" (string or null)\n"
    "   - \"new_director\" (string or null)\n"
    "   - \"appointment_date\" (string or null)\n"
    "   The customer is the party clearly described as the customer or borrower in the documents.\n"
    "   If no such party can be reliably identified, set \"name\" to null.\n"
    "   IMPORTANT: do not set customer.name to COMPANY NAME. if the only company present is COMPANY NAME, set customer.name to null.\n"
    "   If ratings or esg information clearly applies to COMPANY NAME but no customer is identified, "
    "you may still fill \"rating\" and \"esg_scorecard\" while keeping \"name\" as null.\n\n"
    "2. \"corporate_guarantor\" must be an object with the fields:\n"
    "   - \"name\" (string or null)\n"
    "   - \"rating\" (string or null)\n"
    "   - \"esg_scorecard\" (string or null)\n"
    "   - \"new_director\" (string or null)\n"
    "   - \"appointment_date\" (string or null)\n"
    "   The corporate guarantor is any company clearly described as providing a corporate guarantee.\n"
    "   If none is found, set every field under \"corporate_guarantor\" to null.\n"
    "   IMPORTANT: do not set corporate_guarantor.name to COMPANY NAME. if guarantor cannot be shown as a separate guarantor, set it to null.\n\n"
    "3. \"high_risk_entities\" must be a JSON array.\n"
    "   Each element must be an object with fields:\n"
    "   - \"name\" (string)\n"
    "   - \"position\" (string or null)\n"
    "   - \"relationship\" (string or null)\n"
    "   Include individuals or entities that appear clearly high risk in the provided documents, even if they are not directly linked to a customer or guarantor.\n"
    "   If no such high risk individuals or entities are found, return an empty list for \"high_risk_entities\".\n\n"
    "Additional guidance:\n"
    "- \"rating\" should summarise the most recent clear credit rating description if present "
    "(agency, grade, outlook, date); otherwise use null.\n"
    "- \"esg_scorecard\" should summarise the main ESG or sustainability signals affecting risk "
    "in 1-3 short sentences; otherwise use null.\n"
    "- \"new_director\" and \"appointment_date\" should be set only when the documents clearly "
    "mention a new director appointment with an effective date; otherwise use null.\n"
    "- For each entry in \"high_risk_entities\", \"position\" should describe role if clear.\n"
    "- For each entry in \"high_risk_entities\", \"relationship\" should briefly describe how they relate "
    "to the queried company or other key entities.\n"
    "- Use the additional context block only as a rough hint. Always give priority to the full documents.\n"
    "- Use standard JSON formatting with double quotes around all keys and string values.\n"
)


# ==================== SEED QUERY GENERATOR TEMPLATE ====================

SEED_QUERY_GENERATOR_TEMPLATE = (
    "You are a research planner generating seed entity names for a Malaysia-focused business intelligence system.\n\n"
    "Existing seed entities:\n"
    "{existing_entities}\n\n"
    "Task:\n"
    "- Generate 120-200 NEW entity names.\n"
    "- Each item should be a company, financial institution, government-linked company, regulator, or notable individual.\n"
    "- Focus primarily on Malaysia and ASEAN, but you may include key global firms that are likely to interact with Malaysia.\n"
    "- Each item should be a short name, not a sentence (e.g. \"Maybank\", \"Tenaga Nasional Berhad\", \"Securities Commission Malaysia\", \"Najib Razak\").\n"
    "- Do NOT repeat any name that appears in the existing seed entities list above.\n\n"
    "Format:\n"
    "Return a SINGLE valid JSON object, with one key \"queries\" that is a list of strings.\n"
    "Do not include any other keys, comments, or explanation.\n\n"
    "Example:\n"
    "{\n"
    "    \"queries\": [\n"
    "        \"Malayan Banking Berhad\",\n"
    "        \"Tenaga Nasional Berhad\",\n"
    "        \"Securities Commission Malaysia\"\n"
    "    ]\n"
    "}\n"
)