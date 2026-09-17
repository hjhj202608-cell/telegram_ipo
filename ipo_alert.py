import html,json,os,re,ssl,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import date,datetime,timedelta
from pathlib import Path
try:
 import holidays
except ImportError:
 holidays=None

LIST_URL="https://www.38.co.kr/html/fund/index.htm?o=k"
IPO_KOREA="https://ipokorea.kr/"
STATE=Path("state/sent.json")
UA={"User-Agent":"Mozilla/5.0 (compatible; IPO-Alert/2.0)"}
SSL_CONTEXT=ssl.create_default_context()
SSL_CONTEXT.set_ciphers("DEFAULT:@SECLEVEL=1")

def request(url,data=None,headers=None):
 body=urllib.parse.urlencode(data).encode() if data else None
 req=urllib.request.Request(url,data=body,headers=headers or UA)
 with urllib.request.urlopen(req,timeout=35,context=SSL_CONTEXT) as r:return r.read()

def decode(raw):
 for enc in ("euc-kr","cp949","utf-8"):
  try:return raw.decode(enc)
  except UnicodeDecodeError:pass
 return raw.decode("utf-8","replace")

def clean(page):
 text=decode(page)
 text=re.sub(r"<(script|style)[^>]*>.*?</\1>"," ",text,flags=re.I|re.S)
 text=re.sub(r"<[^>]+>"," ",text)
 return re.sub(r"\s+"," ",html.unescape(text)).strip()

def parse_date(value):
 if not value:return None
 value=value.strip().replace(".","-")
 try:return datetime.strptime(value,"%Y-%m-%d").date()
 except ValueError:return None

def capture(text,pattern):
 m=re.search(pattern,text,re.I)
 return m.group(1).strip() if m else ""

def detail_links():
 page=decode(request(LIST_URL))
 links=[]
 for href in re.findall(r'href=["\']([^"\']+)["\']',page,re.I):
  value=html.unescape(href)
  if re.search(r'(?:\?|&)no=\d+',value) and re.search(r'(?:\?|&)o=v(?:&|$)',value):
   url=urllib.parse.urljoin(LIST_URL,value)
   if url not in links:links.append(url)
 if not links:raise RuntimeError("38커뮤니케이션 공모주 목록을 읽지 못했습니다.")
 return links

def parse_detail(url):
 text=clean(request(url))
 name=capture(text,r"종목명\s+(.+?)\s+진행상황")
 demand=re.search(r"수요예측일\s+(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})",text)
 offer=re.search(r"공모청약일\s+(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})",text)
 if not name or not (demand or offer):return None
 return {
  "name":name,
  "market":capture(text,r"시장구분\s+(\S+)") or "미확인",
  "underwriter":capture(text,r"주간사\s+(.+?)\s+주식수:") or "미확인",
  "demand_start":parse_date(demand.group(1)) if demand else None,
  "demand_end":parse_date(demand.group(2)) if demand else None,
  "offer_start":parse_date(offer.group(1)) if offer else None,
  "offer_end":parse_date(offer.group(2)) if offer else None,
  "payment":parse_date(capture(text,r"납입일\s+(\d{4}\.\d{2}\.\d{2})")),
  "listing":parse_date(capture(text,r"상장일\s+(\d{4}\.\d{2}\.\d{2})")),
  "source":url,
 }

def records_38():
 records=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  futures=[pool.submit(parse_detail,url) for url in detail_links()]
  for future in as_completed(futures):
   try:
    record=future.result()
    if record:records.append(record)
   except Exception as exc:print("38 상세 수집 실패:",exc)
 if not records:raise RuntimeError("38커뮤니케이션 상세 일정을 읽지 못했습니다.")
 return records

def records_ipokorea():
 page=html.unescape(request(IPO_KOREA).decode("utf-8"));chunks=[]
 for m in re.finditer(r"self\.__next_f\.push\((.*?)\)</script>",page,re.S):
  try:
   value=json.loads(m.group(1))
   if isinstance(value,list) and len(value)>1 and isinstance(value[1],str):chunks.append(value[1])
  except json.JSONDecodeError:pass
 payload="\n".join(chunks);decoder=json.JSONDecoder();raw={}
 for m in re.finditer(r'\{"id":"',payload):
  try:item,_=decoder.raw_decode(payload[m.start():])
  except json.JSONDecodeError:continue
  if isinstance(item,dict) and item.get("회사명"):raw[item.get("id",item["회사명"])]=item
 out=[]
 for item in raw.values():
  out.append({
   "name":item.get("회사명",""),"market":item.get("시장구분","미확인"),"underwriter":item.get("주관사","미확인"),
   "demand_start":parse_date(item.get("수요예측시작일")),"demand_end":parse_date(item.get("수요예측종료일")),
   "offer_start":parse_date(item.get("청약시작일")),"offer_end":parse_date(item.get("청약종료일")),
   "payment":parse_date(item.get("납입기일")),"listing":parse_date(item.get("상장일")),"source":IPO_KOREA,
  })
 return out

