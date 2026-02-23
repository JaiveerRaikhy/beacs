"""
BEACON BILATERAL SCORING V2
============================

Calculates match scores from both perspectives:
- Mentor's perspective (using mentor's preference weights)
- Mentee's perspective (using default/balanced weights)
- Combined bilateral score (60/40 weighted)

Key changes from v1:
- Uses new factor scores from core_v2
- Handles "Don't care" preferences (weight = 0)
- 6 base factors + optional GPA
- Ready for 7th factor (goal_alignment) to be added
"""

from typing import Dict, Optional
from beacon_core_v2 import (
    get_mentor,
    get_mentee,
    get_mentor_preferences,
    calculate_all_factor_scores,
    is_eligible_match,
)


# ============================================================================
# DEFAULT WEIGHTS (for mentees who don't set preferences)
# ============================================================================

DEFAULT_MENTEE_WEIGHTS = {
    'shared_university': 2.0,
    'university_prestige': 1.0,
    'industry_alignment': 5.0,  # Most important for mentees
    'help_type_match': 5.0,      # Critical - need right help
    'location_proximity': 2.0,
    'experience_gap': 4.0,
    'gpa': 0.0,  # Not relevant from mentee's perspective
}


# ============================================================================
# SCORING FROM MENTOR'S PERSPECTIVE
# ============================================================================

