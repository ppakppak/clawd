#!/usr/bin/env python3
"""
맛집 찾기 스크립트 v2 (크롤링 방식)
사용법: python find-restaurant-v2.py "세종시" [카테고리]
"""

import sys
import requests
from bs4 import BeautifulSoup
import json
import re

def search_kakao_map(query, category=None):
    """카카오맵 웹에서 검색"""
    
    search_query = f"{query} 맛집"
    if category:
        search_query = f"{query} {category}"
    
    # 카카오맵 검색 API (비공식)
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
        
        # JSONP에서 JSON 추출
        text = response.text
        json_match = re.search(r'jQuery\((.*)\)', text, re.DOTALL)
        if not json_match:
            return None
            
        data = json.loads(json_match.group(1))
        places = data.get('place', {}).get('list', [])
        
        results = []
        for p in places[:10]:
            results.append({
                'name': p.get('name', ''),
                'category': p.get('category', ''),
                'address': p.get('address', ''),
                'phone': p.get('phone', '-') or '-',
                'score': p.get('score', {}).get('avg', '-'),
                'review_count': p.get('review', {}).get('count', 0),
                'url': f"https://place.map.kakao.com/{p.get('cid', '')}"
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
    
    print(f"\n🍽️  {query} 맛집 검색 결과")
    print("=" * 65)
    
    for i, r in enumerate(results, 1):
        score_str = f"⭐ {r['score']}" if r['score'] != '-' else ""
        review_str = f"({r['review_count']}개 리뷰)" if r['review_count'] else ""
        
        print(f"\n{i}. {r['name']} {score_str} {review_str}")
        print(f"   📍 {r['address']}")
        print(f"   🏷️  {r['category']}")
        if r['phone'] != '-':
            print(f"   📞 {r['phone']}")
        print(f"   🔗 {r['url']}")
    
    print("\n" + "=" * 65)

def main():
    if len(sys.argv) < 2:
        print("사용법: python find-restaurant-v2.py <지역> [카테고리]")
        print("예시:")
        print("  python find-restaurant-v2.py 세종시")
        print("  python find-restaurant-v2.py 세종시 한식")
        print("  python find-restaurant-v2.py '대전 둔산동' 삼겹살")
        sys.exit(1)
    
    location = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🔍 '{location}' 맛집 검색 중...")
    
    results = search_kakao_map(location, category)
    if results:
        print_results(results, location + (f" {category}" if category else ""))
    else:
        print("검색 결과를 가져오지 못했습니다.")

if __name__ == "__main__":
    main()
