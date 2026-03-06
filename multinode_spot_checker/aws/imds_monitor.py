#!/usr/bin/env python3
import requests,time,json,boto3,sys,os
from datetime import datetime
TU="http://169.254.169.254/latest/api/token"
EP="http://169.254.169.254/latest/meta-data"
AU=f"{EP}/spot/instance-action"
RU=f"{EP}/events/recommendations/rebalance"
def get_imds_token(ttl=21600):
 try:
  r=requests.put(TU,headers={"X-aws-ec2-metadata-token-ttl-seconds":str(ttl)},timeout=1)
  return r.text if r.status_code==200 else None
 except:return None
def get_instance_id(tk):
 try:
  r=requests.get(f"{EP}/instance-id",headers={"X-aws-ec2-metadata-token":tk},timeout=1)
  return r.text if r.status_code==200 else None
 except:return None
def get_spot_instance_action(tk):
 try:
  r=requests.get(AU,headers={"X-aws-ec2-metadata-token":tk},timeout=1)
  return json.loads(r.text) if r.status_code==200 else None
 except:return None
def get_rebalance_event(tk):
 try:
  r=requests.get(RU,headers={"X-aws-ec2-metadata-token":tk},timeout=1)
  if r.status_code!=200:return None
  d=json.loads(r.text)
  if isinstance(d,list):return None
  return d.get('instance-action',d if d else None)
 except:return None
def put_logs_to_cloudwatch(iid,ad,rg,lg,lsp):
 try:
  lc=boto3.client('logs',region_name=rg)
  try:lc.create_log_group(logGroupName=lg)
  except:pass
  try:lc.create_log_stream(logGroupName=lg,logStreamName=lsp)
  except:pass
  m={**ad,'instance_id':iid,'detected_at':datetime.utcnow().isoformat(),'detector':'imds-monitor'}
  lc.put_log_events(logGroupName=lg,logStreamName=lsp,logEvents=[{'timestamp':int(time.time()*1000),'message':json.dumps(m)}])
 except Exception as e:print(f"[CW] Error: {e}")
def get_region_from_imds(tk):
 try:
  r=requests.get(f"{EP}/placement/availability-zone",headers={"X-aws-ec2-metadata-token":tk},timeout=1)
  return r.text[:-1] if r.status_code==200 else "ap-northeast-2"
 except:return "ap-northeast-2"
def main():
 print("[IMDS] Starting monitor...")
 lg=os.environ.get('IMDS_LOG_GROUP','jglee-spot-checker-multinode-log')
 lsp=os.environ.get('IMDS_LOG_STREAM','imds-monitor')
 tk=get_imds_token()
 if not tk:
  time.sleep(10)
  tk=get_imds_token()
 iid=get_instance_id(tk)
 rg=get_region_from_imds(tk)
 print(f"[IMDS] Instance: {iid} in {rg}")
 i=5
 mx=720
 a=0
 rd=ad=False
 while a<mx:
  try:
   if a%200==0:tk=get_imds_token()
   if not rd:
    rb=get_rebalance_event(tk)
    if rb:
     print(f"[IMDS] Rebalance detected")
     put_logs_to_cloudwatch(iid,{**rb,'event_type':'rebalance'},rg,lg,lsp)
     rd=True
   if not ad:
    ac=get_spot_instance_action(tk)
    if ac:
     print(f"[IMDS] Action detected")
     put_logs_to_cloudwatch(iid,{**ac,'event_type':'action'},rg,lg,lsp)
     ad=True
     break
   time.sleep(i)
   a+=1
   if a%24==0:print(f"[IMDS] Monitoring... {a*i}s")
  except KeyboardInterrupt:break
  except Exception as e:
   time.sleep(i)
   a+=1
 if a>=mx:print(f"[IMDS] Timeout"  )
if __name__=='__main__':main()