def calculate_mentor_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Calculate match score from mentor's perspective.
    
    Uses mentor's preference weights to calculate weighted average.
    
    Returns:
        Score from 0 to 100
    """
    # Get factor scores
    factor_scores = calculate_all_factor_scores(mentor_id, mentee_id, data)
    
    # Get mentor's preference weights
    mentor = get_mentor(mentor_id, data)
    weights = get_mentor_preferences(mentor)
    
    # Calculate weighted score
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor, score in factor_scores.items():
        # Map factor names to preference keys
        factor_map = {
            'shared_university': 'university',
            'university_prestige': 'university',
            'industry_alignment': 'industry_alignment',
            'help_type_match': 'help_type',
            'location_proximity': 'location',
            'experience_gap': 'path_alignment',  # Experience gap relates to path
            'gpa': 'gpa',
        }
        
        weight_key = factor_map.get(factor)
        if weight_key:
            weight = weights.get(weight_key, 0.0)
            
            # Special case: if factor is university-related, use uni weight
            if factor in ['shared_university', 'university_prestige']:
                weight = weights.get('university', 0.0)
            
            if weight > 0:  # Only include if mentor cares
                weighted_sum += score * weight
                total_weight += weight
    
    if total_weight == 0:
        return 0.0  # Mentor doesn't care about anything (shouldn't happen)
    
    # Normalize to 0-100
    score = (weighted_sum / total_weight) * 100
    return round(score, 1)


# ============================================================================
# SCORING FROM MENTEE'S PERSPECTIVE
# ============================================================================

def calculate_mentee_score(mentor_id: str, mentee_id: str, data: Dict) -> float:
    """
    Calculate match score from mentee's perspective.
    
    Uses default weights (mentees don't set preferences).
    
    Returns:
        Score from 0 to 100
    """
    # Get factor scores
    factor_scores = calculate_all_factor_scores(mentor_id, mentee_id, data)
    
    # Use default weights
    weights = DEFAULT_MENTEE_WEIGHTS
    
    # Calculate weighted score
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor, score in factor_scores.items():
        weight = weights.get(factor, 0.0)
        
        if weight > 0:
            weighted_sum += score * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    # Normalize to 0-100
    score = (weighted_sum / total_weight) * 100
    return round(score, 1)


# ============================================================================
# BILATERAL SCORING
# ============================================================================

def calculate_bilateral_score(mentor_id: str, mentee_id: str, data: Dict) -> Dict:
    """
    Calculate bilateral match score combining both perspectives.
    
    Formula: (mentor_score × 0.6) + (mentee_score × 0.4)
    
    Returns:
        Dict with:
        - mentor_score: Score from mentor's perspective
        - mentee_score: Score from mentee's perspective
        - bilateral_score: Combined score
        - eligible: Whether pair meets hard requirements
        - ineligible_reason: Reason if not eligible
    """
    # Check eligibility first
    eligible, reason = is_eligible_match(mentor_id, mentee_id, data)
    
    if not eligible:
        return {
            'mentor_score': 0.0,
            'mentee_score': 0.0,
            'bilateral_score': 0.0,
            'eligible': False,
            'ineligible_reason': reason,
        }
    
    # Calculate scores from both perspectives
    mentor_score = calculate_mentor_score(mentor_id, mentee_id, data)
    mentee_score = calculate_mentee_score(mentor_id, mentee_id, data)
    
    # Combine with 60/40 weighting (mentor perspective weighted more)
    bilateral_score = (mentor_score * 0.6) + (mentee_score * 0.4)
    bilateral_score = round(bilateral_score, 1)
    
    return {
        'mentor_score': mentor_score,
        'mentee_score': mentee_score,
        'bilateral_score': bilateral_score,
        'eligible': True,
    }


# ============================================================================
# ACCEPTANCE PROBABILITY ESTIMATION
# ============================================================================

def estimate_acceptance_probability(mentee_score: float) -> float:
    """
    Estimate probability that mentee will accept based on their score.
    
    Higher mentee score = higher acceptance probability
    
    Returns:
        Probability from 0.0 to 1.0
    """
    if mentee_score >= 90:
        return 0.95
    elif mentee_score >= 80:
        return 0.85
    elif mentee_score >= 70:
        return 0.70
    elif mentee_score >= 60:
        return 0.50
    elif mentee_score >= 50:
        return 0.30
    elif mentee_score >= 40:
        return 0.20
    else:
        return 0.10


# ============================================================================
# BATCH SCORING
# ============================================================================

def score_multiple_mentees(mentor_id: str, mentee_ids: list, data: Dict) -> list:
    """
    Score multiple mentees for a mentor.
    
    Returns:
        List of dicts with scores, sorted by bilateral_score descending
    """
    results = []
    
    for mentee_id in mentee_ids:
        scores = calculate_bilateral_score(mentor_id, mentee_id, data)
        
        if scores['eligible']:
            scores['mentee_id'] = mentee_id
            scores['acceptance_probability'] = estimate_acceptance_probability(scores['mentee_score'])
            results.append(scores)
    
    # Sort by bilateral score descending
    results.sort(key=lambda x: x['bilateral_score'], reverse=True)
    
    return results


def filter_by_thresholds(mentor_id: str, mentee_ids: list, data: Dict,
                        min_mentor_score: float = 60.0,
                        min_mentee_score: float = 50.0,
                        min_bilateral_score: float = 55.0) -> list:
    """
    Filter mentees by score thresholds.
    
    Stage 1 of the 3-stage system: Algorithm filters for high-probability matches.
    
    Args:
        mentor_id: Mentor ID
        mentee_ids: List of mentee IDs to consider
        data: Full dataset
        min_mentor_score: Minimum score from mentor's perspective
        min_mentee_score: Minimum score from mentee's perspective
        min_bilateral_score: Minimum combined score
        
    Returns:
        List of filtered mentees with scores, sorted by bilateral_score
    """
    all_scores = score_multiple_mentees(mentor_id, mentee_ids, data)
    
    # Filter by thresholds
    filtered = [
        s for s in all_scores
        if s['mentor_score'] >= min_mentor_score
        and s['mentee_score'] >= min_mentee_score
        and s['bilateral_score'] >= min_bilateral_score
    ]
    
    return filtered


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from beacon_core_v2 import load_all_data
    
    print("\n" + "="*80)
    print("BEACON BILATERAL SCORING V2 - TESTING")
    print("="*80)
    
    # Load data
    data = load_all_data('mentor_profiles.json', 'mentee_profiles.json')
    
    # Test with first mentor
    mentor_id = data['mentors'][0]['id']
    mentor = get_mentor(mentor_id, data)
    
    print(f"\nMentor: {mentor['name']} ({mentor_id})")
    print(f"Industry: {mentor['current_industry']}")
    
    # Score against first 10 mentees
    mentee_ids = [m['id'] for m in data['mentees'][:100]]
    
    print(f"\nScoring {len(mentee_ids)} mentees...")
    
    results = filter_by_thresholds(
        mentor_id, 
        mentee_ids, 
        data,
        min_mentor_score=40.0,
        min_mentee_score=40.0,
        min_bilateral_score=40.0
    )
    
    print(f"\n✓ Found {len(results)} matches above thresholds")
    
    if results:
        print(f"\nTop 5 matches:")
        print(f"{'='*80}")
        
        for i, match in enumerate(results[:5], 1):
            mentee = get_mentee(match['mentee_id'], data)
            print(f"\n{i}. {mentee['name']} ({match['mentee_id']})")
            print(f"   Industry: {mentee['current_industry']}")
            print(f"   Bilateral Score: {match['bilateral_score']}/100")
            print(f"   Mentor View: {match['mentor_score']}/100")
            print(f"   Mentee View: {match['mentee_score']}/100")
            print(f"   Acceptance Prob: {match['acceptance_probability']*100:.0f}%")
    
    print("\n" + "="*80)
    print("✓ BILATERAL SCORING V2 WORKING!")
    print("="*80 + "\n")
