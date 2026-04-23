import requests
from bs4 import BeautifulSoup
import os

# 🔑 환경변수 (GitHub Actions 사용)
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 🔥 날짜 변환 (2026.04.23 → 2026-04-23)
def convert_date(date_str):
    return date_str.replace(".", "-").strip("-")

# 🔥 기존 데이터 조회 (중복 방지)
def get_existing_titles():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=headers)
    data = res.json()

    titles = set()

    for item in data.get("results", []):
        try:
            t = item["properties"]["제목"]["title"][0]["text"]["content"]
            titles.add(t)
        except:
            pass

    return titles

existing_titles = get_existing_titles()
print("기존 데이터 개수:", len(existing_titles))

# 📡 국세청 목록 페이지
url = "https://www.nts.go.kr/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028"

res = requests.get(url)
soup = BeautifulSoup(res.text, "html.parser")

rows = soup.select("tbody tr")

# 🔥 최신글부터 처리 (reverse)
rows.reverse()

for row in rows:
    a_tag = row.select_one("a")

    if not a_tag:
        continue

    # 🔥 N 제거 + 줄바꿈 제거
    title = a_tag.text.replace("\n", "").replace("N", "").strip()

    if not title:
        continue

    if title in existing_titles:
        print("스킵:", title)
        continue

    # 🔥 날짜 추출
    try:
        tds = row.select("td")
        raw_date = tds[3].text.strip()
        date = convert_date(raw_date)
    except:
        date = "2024-01-01"

    print("\n처리:", title)

    # 🔥 JS 추출 (모든 케이스 대응)
    onclick = a_tag.get("href")

    # 1️⃣ a href
    if not onclick or onclick.strip() == "javascript:;":
        onclick = a_tag.get("onclick")

    # 2️⃣ a onclick
    if not onclick or onclick.strip() == "javascript:;":
        onclick = row.get("onclick")

    # 3️⃣ 최종 검증
    if not onclick or "fn_" not in str(onclick):
        print("❌ 링크 없음 → 스킵")
        continue

    print("JS:", onclick)

    # 🔥 JS 파라미터 파싱
    parts = onclick.split("'")

    try:
        # 구조: fn_상세보기('', '1028', 'nttId', 'fileId', '파일명', 'fileKey')
        nttId = parts[5]
        fileId = parts[7]
        fileKey = parts[9]
    except:
        print("❌ 파싱 실패:", onclick)
        continue

    # 🔥 뷰어 링크 생성 (핵심)
    viewer_link = f"https://doc.nts.go.kr:8080/SynapDocViewServer/job?fileType=URL&convertType=1&sync=true&filePath=http://www.nts.go.kr/comm/nttFileDownload.do?fileKey={fileKey}&fid={fileId}{fileKey}"

    print("뷰어 링크:", viewer_link)

    # 📤 노션 업로드
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "제목": {
                "title": [{"text": {"content": title}}]
            },
            "링크": {
                "url": viewer_link
            },
            "유형": {
                "select": {"name": "국세청"}
            },
            "날짜": {
                "date": {"start": date}
            }
        }
    }

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=data
    )

    if res.status_code == 200:
        print("🎉 저장 성공")
    else:
        print("❌ 실패:", res.text)
