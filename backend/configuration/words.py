"""
centralize word definitions
stopwords for multiple languages
relationship stopwords
"""

# ==================== ENGLISH STOPWORDS ====================

ENGLISH_STOPWORDS = {
    # articles
    "a", "an", "the",

    # pronouns
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",

    # verbs
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "could", "should", "might", "must", "shall",
    "can", "need", "dare", "ought", "used",

    # prepositions
    "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "out", "off",
    "over", "under", "again", "further", "then", "once",

    # conjunctions
    "and", "but", "or", "nor", "so", "yet", "both", "either",
    "neither", "not", "only", "own", "same", "than", "too", "very",

    # question words
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "when", "where", "why", "how",

    # other common words
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "any", "if", "because", "as", "until",
    "while", "of", "also", "just", "now", "here", "there"
}


# ==================== MALAY STOPWORDS ====================

MALAY_STOPWORDS = {
    # articles and particles
    "dan", "yang", "di", "ke", "dari", "pada", "untuk", "dengan",
    "adalah", "ini", "itu", "atau", "juga", "akan", "tetapi",
    "oleh", "serta", "dalam", "sebagai", "tidak", "telah", "sudah",
    "dapat", "bagi", "antara", "setelah", "bila", "jika", "agar",
    "supaya", "bahawa", "kerana", "walau", "walaupun", "namun",
    "seperti", "iaitu", "yakni", "sehingga", "hingga", "sambil",
    "ketika", "semasa", "sejak", "sebelum", "sesudah", "selama",
    "apabila", "manakala", "sedangkan", "maka", "lalu", "kemudian",
    "saya", "kami", "kita", "anda", "mereka", "dia", "beliau",
    "nya", "pun", "lah", "kah"
}


# ==================== RELATIONSHIP STOPWORDS ====================

RELATIONSHIP_STOPWORDS = {
    # common fragments
    "the", "of", "in", "a", "an", "and", "or", "-", "–", "—",

    # single characters
    "'", '"', ",", ".", ":", ";",

    # malay particles
    "dan", "yang", "di", "ke", "dari"
}


# ==================== COMBINED STOPWORDS ====================

ALL_STOPWORDS = ENGLISH_STOPWORDS | MALAY_STOPWORDS