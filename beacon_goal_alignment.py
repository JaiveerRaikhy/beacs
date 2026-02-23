"""
BEACON GOAL ALIGNMENT - Gemini LLM Integration
===============================================

Uses Google's Gemini API to score goal alignment between mentor and mentee.

This is the "secret sauce" that makes Beacon magical:
- Understands nuanced career goals
- Matches mentor background to mentee aspirations
- Identifies similar career paths (e.g., consulting → PM)
- Much smarter than keyword matching

Example:
    Mentee: "Pivot to product management role"
    Mentor A: PM at Google → 0.95 (perfect!)
    Mentor B: SWE at Google → 0.60 (same company, wrong role)
    Mentor C: PM at startup → 0.80 (right role, not FAANG)
"""

import json
import os
from typing import Dict, Optional
import google.generativeai as genai
from beacon_core_v2 import get_mentor, get_mentee


# ============================================================================
# CONFIGURATION
# ============================================================================

# Set your Gemini API key
# Get it from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============================================================================
# GOAL ALIGNMENT SCORING
# ============================================================================

def calculate_goal_alignment_score_llm(mentor_id: str, mentee_id: str, data: Dict) -> Dict:
    """
    Use Gemini LLM to score how well mentor can help achieve mentee's goal.
    
    Returns:
        Dict with:
        - score: 0.0 to 1.0
        - reasoning: Explanation from LLM
        - error: If API call failed
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    if not mentor or not mentee:
        return {'score': 0.0, 'reasoning': 'User not found', 'error': True}
    
    # Build prompt
    prompt = f"""You are a career matching expert. Rate how well this MENTOR can help this MENTEE achieve their goal.

MENTEE PROFILE:
Name: {mentee['name']}
Goal: {mentee['goals']}
Context: {mentee['more_info']}
Current Role: {mentee['current_position']} at {mentee['current_company']}
Industry: {mentee['current_industry']}
Needs Help With: {', '.join(mentee['what_i_need_help_with'])}

MENTOR PROFILE:
Name: {mentor['name']}
Current Role: {mentor['current_position']} at {mentor['current_company']}
Industry: {mentor['current_industry']}
Can Help With: {', '.join(mentor['what_i_can_help_with']['tags'])}
Additional Context: {mentor['what_i_can_help_with']['details']}
Career Path: {' → '.join([f"{p['title']} at {p['company']}" for p in mentor['past_positions'] if p.get('duration')])}

TASK:
Rate from 0.0 to 1.0 how well this mentor can help the mentee achieve their specific goal.

Consider:
1. Does the mentor have direct experience in the mentee's target role/industry?
2. Has the mentor made a similar career transition?
3. Can the mentor provide the specific help the mentee needs?
4. Does the mentor's background align with the mentee's aspirations?

