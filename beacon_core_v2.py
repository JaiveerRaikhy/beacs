"""
BEACON CORE V2 - Adapted for New Data Structure
================================================

New data structure:
- mentor_profiles.json (200 mentors)
- mentee_profiles.json (1000 mentees)

Key changes:
- Direct industry from current_industry field
- Extract university from past_positions (education entries)
- Calculate experience from duration fields
- Parse location as "City, State"
- Handle "Don't care" preferences
- 7 matching factors (dropped brand internships)
"""

import json
import re
from typing import Dict, List, Optional, Tuple


# ============================================================================
# DATA LOADING
# ============================================================================

def load_mentors(filepath: str = 'mentor_profiles.json') -> List[Dict]:
    """Load mentor profiles from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_mentees(filepath: str = 'mentee_profiles.json') -> List[Dict]:
    """Load mentee profiles from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_all_data(mentor_file: str = 'mentor_profiles.json', 
                  mentee_file: str = 'mentee_profiles.json') -> Dict:
    """
    Load all data and return combined dictionary.
    
    Returns:
        Dict with keys: mentors, mentees
    """
    mentors = load_mentors(mentor_file)
    mentees = load_mentees(mentee_file)
    
    print(f"✓ Loaded data:")
    print(f"  - {len(mentors)} mentors")
    print(f"  - {len(mentees)} mentees")
    
    return {
        'mentors': mentors,
        'mentees': mentees
    }


# ============================================================================
# DATA ACCESS HELPERS
# ============================================================================

def get_mentor(mentor_id: str, data: Dict) -> Optional[Dict]:
    """Get mentor by ID."""
    for mentor in data['mentors']:
        if mentor['id'] == mentor_id:
            return mentor
    return None


def get_mentee(mentee_id: str, data: Dict) -> Optional[Dict]:
    """Get mentee by ID."""
    for mentee in data['mentees']:
        if mentee['id'] == mentee_id:
            return mentee
    return None


def get_all_mentors(data: Dict) -> List[Dict]:
    """Get all mentors."""
    return data['mentors']


def get_all_mentees(data: Dict) -> List[Dict]:
    """Get all mentees."""
    return data['mentees']


# ============================================================================
# UNIVERSITY EXTRACTION
# ============================================================================

def extract_university(person: Dict) -> Optional[str]:
    """
    Extract university from past_positions (look for degree entries).
    
    Degree entries have titles like: "BS Computer Science", "MBA", "PhD"
    And company field is the university name.
    """
    past_positions = person.get('past_positions', [])
    
    # Look for education entries (BS, BA, MBA, PhD, MD, DO, MFA, etc.)
    degree_keywords = ['BS', 'BA', 'MBA', 'PhD', 'MD', 'DO', 'MFA', 'MS', 'MA']
    
    for position in past_positions:
        title = position.get('title', '')
        # Check if title starts with degree keyword
        for keyword in degree_keywords:
            if title.startswith(keyword):
                return position.get('company')  # Company field = university
    
    # Fallback: use university field if available (for mentors)
    return person.get('university')


# ============================================================================
# EXPERIENCE CALCULATION
# ============================================================================

def parse_duration(duration_str: Optional[str]) -> float:
    """
    Parse duration string to years.
    
    Examples:
        "3 years" → 3.0
        "6 months" → 0.5
        "2 months" → 0.17
        None → 0.0
    """
    if not duration_str:
        return 0.0
    
    duration_str = duration_str.lower().strip()
    
    # Extract number
    match = re.search(r'(\d+)', duration_str)
    if not match:
        return 0.0
    
    number = int(match.group(1))
    
    # Determine unit
    if 'year' in duration_str:
        return float(number)
    elif 'month' in duration_str:
        return number / 12.0
    else:
        return 0.0


def calculate_total_experience(person: Dict) -> float:
    """
    Calculate total years of experience from past_positions.
    
    Excludes education entries (BS, BA, MBA, etc.)
    """
    past_positions = person.get('past_positions', [])
    
    total_years = 0.0
    degree_keywords = ['BS', 'BA', 'MBA', 'PhD', 'MD', 'DO', 'MFA', 'MS', 'MA']
    
    for position in past_positions:
        title = position.get('title', '')
        
        # Skip education entries
        is_education = any(title.startswith(keyword) for keyword in degree_keywords)
        if is_education:
            continue
        
        # Add duration
        duration = position.get('duration')
        total_years += parse_duration(duration)
    
    return round(total_years, 2)


