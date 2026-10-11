"""Exercise the authenticated v1 device API. Uses a private provisioning file."""
import argparse
import json
import math
from pathlib import Path
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError
from outbox import Outbox, upload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--credentials',type=Path,required=True)
    parser.add_argument('--base',default='http://127.0.0.1:8788')
    parser.add_argument('--count',type=int,default=0)
    args=parser.parse_args()
    if args.count<0: parser.error('count must be nonnegative')
    credentials=json.loads(args.credentials.read_text())
    token=credentials['deviceToken']
    device=credentials['deviceId']
    queue=Outbox(str(Path('work')/('outbox-'+device+'.sqlite3')))
    boot=uuid.uuid4().hex;step=0;mode='normal'
    print('Synthetic device simulation; coordinates do not describe a real pet.')
    while not args.count or step<args.count:
        started=time.monotonic();interval=60
        heartbeat={'battery':85,'fixValid':True,'appliedMode':mode,'firmware':'desktop-simulator-0.2'}
        try:
            request=Request(args.base+'/v1/device/heartbeat',data=json.dumps(heartbeat).encode(),
                            headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
            with urlopen(request,timeout=5) as response: settings=json.load(response)
            mode=settings['desiredMode'];interval=settings['reportIntervalSeconds']
        except (URLError,OSError,ValueError): print('Heartbeat failed; keeping previous mode')
        point={'bootId':boot,'sequence':step,'capturedAt':time.time(),'latitude':31.2304+.001*math.sin(step/20),
               'longitude':121.4737+.001*math.cos(step/20),'coordinateSystem':'gcj02','battery':85}
        try: queue.enqueue(point)
        except OverflowError: print('Outbox full; new point not stored')
        try:
            queue.flush(lambda p:upload(p,args.base+'/v1/device/positions',token))
            print('Pending points:',queue.pending(),'mode:',mode)
        except (URLError,OSError,ValueError): print('Upload failed; points retained:',queue.pending())
        step+=1
        if not args.count or step<args.count: time.sleep(max(1,interval-(time.monotonic()-started)))

if __name__=='__main__':
    try: main()
    except KeyboardInterrupt: print('Stopped; pending points retained.')
