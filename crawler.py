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

def convert_date(date_str):
    return date_str.replace(".", "-").strip("-")

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

# 📡 페이지 요청
url = "https://www.nts.go.kr/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028"
res = requests.get(url)
soup = BeautifulSoup(res.text, "html.parser")

rows = soup.select("tbody tr")
rows.reverse()

for row in rows:
    a_tag = row.select_one("a")
    if not a_tag:
        continue

    # ✅ 제목 정리 (N + 공백)
    raw_title = a_tag.text
    title = re.sub(r"\s+", " ", raw_title).strip()
    title = re.sub(r"^N\s*", "", title)

    if not title:
        continue

    if title in existing_titles:
        print("스킵:", title)
        continue

    # 날짜
    tds = row.select("td")
    raw_date = tds[3].text.strip()
    date = convert_date(raw_date)

    print("\n처리:", title)

    # 🔥 핵심: href + onclick 둘 다 대응
    onclick = a_tag.get("href")

    if not onclick or onclick.strip() == "javascript:;":
        onclick = a_tag.get("onclick")

    print("JS:", onclick)

    if not onclick:
        print("❌ 링크 없음 → 스킵")
        continue

    # 🔥 파싱
    matches = re.findall(r"'(.*?)'", onclick)

    if len(matches) < 5:
        print("❌ 파싱 실패:", onclick)
        continue

    try:
        nttId = matches[2]
        fileId = matches[3]
        fileKey = matches[4]
    except:
        print("❌ 파싱 오류:", onclick)
        continue

    # 🔥 링크 생성
    viewer_link = f"https://doc.nts.go.kr:8080/SynapDocViewServer/job?fileType=URL&convertType=1&sync=true&filePath=http://www.nts.go.kr/comm/nttFileDownload.do?fileKey={fileKey}&fid={fileId}{fileKey}"

    print("링크:", viewer_link)

    # 노션 업로드
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
