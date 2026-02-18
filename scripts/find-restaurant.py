#!/usr/bin/env python3
"""
맛집 찾기 스크립트
사용법: python find-restaurant.py "세종시" [카테고리]
"""

import sys
import requests
import json
import re

def search_restaurants(query, category=None, limit=10):
    """카카오맵에서 맛집 검색"""
    
    search_query = f"{query} 맛집"
    if category:
        search_query = f"{query} {category}"
    
    url = "https://search.map.kakao.com/mapsearch/map.daum"
    params = {
        "callback": "jQuery",
        "q": search_query,
        "msFlag": "A",
        "sort": "0"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://map.kakao.com/"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        text = response.text
        
        json_match = re.search(r'jQuery\((.*)\)', text, re.DOTALL)
        if not json_match:
            return None
            
        data = json.loads(json_match.group(1))
        places = data.get('place', [])
        
        if not places:
            return []
        
        results = []
        for p in places[:limit]:
            # 카테고리 조합
            cats = [p.get(f'cate_name_depth{i}', '') for i in range(1, 6)]
            category_str = ' > '.join([c for c in cats if c])
            
            # 평점
            rating = p.get('rating_average') or p.get('kplace_rating') or '-'
            if rating != '-':
                rating = f"{float(rating):.1f}"
            
            results.append({
                'name': p.get('name', ''),
                'category': category_str,
                'address': p.get('new_address_disp') or p.get('address_disp') or p.get('address', ''),
                'phone': p.get('tel', '-') or '-',
                'rating': rating,
                'review_count': p.get('rating_count') or p.get('reviewCount') or 0,
                'url': f"https://place.map.kakao.com/{p.get('confirmid', '')}"
            })
        
        return results
        
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return None

def print_results(results, query):
    """결과 출력"""
    if not results:
        print("검색 결과가 없습니다.")
        return
    
    print(f"\n🍽️  '{query}' 맛집 Top {len(results)}")
    print("=" * 65)
    
    for i, r in enumerate(results, 1):
        # 평점 & 리뷰
        rating_str = f"⭐{r['rating']}" if r['rating'] != '-' else ""
        review_str = f"({r['review_count']})" if r['review_count'] else ""
        
        print(f"\n{i}. {r['name']} {rating_str} {review_str}")
        print(f"   📍 {r['address']}")
        if r['category']:
            cat_short = r['category'].split(' > ')[-1] if ' > ' in r['category'] else r['category']
            print(f"   🏷️  {cat_short}")
        if r['phone'] != '-':
            print(f"   📞 {r['phone']}")
        print(f"   🔗 {r['url']}")
    
    print("\n" + "=" * 65)

def main():
    if len(sys.argv) < 2:
        print("🍽️  맛집 찾기")
        print("-" * 40)
        print("사용법: python find-restaurant.py <지역> [종류]")
        print()
        print("예시:")
        print("  python find-restaurant.py 세종시")
        print("  python find-restaurant.py 세종시 한식")
        print("  python find-restaurant.py '대전 둔산동' 삼겹살")
        print("  python find-restaurant.py 조치원 순대국밥")
        sys.exit(0)
    
    location = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else None
    
    query_display = location + (f" {category}" if category else "")
    print(f"🔍 '{query_display}' 검색 중...")
    
    results = search_restaurants(location, category)
    if results:
        print_results(results, query_display)

if __name__ == "__main__":
    main()
