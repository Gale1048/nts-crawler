import requests
from bs4 import BeautifulSoup
import os
import re

# 🔑 환경변수
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 🔥 날짜 변환
def convert_date(date_str):
    return date_str.replace(".", "-").strip("-")

# 🔥 기존 데이터 (중복 방지)
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
rows.reverse()

for row in rows:
    a_tag = row.select_one("a")

    if not a_tag:
        continue

    # 🔥🔥🔥 핵심 수정 (문자열 정리)
    raw_title = a_tag.text

    title = re.sub(r"\s+", " ", raw_title).strip()   # 공백 정리
    title = re.sub(r"^N\s*", "", title)             # 앞에 N 제거

    if not title:
        continue

    if title in existing_titles:
        print("스킵:", title)
        continue

    # 🔥 날짜
    tds = row.select("td")
    raw_date = tds[3].text.strip()
    date = convert_date(raw_date)

    print("처리:", title)

    # 🔥 JS 파라미터 추출
    onclick = a_tag.get("href")

    if "javascript" not in onclick:
        continue

    parts = onclick.split("'")

    try:
        nttId = parts[5]
        fileId = parts[7]
        fileKey = parts[9]
    except:
        print("❌ 파싱 실패")
        continue

    # 🔥 viewer 링크 생성
    viewer_link = f"https://doc.nts.go.kr:8080/SynapDocViewServer/job?fileType=URL&convertType=1&sync=true&filePath=http://www.nts.go.kr/comm/nttFileDownload.do?fileKey={fileKey}&fid={fileId}{fileKey}"

    print("링크:", viewer_link)

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

    res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

    if res.status_code == 200:
        print("🎉 성공:", title)
    else:
        print("❌ 실패:", res.text)