def key(name):return re.sub(r"[^0-9a-z가-힣]","",name.lower())

def all_records():
 primary=records_38();merged={key(x["name"]):x for x in primary}
 try:
  for extra in records_ipokorea():
   k=key(extra["name"])
   if not k:continue
   if k not in merged:merged[k]=extra
   else:
    for field in ("market","underwriter","demand_start","demand_end","offer_start","offer_end","payment","listing"):
     if not merged[k].get(field) and extra.get(field):merged[k][field]=extra[field]
 except Exception as exc:print("IPO Korea 보조 수집 실패:",exc)
 print(f"수집 종목: 38커뮤니케이션 {len(primary)}개, 통합 {len(merged)}개")
 return list(merged.values())

def holiday_set(years):
 return holidays.KR(years=years) if holidays else set()

def business_day(d,off):return d.weekday()<5 and d not in off

def business_index(start,end,off):
 cur=start;count=0
 while cur<=end:
  if business_day(cur,off):count+=1
  cur+=timedelta(days=1)
 return count

def minus_business_days(target,count,off):
 cur=target
 while count:
  cur-=timedelta(days=1)
  if business_day(cur,off):count-=1
 return cur

def mmdd(d):return d.strftime("%m.%d")

def tasks(records,today):
 years={today.year,today.year-1,today.year+1};off=holiday_set(years);out=[]
 for x in sorted(records,key=lambda r:r["name"]):
  name=x["name"];ds=x.get("demand_start");de=x.get("demand_end");offer=x.get("offer_start");pay=x.get("payment");listing=x.get("listing")
  if ds and de and ds<=today<=de and business_day(today,off):
   n=business_index(ds,today,off)
   out.append(f"{name} 수요예측 {n}일차입니다. 수요예측시작:{mmdd(ds)}, 수요예측마감 {mmdd(de)}")
  if de==today:out.append(f"{name} 수요예측 마감일 입니다.")
  if offer==today:out.append(f"{name} 공모주 청약일 1일차입니다.")
  if pay and minus_business_days(pay,2,off)==today:
   out.append(f"{name} 납입일 2영업일 전입니다. 공문을 작성하세요. {name} 납입일 {mmdd(pay)}")
  if pay==today:out.append(f"{name} 납입일 입니다. 수신팀에게 메신저를 보내세요.")
  if listing==today:out.append(f"금일 {name} 상장일 입니다. 매도 공문을 작성하세요.")
 return out

def message(today,items):
 title=f"📌 공모주 업무 알림 | {today.month}월 {today.day}일"
 body="\n\n".join(f"• {item}" for item in items)
 return title,body

def send(title,body):
 keys=["KAKAO_REST_API_KEY","KAKAO_CLIENT_SECRET","KAKAO_REFRESH_TOKEN"]
 if any(not os.getenv(k) for k in keys):raise RuntimeError("GitHub Secrets가 필요합니다.")
 token=json.loads(request("https://kauth.kakao.com/oauth/token",{"grant_type":"refresh_token","client_id":os.environ[keys[0]],"client_secret":os.environ[keys[1]],"refresh_token":os.environ[keys[2]]},{}))
 link={"web_url":"https://www.38.co.kr/html/ipo/ipo_schedule.php","mobile_web_url":"https://www.38.co.kr/html/ipo/ipo_schedule.php"}
 template={"object_type":"feed","content":{"title":title,"description":body,"link":link},"button_title":"38 일정 확인"}
 result=json.loads(request("https://kapi.kakao.com/v2/api/talk/memo/default/send",{"template_object":json.dumps(template,ensure_ascii=False)},{"Authorization":"Bearer "+token["access_token"]}))
 if result.get("result_code")!=0:raise RuntimeError(str(result))
 if token.get("refresh_token"):print("::warning::KAKAO_REFRESH_TOKEN 갱신 필요")

def main():
 today=date.fromisoformat(os.getenv("ALERT_DATE") or date.today().isoformat());records=all_records();items=tasks(records,today)
 if not items:print("오늘 알림 없음");return
 title,body=message(today,items)
 print(title+"\n"+body)
 if os.getenv("DRY_RUN")=="1":return
 state=json.loads(STATE.read_text()) if STATE.exists() else {"sent_dates":[]}
 if today.isoformat() in state.get("sent_dates",[]) and os.getenv("FORCE_SEND")!="1":print("이미 발송함");return
 send(title,body)
 STATE.parent.mkdir(exist_ok=True);state["sent_dates"]=(state.get("sent_dates",[])+[today.isoformat()])[-90:];STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2));print("발송 성공: 1건")

if __name__=="__main__":main()
