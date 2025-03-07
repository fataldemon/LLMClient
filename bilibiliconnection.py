import asyncio
import os

from dotenv import load_dotenv
import blivedm
import blivedm.models.open_live as open_models
import blivedm.models.web as web_models

load_dotenv()


class BilibiliClient:

    def __init__(self, access_key_id: str, access_key_secret: str, app_id: int, room_owner_id: str):
        self.client = None
        self.ACCESS_KEY_ID = access_key_id
        self.ACCESS_KEY_SECRET = access_key_secret
        self.APP_ID = app_id
        self.ROOM_OWNER_AUTH_CODE = room_owner_id

    async def run_single_client(self):
        """
        演示监听一个直播间
        """
        self.client = blivedm.OpenLiveClient(
            access_key_id=ACCESS_KEY_ID,
            access_key_secret=ACCESS_KEY_SECRET,
            app_id=APP_ID,
            room_owner_auth_code=ROOM_OWNER_AUTH_CODE,
        )
        handler = MyHandler()
        self.client.set_handler(handler)

        self.client.start()
        try:
            # 演示70秒后停止
            # await asyncio.sleep(70)
            # client.stop()

            await self.client.join()
        finally:
            await self.client.stop_and_close()

    async def close_client(self):
        await self.client.stop_and_close()


class MyHandler(blivedm.BaseHandler):
    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        print(f'[{client.room_id}] 心跳')

    def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
        print(f'[{message.room_id}] {message.uname}：{message.msg}')

    def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
        coin_type = '金瓜子' if message.paid else '银瓜子'
        total_coin = message.price * message.gift_num
        print(f'[{message.room_id}] {message.uname} 赠送{message.gift_name}x{message.gift_num}'
              f' （{coin_type}x{total_coin}）')

    def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
        print(f'[{message.room_id}] {message.user_info.uname} 购买 大航海等级={message.guard_level}')

    def _on_open_live_super_chat(
        self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage
    ):
        print(f'[{message.room_id}] 醒目留言 ¥{message.rmb} {message.uname}：{message.message}')

    def _on_open_live_super_chat_delete(
        self, client: blivedm.OpenLiveClient, message: open_models.SuperChatDeleteMessage
    ):
        print(f'[{message.room_id}] 删除醒目留言 message_ids={message.message_ids}')

    def _on_open_live_like(self, client: blivedm.OpenLiveClient, message: open_models.LikeMessage):
        print(f'[{message.room_id}] {message.uname} 点赞')

    def _on_open_live_enter_room(self, client: blivedm.OpenLiveClient, message: open_models.RoomEnterMessage):
        print(f'[{message.room_id}] {message.uname} 进入房间')

    def _on_open_live_start_live(self, client: blivedm.OpenLiveClient, message: open_models.LiveStartMessage):
        print(f'[{message.room_id}] 开始直播')

    def _on_open_live_end_live(self, client: blivedm.OpenLiveClient, message: open_models.LiveEndMessage):
        print(f'[{message.room_id}] 结束直播')


if __name__ == '__main__':
    # 在开放平台申请的开发者密钥
    ACCESS_KEY_ID = os.environ.get("ACCESS_KEY_ID")
    ACCESS_KEY_SECRET = os.environ.get("ACCESS_KEY_SECRET")
    # 在开放平台创建的项目ID
    APP_ID = int(os.environ.get("APP_ID"))
    # 主播身份码
    ROOM_OWNER_AUTH_CODE = os.environ.get("ROOM_OWNER_AUTH_CODE")
    client = BilibiliClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, APP_ID, ROOM_OWNER_AUTH_CODE)
    asyncio.run(client.run_single_client())




