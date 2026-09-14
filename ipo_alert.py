import html,json,os,re,sys,urllib.parse,urllib.request
from datetime import date,datetime,timedelta
from pathlib import Path
try:
 import holidays
except ImportError:
 holidays=None
IPO_URL="https://ipokorea.kr/"
STATE=Path("state/sent.json")
def post(url,data=None,headers=None):
 body=urllib.parse.urlencode(data).encode() if data else None
 req=urllib.request.Request(url,data=body,headers=headers or {})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read()
def extract(page):
 text=html.unescape(page.decode("utf-8"));chunks=[]
 for m in re.finditer(r"self\.__next_f\.push\((.*?)\)</script>",text,re.S):
  try:
   v=json.loads(m.group(1))
   if isinstance(v,list) and len(v)>1 and isinstance(v[1],str):chunks.append(v[1])
  except json.JSONDecodeError:pass
 payload="\n".join(chunks);decoder=json.JSONDecoder();out={}
 for m in re.finditer(r'\{"id":"',payload):
  try:o,_=decoder.raw_decode(payload[m.start():])
  except json.JSONDecodeError:continue
  if isinstance(o,dict) and o.get("회사명") and o.get("id"):out[o["id"]]=o
 return list(out.values())
def day(v):return datetime.strptime(v,"%Y-%m-%d").date() if v else None
def third(start):
 off=holidays.KR(years=[start.year]) if holidays else set();cur=start;n=0
 while True:
  if cur.weekday()<5 and cur not in off:
   n+=1
   if n==3:return cur
  cur+=timedelta(days=1)
def tasks(records,today):
 out=[]
 for x in records:
  name=x.get("회사명","종목명 미확인");ds=day(x.get("수요예측시작일"));de=day(x.get("수요예측종료일"));ss=day(x.get("청약시작일"));pay=day(x.get("납입기일"));listing=day(x.get("상장일"))
  if ds and third(ds)==today:out.append((name,"수요예측 3일차","일임사에 1차 참여의견을 문의하세요."))
  if de==today:out.append((name,"수요예측 마지막 날","일임사 참여의견을 확인하고 최종 참여 여부를 확정하세요."))
  if ss==today:out.append((name,"공모청약 첫날","일임사가 정상적으로 청약했는지 확인하세요."))
  if pay==today:out.append((name,"납입일","납입금액과 계좌를 재확인한 뒤 실제 자금을 보내세요."))
  if listing==today:out.append((name,"상장일","상장 및 매매 개시 상황을 확인하세요."))
 return out
def message(today,items):
 lines=[f"[공모주 업무 알림 | {today.month}월 {today.day}일]",""]
 for i,(name,event,action) in enumerate(items,1):lines += [f"{i}. {name} - {event}",f"- {action}",""]
 lines.append("일정은 변경될 수 있으니 주관사 공지와 KIND에서 최종 확인하세요.")
 return "\n".join(lines)
def main():
 today=date.fromisoformat(os.getenv("ALERT_DATE") or date.today().isoformat());records=extract(post(IPO_URL));items=tasks(records,today)
 if not records:raise RuntimeError("공모주 데이터를 읽지 못했습니다.")
 if not items:print("오늘 알림 없음");return
 state=json.loads(STATE.read_text()) if STATE.exists() else {"sent_dates":[]}
 if today.isoformat() in state["sent_dates"] and os.getenv("FORCE_SEND")!="1":print("이미 발송함");return
 msg=message(today,items)
 if os.getenv("DRY_RUN")=="1":print(msg);return
 keys=["KAKAO_REST_API_KEY","KAKAO_CLIENT_SECRET","KAKAO_REFRESH_TOKEN"]
 if any(not os.getenv(k) for k in keys):raise RuntimeError("GitHub Secrets가 필요합니다.")
 tok=json.loads(post("https://kauth.kakao.com/oauth/token",{"grant_type":"refresh_token","client_id":os.environ[keys[0]],"client_secret":os.environ[keys[1]],"refresh_token":os.environ[keys[2]]}))
 template={"object_type":"text","text":msg,"link":{"web_url":"https://kind.krx.co.kr","mobile_web_url":"https://kind.krx.co.kr"},"button_title":"KIND 확인"}
 result=json.loads(post("https://kapi.kakao.com/v2/api/talk/memo/default/send",{"template_object":json.dumps(template,ensure_ascii=False)},{"Authorization":"Bearer "+tok["access_token"]}))
 if result.get("result_code")!=0:raise RuntimeError(str(result))
 STATE.parent.mkdir(exist_ok=True);state["sent_dates"]=(state["sent_dates"]+[today.isoformat()])[-90:];STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2));print("발송 성공")
 if tok.get("refresh_token"):print("::warning::KAKAO_REFRESH_TOKEN 갱신 필요")
if __name__=="__main__":main()