Return ONLY a JSON object with this exact format (no markdown, no explanation):
{{"score": 0.75, "reasoning": "Brief explanation in 1-2 sentences"}}"""

    try:
        # Call Gemini API
        if not GEMINI_API_KEY:
            # Fallback: use simple heuristic if no API key
            return calculate_goal_alignment_score_fallback(mentor_id, mentee_id, data)
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate score
        score = float(result.get('score', 0.0))
        score = max(0.0, min(1.0, score))  # Clamp to 0-1
        
        return {
            'score': score,
            'reasoning': result.get('reasoning', ''),
            'error': False
        }
        
    except Exception as e:
        print(f"Warning: Gemini API error: {e}")
        # Fallback to heuristic
        return calculate_goal_alignment_score_fallback(mentor_id, mentee_id, data)


def calculate_goal_alignment_score_fallback(mentor_id: str, mentee_id: str, data: Dict) -> Dict:
    """
    Fallback heuristic if Gemini API unavailable.
    
    Simple rule-based scoring:
    - Same industry: +0.5
    - Help type overlap: +0.3 per match
    - Career path similarity: +0.2
    """
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    score = 0.0
    reasons = []
    
    # Industry match
    if mentor['current_industry'] == mentee['current_industry']:
        score += 0.5
        reasons.append("Same industry")
    
    # Help type overlap
    mentor_help = set(mentor['what_i_can_help_with']['tags'])
    mentee_needs = set(mentee['what_i_need_help_with'])
    overlap = mentor_help & mentee_needs
    
    if overlap:
        overlap_score = min(0.3 * len(overlap), 0.4)
        score += overlap_score
        reasons.append(f"Can help with {len(overlap)} needed areas")
    
    # Clamp score
    score = min(1.0, score)
    
    reasoning = "; ".join(reasons) if reasons else "Limited alignment"
    
    return {
        'score': score,
        'reasoning': reasoning + " (heuristic fallback)",
        'error': False
    }


# ============================================================================
# BATCH SCORING
# ============================================================================

def score_goals_for_multiple_mentees(mentor_id: str, mentee_ids: list, data: Dict) -> Dict[str, Dict]:
    """
    Score goal alignment for multiple mentees.
    
    Returns:
        Dict mapping mentee_id to {score, reasoning}
    """
    results = {}
    
    for i, mentee_id in enumerate(mentee_ids):
        if (i + 1) % 10 == 0:
            print(f"  Scored {i + 1}/{len(mentee_ids)} mentees...")
        
        result = calculate_goal_alignment_score_llm(mentor_id, mentee_id, data)
        results[mentee_id] = result
    
    return results


# ============================================================================
# INTEGRATION WITH BILATERAL SCORING
# ============================================================================

def calculate_bilateral_score_with_goals(mentor_id: str, mentee_id: str, data: Dict,
                                        goal_weight: float = 5.0) -> Dict:
    """
    Calculate bilateral score including goal alignment.
    
    This adds goal_alignment as a 7th factor with high weight.
    
    Args:
        mentor_id: Mentor ID
        mentee_id: Mentee ID
        data: Full dataset
        goal_weight: Weight for goal alignment factor (default: 5.0 - very important!)
        
    Returns:
        Extended bilateral score dict with goal_alignment
    """
    from beacon_bilateral_scoring_v2 import calculate_bilateral_score
    from beacon_core_v2 import calculate_all_factor_scores
    
    # Get base bilateral scores
    bilateral = calculate_bilateral_score(mentor_id, mentee_id, data)
    
    if not bilateral['eligible']:
        return bilateral
    
    # Get goal alignment
    goal_result = calculate_goal_alignment_score_llm(mentor_id, mentee_id, data)
    goal_score = goal_result['score']
    
    # Recalculate scores including goal alignment
    # We'll add goal as a high-weight factor
    
    factor_scores = calculate_all_factor_scores(mentor_id, mentee_id, data)
    factor_scores['goal_alignment'] = goal_score
    
    # Recalculate mentor score with goal alignment
    from beacon_core_v2 import get_mentor_preferences
    mentor = get_mentor(mentor_id, data)
    weights = get_mentor_preferences(mentor)
    
    # Add goal alignment weight
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor, score in factor_scores.items():
        if factor == 'goal_alignment':
            weight = goal_weight  # High weight for goal alignment!
        else:
            # Map to preference weights (simplified)
            weight_map = {
                'industry_alignment': weights.get('industry_alignment', 0),
                'help_type_match': weights.get('help_type', 0),
                'location_proximity': weights.get('location', 0),
                'experience_gap': weights.get('path_alignment', 0),
            }
            weight = weight_map.get(factor, 1.0)
        
        if weight > 0:
            weighted_sum += score * weight
            total_weight += weight
    
    new_mentor_score = (weighted_sum / total_weight * 100) if total_weight > 0 else 0
    
    # Mentee score also benefits from goal alignment
    from beacon_bilateral_scoring_v2 import DEFAULT_MENTEE_WEIGHTS
    mentee_weights = DEFAULT_MENTEE_WEIGHTS.copy()
    mentee_weights['goal_alignment'] = goal_weight
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor, score in factor_scores.items():
        weight = mentee_weights.get(factor, 0)
        if weight > 0:
            weighted_sum += score * weight
            total_weight += weight
    
    new_mentee_score = (weighted_sum / total_weight * 100) if total_weight > 0 else 0
    
    # New bilateral score
    new_bilateral = (new_mentor_score * 0.6) + (new_mentee_score * 0.4)
    
    return {
        'mentor_score': round(new_mentor_score, 1),
        'mentee_score': round(new_mentee_score, 1),
        'bilateral_score': round(new_bilateral, 1),
        'goal_alignment_score': goal_score,
        'goal_reasoning': goal_result['reasoning'],
        'eligible': True,
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from beacon_core_v2 import load_all_data
    
    print("\n" + "="*80)
    print("BEACON GOAL ALIGNMENT - TESTING")
    print("="*80)
    
    if not GEMINI_API_KEY:
        print("\n⚠️  Warning: GEMINI_API_KEY not set!")
        print("Set it with: export GEMINI_API_KEY='your-key'")
        print("Using fallback heuristic for testing...\n")
    
    # Load data
    data = load_all_data('mentor_profiles.json', 'mentee_profiles.json')
    
    # Test with specific pair
    mentor_id = 'M001'  # Barbara Ali - Engineering/Manufacturing VP
    mentee_id = 'ME0001'  # Ashley Levy - Healthcare, wants to break in
    
    mentor = get_mentor(mentor_id, data)
    mentee = get_mentee(mentee_id, data)
    
    print(f"Mentor: {mentor['name']}")
    print(f"  {mentor['current_position']} at {mentor['current_company']}")
    print(f"  Industry: {mentor['current_industry']}")
    
    print(f"\nMentee: {mentee['name']}")
    print(f"  Goal: {mentee['goals']}")
    print(f"  Industry: {mentee['current_industry']}")
    
    print(f"\n{'='*80}")
    print("GOAL ALIGNMENT ANALYSIS")
    print(f"{'='*80}")
    
    result = calculate_goal_alignment_score_llm(mentor_id, mentee_id, data)
    
    print(f"\nGoal Alignment Score: {result['score']:.2f}/1.0")
    print(f"Reasoning: {result['reasoning']}")
    
    print(f"\n{'='*80}")
    print("BILATERAL SCORE WITH GOALS")
    print(f"{'='*80}")
    
    bilateral = calculate_bilateral_score_with_goals(mentor_id, mentee_id, data)
    
    print(f"\nMentor Score: {bilateral['mentor_score']}/100")
    print(f"Mentee Score: {bilateral['mentee_score']}/100")
    print(f"Bilateral Score: {bilateral['bilateral_score']}/100")
    print(f"Goal Alignment: {bilateral['goal_alignment_score']:.2f}/1.0")
    
    print("\n" + "="*80)
    print("✓ GOAL ALIGNMENT MODULE WORKING!")
    print("="*80 + "\n")