# ============================================================================
# LOCATION PARSING
# ============================================================================

def parse_location(location: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse location string "City, State" into components.
    
    Examples:
        "Miami, FL" → ("Miami", "FL")
        "New York, NY" → ("New York", "NY")
        "San Francisco, CA" → ("San Francisco", "CA")
    """
    if not location:
        return None, None
    
    parts = location.split(',')
    if len(parts) == 2:
        city = parts[0].strip()
        state = parts[1].strip()
        return city, state
    
    return None, None


def compare_locations(loc1: str, loc2: str) -> float:
    """
    Compare two locations and return similarity score.
    
    Returns:
        1.0 - Same city
        0.5 - Same state (different city)
        0.0 - Different state
    """
    if not loc1 or not loc2:
        return 0.0
    
    city1, state1 = parse_location(loc1)
    city2, state2 = parse_location(loc2)
    
    if city1 == city2 and state1 == state2:
        return 1.0  # Same city
    elif state1 == state2:
        return 0.5  # Same state
    else:
        return 0.0  # Different state


# ============================================================================
# UNIVERSITY TIER SYSTEM
# ============================================================================

UNIVERSITY_TIERS = {
    # Tier 1 - Ivy League + Stanford, MIT, Caltech
    'Harvard University': 1,
    'Yale University': 1,
    'Princeton University': 1,
    'Columbia University': 1,
    'University of Pennsylvania': 1,
    'Cornell University': 1,
    'Brown University': 1,
    'Dartmouth College': 1,
    'Stanford University': 1,
    'MIT': 1,
    'Caltech': 1,
    
    # Tier 2 - Top 20
    'Duke University': 2,
    'Northwestern University': 2,
    'Johns Hopkins University': 2,
    'University of Chicago': 2,
    'Rice University': 2,
    'Vanderbilt University': 2,
    'Washington University in St. Louis': 2,
    'Notre Dame': 2,
    'UC Berkeley': 2,
    'UCLA': 2,
    'Georgetown University': 2,
    
    # Tier 3 - Top 50
    'University of Michigan': 3,
    'University of Virginia': 3,
    'University of North Carolina': 3,
    'Georgia Tech': 3,
    'University of Texas at Austin': 3,
    'University of Wisconsin': 3,
    'University of Illinois': 3,
    'Ohio State University': 3,
    'Penn State University': 3,
    'University of Washington': 3,
    'University of Florida': 3,
    'Purdue University': 3,
    'UC San Diego': 3,
    'University of Maryland': 3,
}


def get_university_tier(university: Optional[str]) -> int:
    """
    Get tier for a university.
    
    Returns:
        1-4 (1 = best, 4 = default)
    """
    if not university:
        return 4
    
    return UNIVERSITY_TIERS.get(university, 4)  # Default tier 4


# ============================================================================
# PREFERENCE HANDLING
# ============================================================================

def get_preference_weight(preference_value) -> float:
    """
    Convert preference to weight.
    
    Args:
        preference_value: Either int (1-5) or "Don't care"
        
    Returns:
        Weight (5 for rank 1, down to 1 for rank 5, 0 for "Don't care")
    """
    if preference_value == "Don't care":
        return 0.0
    
    # Convert ranking to weight (1 → 5, 5 → 1)
    return 6 - int(preference_value)


def get_mentor_preferences(mentor: Dict) -> Dict[str, float]:
    """
    Get mentor's preference weights.
    
    Returns:
        Dict mapping factor name to weight (0.0 if "Don't care")
    """
    prefs = mentor.get('preferences', {})
    
    dont_care = "Don't care"
    
    return {
        'location': get_preference_weight(prefs.get('location', dont_care)),
        'university': get_preference_weight(prefs.get('uni', dont_care)),
        'gpa': get_preference_weight(prefs.get('gpa', dont_care)),
        'industry_alignment': get_preference_weight(prefs.get('industry_alignment', dont_care)),
        'help_type': get_preference_weight(prefs.get('help_type', dont_care)),
        'path_alignment': get_preference_weight(prefs.get('path_alignment', dont_care)),
    }


# ============================================================================
# FACTOR SCORING FUNCTIONS
# ============================================================================

def calculate_shared_university_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on shared university.
    
    Returns:
        1.0 if same university, 0.0 otherwise
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_uni = extract_university(mentor)
    mentee_uni = extract_university(mentee)
    
    if mentor_uni and mentee_uni and mentor_uni == mentee_uni:
        return 1.0
    return 0.0


def calculate_university_prestige_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on university tier similarity.
    
    Returns:
        1.0 if same tier, decreasing for tier gap
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_uni = extract_university(mentor)
    mentee_uni = extract_university(mentee)
    
    mentor_tier = get_university_tier(mentor_uni)
    mentee_tier = get_university_tier(mentee_uni)
    
    # Score based on tier difference
    tier_diff = abs(mentor_tier - mentee_tier)
    max_diff = 3  # Max possible difference (tier 1 to tier 4)
    
    score = 1.0 - (tier_diff / max_diff)
    return max(0.0, score)


def calculate_industry_alignment_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on industry match.
    
    Uses current_industry field directly.
    
    Returns:
        1.0 if exact match, 0.0 otherwise
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_industry = mentor.get('current_industry', '')
    mentee_industry = mentee.get('current_industry', '')
    
    if mentor_industry and mentee_industry and mentor_industry == mentee_industry:
        return 1.0
    return 0.0


def calculate_help_type_match_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on help type overlap.
    
    Compares mentor's "what_i_can_help_with.tags" with mentee's "what_i_need_help_with"
    
    Returns:
        Overlap score (0.0 to 1.0)
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    # Get tags
    mentor_help = mentor.get('what_i_can_help_with', {}).get('tags', [])
    mentee_needs = mentee.get('what_i_need_help_with', [])
    
    if not mentee_needs:
        return 0.0
    
    # Calculate overlap
    mentor_set = set(mentor_help)
    mentee_set = set(mentee_needs)
    
    overlap = mentor_set & mentee_set
    
    # Score = overlap / mentee needs
    score = len(overlap) / len(mentee_set)
    return min(1.0, score)


def calculate_location_proximity_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on location proximity.
    
    Returns:
        1.0 - Same city
        0.5 - Same state
        0.0 - Different state
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_location = mentor.get('location', '')
    mentee_location = mentee.get('location', '')
    
    return compare_locations(mentor_location, mentee_location)


def calculate_experience_gap_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Score based on experience gap.
    
    Ideal gap: 3-7 years (mentor has more experience)
    
    Returns:
        Score from 0.0 to 1.0
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_exp = calculate_total_experience(mentor)
    mentee_exp = calculate_total_experience(mentee)
    
    gap = mentor_exp - mentee_exp
    
    if gap <= 0:
        return 0.0  # Mentor has less experience - not good
    
    # Optimal gap: 3-7 years
    if 3 <= gap <= 7:
        return 1.0
    elif gap < 3:
        # Too small gap (less than 3 years)
        return gap / 3.0
    else:
        # Too large gap (more than 7 years) - diminishing returns
        # Gap of 10 years = 0.7, 15 years = 0.5, 20 years = 0.35
        return 1.0 / (1 + 0.1 * (gap - 7))


def calculate_gpa_score(mentor_id: str, mentee_id: str, data: Dict) -> Optional[float]:
    """
    Score based on GPA.
    
    Only calculated if mentor cares about GPA (preference != "Don't care")
    
    Returns:
        Score from 0.0 to 1.0, or None if mentor doesn't care
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    # Check if mentor cares about GPA
    gpa_pref = mentor.get('preferences', {}).get('gpa')
    if gpa_pref == "Don't care":
        return None  # Don't score GPA
    
    mentee_gpa = mentee.get('gpa', 0.0)
    
    # Normalize GPA (4.0 scale)
    # 4.0 = 1.0, 3.0 = 0.75, 2.0 = 0.5
    score = mentee_gpa / 4.0
    return min(1.0, max(0.0, score))


def calculate_all_factor_scores(mentor_id: str, mentee_id: str, data: Dict) -> Dict[str, float]:
    """
    Calculate all factor scores for a mentor-mentee pair.
    
    Returns:
        Dictionary with all factor scores
    """
    scores = {
        'shared_university': calculate_shared_university_score(mentor_id, mentee_id, data),
        'university_prestige': calculate_university_prestige_score(mentor_id, mentee_id, data),
        'industry_alignment': calculate_industry_alignment_score(mentor_id, mentee_id, data),
        'help_type_match': calculate_help_type_match_score(mentor_id, mentee_id, data),
        'location_proximity': calculate_location_proximity_score(mentor_id, mentee_id, data),
        'experience_gap': calculate_experience_gap_score(mentor_id, mentee_id, data),
    }
    
    # Add GPA if mentor cares
    gpa_score = calculate_gpa_score(mentor_id, mentee_id, data)
    if gpa_score is not None:
        scores['gpa'] = gpa_score
    
    return scores


# ============================================================================
# HARD REQUIREMENT FILTERS
# ============================================================================

def has_help_type_overlap(mentor_id: str, mentee_id: str, data: Dict) -> bool:
    """
    Check if mentor can help with at least one thing mentee needs.
    
    Returns:
        True if there's overlap, False otherwise
    """
    score = calculate_help_type_match_score(mentor_id, mentee_id, data)
    return score > 0.0


def has_sufficient_experience_gap(mentor_id: str, mentee_id: str, data: Dict) -> bool:
    """
    Check if mentor has more experience than mentee.
    
    Returns:
        True if mentor has more experience
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    mentor_exp = calculate_total_experience(mentor)
    mentee_exp = calculate_total_experience(mentee)
    
    return mentor_exp > mentee_exp


def is_eligible_match(mentor_id: str, mentee_id: str, data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check if mentor-mentee pair meets all hard requirements.
    
    Returns:
        (is_eligible, reason_if_not)
    """
    if not has_help_type_overlap(mentor_id, mentee_id, data):
        return False, "No help type overlap"
    
    if not has_sufficient_experience_gap(mentor_id, mentee_id, data):
        return False, "Insufficient experience gap"
    
    return True, None


# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def print_mentor_summary(mentor_id: str, data: Dict):
    """Print a summary of a mentor's profile."""
    mentor = get_mentor(mentor_id, data)
    if not mentor:
        print(f"Mentor {mentor_id} not found")
        return
    
    print(f"\n{'='*80}")
    print(f"MENTOR: {mentor['name']} ({mentor_id})")
    print(f"{'='*80}")
    print(f"Current: {mentor['current_position']} at {mentor['current_company']}")
    print(f"Industry: {mentor['current_industry']}")
    print(f"Location: {mentor['location']}")
    print(f"University: {extract_university(mentor)}")
    print(f"Experience: {calculate_total_experience(mentor)} years")
    
    print(f"\nCan help with:")
    for tag in mentor['what_i_can_help_with']['tags']:
        print(f"  • {tag}")
    
    print(f"\nPreferences:")
    prefs = get_mentor_preferences(mentor)
    for factor, weight in prefs.items():
        if weight > 0:
            print(f"  {factor}: {weight}")


def print_mentee_summary(mentee_id: str, data: Dict):
    """Print a summary of a mentee's profile."""
    mentee = get_mentee(mentee_id, data)
    if not mentee:
        print(f"Mentee {mentee_id} not found")
        return
    
    print(f"\n{'='*80}")
    print(f"MENTEE: {mentee['name']} ({mentee_id})")
    print(f"{'='*80}")
    print(f"Current: {mentee['current_position']} at {mentee['current_company']}")
    print(f"Industry: {mentee['current_industry']}")
    print(f"Location: {mentee['location']}")
    print(f"University: {extract_university(mentee)}")
    print(f"GPA: {mentee.get('gpa', 'N/A')}")
    print(f"Experience: {calculate_total_experience(mentee)} years")
    
    print(f"\nNeeds help with:")
    for tag in mentee['what_i_need_help_with']:
        print(f"  • {tag}")
    
    print(f"\nGoal: {mentee['goals']}")
    print(f"Context: {mentee['more_info']}")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("BEACON CORE V2 - TESTING")
    print("="*80)
    
    # Load data
    data = load_all_data('mentor_profiles.json', 'mentee_profiles.json')
    
    # Test with first mentor and mentee
    mentor_id = data['mentors'][0]['id']
    mentee_id = data['mentees'][0]['id']
    
    print_mentor_summary(mentor_id, data)
    print_mentee_summary(mentee_id, data)
    
    # Test eligibility
    print(f"\n{'='*80}")
    print("ELIGIBILITY CHECK")
    print(f"{'='*80}")
    eligible, reason = is_eligible_match(mentor_id, mentee_id, data)
    print(f"Eligible: {eligible}")
    if not eligible:
        print(f"Reason: {reason}")
    
    # Test factor scores
    print(f"\n{'='*80}")
    print("FACTOR SCORES")
    print(f"{'='*80}")
    scores = calculate_all_factor_scores(mentor_id, mentee_id, data)
    for factor, score in scores.items():
        print(f"{factor}: {score:.2f}")
    
    print("\n" + "="*80)
    print("✓ CORE V2 WORKING!")
    print("="*80 + "\n")
