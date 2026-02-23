"""
BEACON FEED GENERATION V2
==========================

Generates personalized mentor feeds using:
- New data structure (mentor_profiles.json, mentee_profiles.json)
- Bilateral scoring with goal alignment
- Stable matching (to be added)
- LLM reasoning for each match

Feed Structure:
1. ⭐ Stable match (if exists) - highlighted
2. Top bilateral matches sorted by score
"""

from typing import List, Dict, Optional
from beacon_core_v2 import (
    get_mentor,
    get_mentee,
    extract_university,
    calculate_total_experience,
)
from beacon_goal_alignment import calculate_bilateral_score_with_goals
from beacon_bilateral_scoring_v2 import estimate_acceptance_probability


# ============================================================================
# FEED ITEM CREATION
# ============================================================================

def create_feed_item(mentor_id: str, mentee_id: str, data: Dict, 
                     is_stable_match: bool = False) -> Dict:
    """
    Create a complete feed item for a mentee.
    
    Returns:
        Dict with all info needed to display in UI
    """
    mentee = get_mentee(mentee_id, data)
    
    # Calculate scores with goal alignment
    scores = calculate_bilateral_score_with_goals(mentor_id, mentee_id, data)
    
    if not scores['eligible']:
        return None
    
    # Build feed item
    item = {
        'mentee_id': mentee_id,
        'name': mentee['name'],
        'university': extract_university(mentee) or 'Unknown',
        'location': mentee.get('location', 'Unknown'),
        'gpa': mentee.get('gpa'),
        'current_position': mentee.get('current_position', 'Unknown'),
        'current_company': mentee.get('current_company', 'Unknown'),
        'current_industry': mentee.get('current_industry', 'Unknown'),
        'total_experience_years': calculate_total_experience(mentee),
        
        # Past positions (top 2)
        'past_positions': mentee.get('past_positions', [])[:2],
        
        # What they need help with
        'help_seeking': mentee.get('what_i_need_help_with', []),
        
        # Goals and context
        'goals': mentee.get('goals', ''),
        'more_info': mentee.get('more_info', ''),
        
        # Scores
        'bilateral_score': scores['bilateral_score'],
        'mentor_score': scores['mentor_score'],
        'mentee_score': scores['mentee_score'],
        'goal_alignment_score': scores['goal_alignment_score'],
        'goal_reasoning': scores['goal_reasoning'],
        'acceptance_probability': estimate_acceptance_probability(scores['mentee_score']),
        
        # Metadata
        'is_stable_match': is_stable_match,
    }
    
    return item


# ============================================================================
# FEED GENERATION
# ============================================================================

def generate_mentor_feed(mentor_id: str, data: Dict, 
                        feed_size: int = 5,
                        min_bilateral_score: float = 50.0,
                        excluded_mentee_ids: Optional[List[str]] = None) -> List[Dict]:
    """
    Generate personalized feed for a mentor.
    
    Args:
        mentor_id: Mentor ID
        data: Full dataset
        feed_size: Number of mentees to show
        min_bilateral_score: Minimum score threshold
        excluded_mentee_ids: Mentees to exclude (already contacted)
        
    Returns:
        List of feed items sorted by bilateral score
    """
    excluded = excluded_mentee_ids or []
    
    # Get all mentees
    all_mentees = data['mentees']
    
    # Score all eligible mentees
    print(f"\n🔄 Scoring {len(all_mentees)} mentees...")
    
    feed_items = []
    
    for i, mentee in enumerate(all_mentees):
        if (i + 1) % 100 == 0:
            print(f"   Processed {i + 1}/{len(all_mentees)}...")
        
        mentee_id = mentee['id']
        
        # Skip excluded
        if mentee_id in excluded:
            continue
        
        # Create feed item
        item = create_feed_item(mentor_id, mentee_id, data, is_stable_match=False)
        
        if item and item['bilateral_score'] >= min_bilateral_score:
            feed_items.append(item)
    
    # Sort by bilateral score descending
    feed_items.sort(key=lambda x: x['bilateral_score'], reverse=True)
    
    # Take top N
    feed_items = feed_items[:feed_size]
    
    # Mark top as stable match (simplified - real version would use Gale-Shapley)
    if feed_items:
        feed_items[0]['is_stable_match'] = True
    
    print(f"✓ Generated feed with {len(feed_items)} matches")
    
    return feed_items


# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def display_feed(feed: List[Dict]):
    """Display feed in terminal (for testing)."""
    if not feed:
        print("\n⚠️  No matches found")
        return
    
    print(f"\n{'='*80}")
    print(f"YOUR MATCHES ({len(feed)} prospects)")
    print(f"{'='*80}\n")
    
    for i, item in enumerate(feed, 1):
        if item['is_stable_match']:
            print(f"{'─'*80}")
            print(f"⭐ Best Match")
            print(f"{'─'*80}\n")
        
        print(f"#{i}. {item['name']}")
        print(f"    {item['university']}")
        print(f"    📍 {item['location']}")
        if item['gpa']:
            print(f"    📊 GPA: {item['gpa']}")
        
        print(f"\n    💼 Current: {item['current_position']} at {item['current_company']}")
        print(f"       Industry: {item['current_industry']}")
        print(f"       Experience: {item['total_experience_years']} years")
        
        if item['past_positions']:
            print(f"\n    📋 Past Positions:")
            for pos in item['past_positions']:
                if pos.get('duration'):
                    print(f"       • {pos['title']} at {pos['company']} ({pos['duration']})")
        
        print(f"\n    🎯 Goal: {item['goals']}")
        print(f"    💭 Context: {item['more_info'][:100]}...")
        
        print(f"\n    🤝 Seeking help with:")
        for help_item in item['help_seeking'][:3]:
            print(f"       • {help_item}")
        
        print(f"\n    📊 Match Scores:")
        print(f"       Bilateral: {item['bilateral_score']:.1f}/100")
        print(f"       Your perspective: {item['mentor_score']:.1f}/100")
        print(f"       Their perspective: {item['mentee_score']:.1f}/100")
        print(f"       Goal Alignment: {item['goal_alignment_score']:.2f}/1.0")
        print(f"       Acceptance probability: {item['acceptance_probability']*100:.0f}%")
        
        print(f"\n    ✨ Why this match?")
        print(f"       {item['goal_reasoning']}")
        
        print()


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from beacon_core_v2 import load_all_data
    
    print("\n" + "="*80)
    print("BEACON FEED GENERATION V2 - TESTING")
    print("="*80)
    
    # Load data
    data = load_all_data('mentor_profiles.json', 'mentee_profiles.json')
    
    # Generate feed for first mentor
    mentor_id = 'M006'  # Nancy Gonzalez - Finance
    mentor = get_mentor(mentor_id, data)
    
    print(f"\nGenerating feed for: {mentor['name']}")
    print(f"Industry: {mentor['current_industry']}")
    
    feed = generate_mentor_feed(
        mentor_id,
        data,
        feed_size=5,
        min_bilateral_score=50.0
    )
    
    display_feed(feed)
    
    print("\n" + "="*80)
    print("✓ FEED GENERATION V2 WORKING!")
    print("="*80 + "\n")
