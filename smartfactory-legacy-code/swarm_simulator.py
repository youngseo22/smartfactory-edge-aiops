import asyncio
import json
import random
from datetime import datetime, timezone
import websockets

SERVER_URL = "ws://localhost:8000/ws"
NUM_DEVICES = 1000  # 동시에 연결할 가상 설비(센서) 개수

async def run_virtual_sensor(device_num: int):
    device_id = f"MIXER-SIM-{device_num:03d}"
    uri = f"{SERVER_URL}/{device_id}"

    while True:
        try:
            async with websockets.connect(uri) as ws:
                while True:
                    # 1. 센서에서 데이터가 측정된 실제 시간 (Event Time) 기록
                    event_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    
                    # 평상시 정상 진동 수치 (9.5 ~ 12.0 사이), 0.5% 확률로 가상 센서에서도 이상 진동 발생
                    if random.random() < 0.005:
                        svm = round(random.uniform(18.5, 25.0), 2)
                        status = "WARNING"
                    else:
                        svm = round(random.uniform(9.5, 12.0), 2)
                        status = "NORMAL"

                    payload = {
                        "device_id": device_id,
                        "device_type": "SIMULATED_SWARM",
                        "event_time": event_time,
                        "svm": svm,
                        "status": status
                    }

                    # 2. [핵심 실험 포인트] 10% 확률로 공장 와이파이 지연(2~4초 Late Data) 시뮬레이션
                    # event_time은 과거인데 서버에는 늦게 도착하므로 순서 뒤바뀜(Out-of-order) 발생!
                    if random.random() < 0.10:
                        delay = random.uniform(2.0, 4.0)
                        asyncio.create_task(send_delayed(ws, payload, delay))
                    else:
                        await ws.send(json.dumps(payload))

                    # 3. [핵심 실험 포인트] 2% 확률로 네트워크 불안정으로 인한 연결 끊김 및 재접속 유도
                    if random.random() < 0.02:
                        break  # while 루프를 탈출하여 소켓을 끊고 바깥 루프에서 재접속 시도

                    await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception:
            pass
        
        # 끊어진 후 0.5 ~ 2초 뒤 재접속 (수십 대가 겹치면 Reconnection Storm 발생)
        await asyncio.sleep(random.uniform(0.5, 2.0))

async def send_delayed(ws, payload, delay):
    """네트워크 지연으로 인해 늦게 도착하는 데이터를 비동기로 전송"""
    await asyncio.sleep(delay)
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        pass

async def main():
    print(f"🐳 {NUM_DEVICES}대의 가상 스마트팩토리 센서 군집(Swarm) 가동을 시작합니다...")
    print("⚡ (지연 데이터 및 무작위 재접속 폭풍 시뮬레이션 포함)")
    tasks = [asyncio.create_task(run_virtual_sensor(i)) for i in range(1, NUM_DEVICES + 1)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())